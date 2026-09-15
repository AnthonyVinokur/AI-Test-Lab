from __future__ import annotations

from dataclasses import asdict
from typing import Any, Mapping

from src.reference_architecture_evidence_disclosure_contract import (
    DISCLOSURE_HASH_ALGORITHM, DISCLOSURE_SCHEMA_VERSION, DisclosureDecision, DisclosureManifest,
    DisclosureReasonCode, DisclosureReceipt, DisclosureVerificationResult, EvidenceDisclosureRelease,
    PublicEvidenceRecord,
)
from src.reference_architecture_evidence_disclosure_serialization import (
    canonical_disclosure_json_bytes, disclosure_digest, parse_disclosure_document,
)


def _failed(reason: DisclosureReasonCode, release_id: str | None = None) -> DisclosureVerificationResult:
    return DisclosureVerificationResult(False, DisclosureDecision.INTEGRITY_FAILURE, reason, release_id)


def _decode(value: Mapping[str, Any]) -> EvidenceDisclosureRelease:
    if set(value) != {"manifest", "records", "receipt"}: raise ValueError
    if not isinstance(value["manifest"], Mapping) or not isinstance(value["receipt"], Mapping) or not isinstance(value["records"], list):
        raise ValueError
    if set(value["manifest"]) != set(DisclosureManifest.__dataclass_fields__) or set(value["receipt"]) != set(DisclosureReceipt.__dataclass_fields__):
        raise ValueError
    manifest = dict(value["manifest"])
    manifest["disclosed_record_ids"] = tuple(manifest["disclosed_record_ids"])
    manifest["disclosed_fields"] = tuple(manifest["disclosed_fields"])
    records = []
    for raw in value["records"]:
        if not isinstance(raw, Mapping) or set(raw) != {"evidence_id", "fields"} or not isinstance(raw["fields"], list): raise ValueError
        records.append(PublicEvidenceRecord(raw["evidence_id"], tuple(tuple(item) for item in raw["fields"])))
    return EvidenceDisclosureRelease(DisclosureManifest(**manifest), tuple(records), DisclosureReceipt(**value["receipt"]))


def verify_disclosure_release(value: EvidenceDisclosureRelease | bytes | str | Mapping[str, Any]) -> DisclosureVerificationResult:
    raw = None
    try:
        if isinstance(value, EvidenceDisclosureRelease): release = value
        else:
            document, raw = parse_disclosure_document(value); release = _decode(document)
        release_id = release.manifest.release_id
        if raw is not None and raw != canonical_disclosure_json_bytes(asdict(release)):
            return _failed(DisclosureReasonCode.RELEASE_INTEGRITY_FAILURE, release_id)
        manifest = release.manifest; receipt = release.receipt
        if manifest.schema_version != DISCLOSURE_SCHEMA_VERSION or receipt.receipt_version != DISCLOSURE_SCHEMA_VERSION:
            return DisclosureVerificationResult(False, DisclosureDecision.UNSUPPORTED_VERSION,
                                                DisclosureReasonCode.UNSUPPORTED_VERSION, release_id)
        if manifest.digest_algorithm != DISCLOSURE_HASH_ALGORITHM or manifest.serialization_algorithm != "canonical-json-rfc8259":
            return DisclosureVerificationResult(False, DisclosureDecision.UNSUPPORTED_VERSION,
                                                DisclosureReasonCode.UNSUPPORTED_ALGORITHM, release_id)
        manifest_seed = asdict(manifest); manifest_seed.pop("release_id")
        if disclosure_digest(manifest_seed) != release_id: return _failed(DisclosureReasonCode.RELEASE_INTEGRITY_FAILURE, release_id)
        if disclosure_digest([asdict(record) for record in release.records]) != manifest.content_digest:
            return _failed(DisclosureReasonCode.RELEASE_INTEGRITY_FAILURE, release_id)
        if manifest.disclosed_record_ids != tuple(record.evidence_id for record in release.records):
            return _failed(DisclosureReasonCode.RELEASE_INTEGRITY_FAILURE, release_id)
        if any(tuple(name for name, _ in record.fields) != manifest.disclosed_fields for record in release.records):
            return _failed(DisclosureReasonCode.RELEASE_INTEGRITY_FAILURE, release_id)
        if (receipt.release_id != release_id or receipt.source_package_id != manifest.source_package_id
                or receipt.authorization_decision_id != manifest.authorization_decision_id
                or receipt.disclosure_request_id != manifest.disclosure_request_id
                or receipt.recipient_id != manifest.recipient_id or receipt.purpose != manifest.purpose
                or receipt.released_at != manifest.released_at or receipt.content_digest != manifest.content_digest
                or receipt.manifest_digest != disclosure_digest(asdict(manifest))):
            return _failed(DisclosureReasonCode.RELEASE_INTEGRITY_FAILURE, release_id)
        receipt_seed = asdict(receipt); receipt_seed.pop("receipt_digest")
        if disclosure_digest(receipt_seed) != receipt.receipt_digest:
            return _failed(DisclosureReasonCode.RELEASE_INTEGRITY_FAILURE, release_id)
        return DisclosureVerificationResult(True, DisclosureDecision.RELEASED, DisclosureReasonCode.RELEASE_CREATED, release_id)
    except Exception:
        return _failed(DisclosureReasonCode.RELEASE_INTEGRITY_FAILURE)
