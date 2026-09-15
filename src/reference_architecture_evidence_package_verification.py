from __future__ import annotations

from typing import Any, Mapping

from src.reference_architecture_evidence_ledger_contract import (
    EvidenceLedgerAppendRequest, EvidenceLedgerEntryId, EvidenceChainId, LedgerSequence,
)
from src.reference_architecture_evidence_ledger_identity import (
    calculate_evidence_ledger_entry_digest, calculate_evidence_ledger_entry_id,
)
from src.reference_architecture_evidence_package_builder import vars_manifest, vars_record
from src.reference_architecture_evidence_package_contract import (
    EVIDENCE_PACKAGE_FORMAT_VERSION, EVIDENCE_PACKAGE_HASH_ALGORITHM, EvidencePackage,
    EvidencePackageManifest, PackageReasonCode, PackageStatus, PackageVerificationRequest,
    PackageVerificationResult, PackagedEvidenceRecord,
)
from src.reference_architecture_evidence_package_serialization import canonical_json_bytes, parse_json_object, sha256_digest


def _invalid(reason: PackageReasonCode, package_id: str | None = None,
             evidence_id: str | None = None) -> PackageVerificationResult:
    return PackageVerificationResult(PackageStatus.INVALID, reason, package_id, evidence_id)


def _strict_keys(value: Mapping[str, Any], expected: set[str]) -> bool:
    return set(value) == expected


def _decode(value: Mapping[str, Any]) -> EvidencePackage:
    if not _strict_keys(value, {"manifest", "records", "package_digest"}):
        raise ValueError
    raw_manifest = value["manifest"]
    raw_records = value["records"]
    if not isinstance(raw_manifest, Mapping) or not isinstance(raw_records, list):
        raise ValueError
    manifest_fields = set(EvidencePackageManifest.__dataclass_fields__)
    record_fields = set(PackagedEvidenceRecord.__dataclass_fields__)
    if not _strict_keys(raw_manifest, manifest_fields):
        raise ValueError
    manifest_value = dict(raw_manifest)
    for name in ("evidence_ids", "run_ids", "admission_references"):
        if not isinstance(manifest_value[name], list): raise ValueError
        manifest_value[name] = tuple(manifest_value[name])
    records = []
    for item in raw_records:
        if not isinstance(item, Mapping) or not _strict_keys(item, record_fields): raise ValueError
        records.append(PackagedEvidenceRecord(**item))
    return EvidencePackage(EvidencePackageManifest(**manifest_value), tuple(records), value["package_digest"])


def verify_evidence_package(request: PackageVerificationRequest) -> PackageVerificationResult:
    if not isinstance(request, PackageVerificationRequest):
        return _invalid(PackageReasonCode.MALFORMED_REQUEST)
    raw: bytes | None = None
    try:
        if isinstance(request.package, EvidencePackage):
            package = request.package
        else:
            value, raw = parse_json_object(request.package)
            package = _decode(value)
        package_id = package.manifest.package_id
        if raw is not None and raw != canonical_json_bytes({
            "manifest": vars_manifest(package.manifest), "package_digest": package.package_digest,
            "records": [vars_record(r) for r in package.records],
        }):
            return _invalid(PackageReasonCode.MANIFEST_MISMATCH, package_id)
        if package.manifest.format_version != EVIDENCE_PACKAGE_FORMAT_VERSION:
            return _invalid(PackageReasonCode.UNSUPPORTED_PACKAGE_VERSION, package_id)
        if package.manifest.hash_algorithm != EVIDENCE_PACKAGE_HASH_ALGORITHM:
            return _invalid(PackageReasonCode.UNSUPPORTED_ALGORITHM, package_id)
        records_docs = [vars_record(r) for r in package.records]
        if package.manifest.content_digest != sha256_digest(records_docs):
            return _invalid(PackageReasonCode.EVIDENCE_DIGEST_MISMATCH, package_id)
        without_digest = {"manifest": vars_manifest(package.manifest), "records": records_docs}
        if package.package_digest != sha256_digest(without_digest):
            return _invalid(PackageReasonCode.PACKAGE_DIGEST_MISMATCH, package_id)
        manifest_seed = vars_manifest(package.manifest)
        manifest_seed.pop("package_id")
        if package_id != sha256_digest(manifest_seed):
            return _invalid(PackageReasonCode.MANIFEST_MISMATCH, package_id)
        if not package.records:
            return _invalid(PackageReasonCode.PACKAGE_INCOMPLETE, package_id)
        m = package.manifest
        if (m.entry_count != len(package.records) or m.evidence_ids != tuple(r.evidence_id for r in package.records)
                or m.run_ids != tuple(sorted({r.run_id for r in package.records}))
                or m.admission_references != tuple(r.admission_reference for r in package.records)
                or m.sequence_start != package.records[0].sequence or m.sequence_end != package.records[-1].sequence
                or m.ledger_head_digest != package.records[-1].entry_digest):
            return _invalid(PackageReasonCode.MANIFEST_MISMATCH, package_id)
        if len(set(m.evidence_ids)) != len(m.evidence_ids):
            return _invalid(PackageReasonCode.PACKAGE_INCOMPLETE, package_id)
        if [r.sequence for r in package.records] != list(range(1, len(package.records) + 1)):
            return _invalid(PackageReasonCode.CHAIN_PROOF_INVALID, package_id)
        selection = m.selection
        if not isinstance(selection, Mapping): return _invalid(PackageReasonCode.MANIFEST_MISMATCH, package_id)
        run_id = selection.get("run_id")
        if run_id is not None and any(r.run_id != run_id for r in package.records):
            return _invalid(PackageReasonCode.RUN_BINDING_MISMATCH, package_id)
        requested_ids = selection.get("evidence_ids")
        if requested_ids and tuple(requested_ids) != m.evidence_ids:
            return _invalid(PackageReasonCode.PACKAGE_INCOMPLETE, package_id)
        for index, record in enumerate(package.records):
            if record.ledger_id != m.ledger_id:
                return _invalid(PackageReasonCode.CHAIN_PROOF_INVALID, package_id, record.evidence_id)
            expected_previous = None if index == 0 else package.records[index - 1]
            if record.previous_entry_digest != (None if expected_previous is None else expected_previous.entry_digest):
                return _invalid(PackageReasonCode.CHAIN_PROOF_INVALID, package_id, record.evidence_id)
            if index and record.supersedes_evidence_id != expected_previous.evidence_id:
                return _invalid(PackageReasonCode.CHAIN_PROOF_INVALID, package_id, record.evidence_id)
            append = EvidenceLedgerAppendRequest(
                record.evidence_digest, record.evidence_type, record.producer_id, record.run_id,
                record.admission_reference, record.provenance_reference, record.evidence_contract_version,
                record.admission_contract_version, record.ledger_contract_version, record.policy_version,
                __import__("datetime").datetime.fromisoformat(record.recorded_at.replace("Z", "+00:00")),
                None if record.supersedes_evidence_id is None else EvidenceLedgerEntryId(record.supersedes_evidence_id),
            )
            if calculate_evidence_ledger_entry_id(append) != record.evidence_id:
                return _invalid(PackageReasonCode.ADMISSION_BINDING_MISMATCH, package_id, record.evidence_id)
            digest = calculate_evidence_ledger_entry_digest(request=append,
                entry_id=EvidenceLedgerEntryId(record.evidence_id), chain_id=EvidenceChainId(record.ledger_id),
                sequence=LedgerSequence(record.sequence), previous_entry_digest=record.previous_entry_digest)
            if digest != record.entry_digest:
                return _invalid(PackageReasonCode.EVIDENCE_DIGEST_MISMATCH, package_id, record.evidence_id)
        return PackageVerificationResult(PackageStatus.VALID, PackageReasonCode.PACKAGE_VALID, package_id)
    except Exception:
        return _invalid(PackageReasonCode.MALFORMED_REQUEST)
