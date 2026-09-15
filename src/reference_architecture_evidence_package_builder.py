from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any

from src.reference_architecture_evidence_ledger import EvidenceLedgerPort, verify_evidence_ledger_chain
from src.reference_architecture_evidence_ledger_contract import EvidenceLedgerEntry
from src.reference_architecture_evidence_package_contract import (
    EVIDENCE_PACKAGE_FORMAT_VERSION, EVIDENCE_PACKAGE_HASH_ALGORITHM, EvidencePackage,
    EvidencePackageBuildResult, EvidencePackageManifest, EvidencePackageRequest,
    PackageReasonCode, PackageStatus, PackagedEvidenceRecord,
)
from src.reference_architecture_evidence_package_serialization import sha256_digest
from src.reference_architecture_evidence_package_translation import (
    EvidencePackageTranslationError, translate_untrusted_evidence_package_request,
)


SelectionAuthorizer = Callable[[EvidencePackageRequest, Sequence[EvidenceLedgerEntry]], bool]


def _result(reason: PackageReasonCode, *, status: PackageStatus = PackageStatus.REJECTED,
            package: EvidencePackage | None = None) -> EvidencePackageBuildResult:
    return EvidencePackageBuildResult(status, reason, package)


def _project(entry: EvidenceLedgerEntry) -> PackagedEvidenceRecord:
    """Explicit public allowlist: never serialize the internal ledger object."""
    return PackagedEvidenceRecord(
        evidence_id=entry.entry_id, ledger_id=entry.chain_id, sequence=entry.sequence,
        evidence_digest=entry.evidence_sha256, evidence_type=entry.evidence_type,
        producer_id=entry.producer_id, run_id=entry.evaluation_run_id,
        admission_reference=entry.admission_decision_id,
        provenance_reference=entry.provenance_reference,
        evidence_contract_version=entry.evidence_contract_version,
        admission_contract_version=entry.admission_contract_version,
        ledger_contract_version=entry.ledger_contract_version, policy_version=entry.policy_version,
        recorded_at=entry.recorded_at.isoformat(timespec="seconds").replace("+00:00", "Z"),
        previous_entry_digest=entry.previous_entry_digest, entry_digest=entry.entry_digest,
        supersedes_evidence_id=entry.supersedes_entry_id,
    )


def build_evidence_package(payload: Mapping[str, Any], *, ledger: EvidenceLedgerPort,
                           authorize: SelectionAuthorizer | None = None) -> EvidencePackageBuildResult:
    """Build a deterministic package from one verified A.06 chain."""
    if isinstance(payload, Mapping):
        references = payload.get("evidence_ids")
        if (isinstance(references, (list, tuple)) and all(isinstance(item, str) for item in references)
                and len(references) != len(set(references))):
            return _result(PackageReasonCode.DUPLICATE_EVIDENCE_REFERENCE)
    try:
        request = translate_untrusted_evidence_package_request(payload)
    except EvidencePackageTranslationError:
        return _result(PackageReasonCode.MALFORMED_REQUEST)
    if request.format_version != EVIDENCE_PACKAGE_FORMAT_VERSION:
        return _result(PackageReasonCode.UNSUPPORTED_PACKAGE_VERSION)
    if not callable(getattr(ledger, "chain", None)):
        return _result(PackageReasonCode.INTERNAL_PACKAGE_ERROR, status=PackageStatus.ERROR)
    try:
        chain = ledger.chain(request.ledger_id)
        if not chain:
            return _result(PackageReasonCode.LEDGER_NOT_FOUND)
        if not verify_evidence_ledger_chain(chain).verified:
            return _result(PackageReasonCode.LEDGER_VERIFICATION_FAILED)
        by_id = {entry.entry_id: entry for entry in chain}
        if request.evidence_ids:
            if any(item not in by_id for item in request.evidence_ids):
                return _result(PackageReasonCode.EVIDENCE_NOT_FOUND)
            selected = [by_id[item] for item in request.evidence_ids]
        else:
            selected = list(chain)
        if request.run_id is not None:
            selected = [entry for entry in selected if entry.evaluation_run_id == request.run_id]
        if request.sequence_start is not None:
            selected = [entry for entry in selected if entry.sequence >= request.sequence_start]
        if request.sequence_end is not None:
            selected = [entry for entry in selected if entry.sequence <= request.sequence_end]
        selected.sort(key=lambda entry: entry.sequence)
        if not selected:
            return _result(PackageReasonCode.EMPTY_SELECTION)
        # A chain proof is self-contained only when every predecessor through the selected head is included.
        if selected[0].sequence != 1 or [e.sequence for e in selected] != list(range(1, selected[-1].sequence + 1)):
            return _result(PackageReasonCode.PACKAGE_INCOMPLETE)
        if authorize is not None and not authorize(request, tuple(selected)):
            return _result(PackageReasonCode.UNAUTHORIZED_SELECTION)

        records = tuple(_project(entry) for entry in selected)
        record_documents = [vars_record(record) for record in records]
        content_digest = sha256_digest(record_documents)
        selection = {
            "evidence_ids": [r.evidence_id for r in records] if request.evidence_ids else [], "run_id": request.run_id,
            "sequence_start": request.sequence_start, "sequence_end": request.sequence_end,
        }
        manifest_seed = {
            "format_version": request.format_version, "ledger_id": request.ledger_id,
            "evidence_ids": [r.evidence_id for r in records], "run_ids": sorted({r.run_id for r in records}),
            "admission_references": [r.admission_reference for r in records],
            "sequence_start": records[0].sequence, "sequence_end": records[-1].sequence,
            "entry_count": len(records), "hash_algorithm": EVIDENCE_PACKAGE_HASH_ALGORITHM,
            "ledger_head_digest": records[-1].entry_digest, "content_digest": content_digest,
            "selection": selection, "metadata": dict(sorted(request.metadata.items())),
        }
        package_id = sha256_digest(manifest_seed)
        manifest = EvidencePackageManifest(package_id=package_id, **manifest_seed)
        package_without_digest = {"manifest": vars_manifest(manifest), "records": record_documents}
        package = EvidencePackage(manifest, records, sha256_digest(package_without_digest))
        return _result(PackageReasonCode.PACKAGE_VALID, status=PackageStatus.VALID, package=package)
    except Exception:
        return _result(PackageReasonCode.INTERNAL_PACKAGE_ERROR, status=PackageStatus.ERROR)


def vars_record(record: PackagedEvidenceRecord) -> dict[str, Any]:
    return {name: getattr(record, name) for name in record.__dataclass_fields__}


def vars_manifest(manifest: EvidencePackageManifest) -> dict[str, Any]:
    value = {name: getattr(manifest, name) for name in manifest.__dataclass_fields__}
    for name in ("evidence_ids", "run_ids", "admission_references"):
        value[name] = list(value[name])
    value["selection"] = dict(value["selection"])
    value["metadata"] = dict(value["metadata"])
    return value
