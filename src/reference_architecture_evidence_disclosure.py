from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict
from threading import Lock

from src.reference_architecture_evidence_disclosure_contract import (
    DISCLOSURE_CONTRACT_VERSION, DISCLOSURE_HASH_ALGORITHM, DISCLOSURE_SCHEMA_VERSION,
    DisclosureAuthorization, DisclosureDecision, DisclosureManifest, DisclosureOutcome,
    DisclosureReasonCode, DisclosureReceipt, DisclosureRequest, EvidenceDisclosureRelease,
    PublicEvidenceRecord,
)
from src.reference_architecture_evidence_disclosure_serialization import disclosure_digest
from src.reference_architecture_evidence_package_contract import PackageVerificationRequest
from src.reference_architecture_evidence_package_serialization import serialize_evidence_package
from src.reference_architecture_evidence_package_verification import verify_evidence_package


PUBLIC_RECORD_FIELDS = frozenset({
    "evidence_id", "sequence", "evidence_digest", "evidence_type", "producer_id", "run_id",
    "admission_reference", "provenance_reference", "evidence_contract_version",
    "admission_contract_version", "ledger_contract_version", "recorded_at", "entry_digest",
})
PROTECTED_RECORD_FIELDS = frozenset({
    "policy_version", "previous_entry_digest", "supersedes_evidence_id", "internal_policy_rules",
    "risk_score", "governance_interpretation", "compliance_recommendation", "credentials",
    "orchestration_state", "storage_provider", "debug", "private_model_data", "customer_data",
})


class InMemoryDisclosureReplayRegistry:
    """Atomic one-time grant registry. Persistent deployments should implement this port durably."""
    def __init__(self) -> None:
        self._used: set[str] = set(); self._lock = Lock()

    def claim(self, authorization_id: str) -> bool:
        with self._lock:
            if authorization_id in self._used: return False
            self._used.add(authorization_id); return True


def _out(decision: DisclosureDecision, reason: DisclosureReasonCode) -> DisclosureOutcome:
    return DisclosureOutcome(decision, reason)


def disclose_evidence(
    request: DisclosureRequest,
    authorization: DisclosureAuthorization,
    *,
    replay_registry: InMemoryDisclosureReplayRegistry | None = None,
    lifecycle_allows: Callable[[tuple[str, ...]], bool] | None = None,
) -> DisclosureOutcome:
    """Validate, minimize, and bind a verified A.07 package to a safe public release."""
    try:
        if not isinstance(request, DisclosureRequest) or not isinstance(authorization, DisclosureAuthorization):
            return _out(DisclosureDecision.INVALID_REQUEST, DisclosureReasonCode.MALFORMED_REQUEST)
        if request.contract_version != DISCLOSURE_CONTRACT_VERSION:
            return _out(DisclosureDecision.UNSUPPORTED_VERSION, DisclosureReasonCode.UNSUPPORTED_VERSION)
        if request.output_format != "json":
            return _out(DisclosureDecision.UNSUPPORTED_VERSION, DisclosureReasonCode.UNSUPPORTED_FORMAT)
        # A.07's canonical bytes are the public verification boundary; normalizing through them also
        # prevents internal container representation from affecting the disclosure decision.
        verified = verify_evidence_package(PackageVerificationRequest(serialize_evidence_package(request.package)))
        if not verified.verified:
            return _out(DisclosureDecision.INTEGRITY_FAILURE, DisclosureReasonCode.PACKAGE_INTEGRITY_FAILURE)
        package_id = request.package.manifest.package_id
        binding = (request.authorization_id == authorization.authorization_id
            and request.requester_id == authorization.requester_id
            and request.recipient_id == authorization.recipient_id
            and package_id == authorization.package_id
            and request.package.package_digest == authorization.package_digest
            and request.purpose == authorization.purpose and request.environment == authorization.environment)
        if not authorization.granted:
            return _out(DisclosureDecision.DENIED, DisclosureReasonCode.AUTHORIZATION_DENIED)
        if not binding:
            return _out(DisclosureDecision.AUTHORIZATION_MISMATCH, DisclosureReasonCode.AUTHORIZATION_BINDING_MISMATCH)
        if authorization.revoked:
            return _out(DisclosureDecision.DENIED, DisclosureReasonCode.AUTHORIZATION_REVOKED)
        if request.requested_at < authorization.issued_at or request.requested_at >= authorization.expires_at:
            return _out(DisclosureDecision.DENIED, DisclosureReasonCode.AUTHORIZATION_EXPIRED)
        requested_ids, requested_fields = set(request.requested_record_ids), set(request.requested_fields)
        package_ids = {record.evidence_id for record in request.package.records}
        if (not requested_ids <= package_ids or not requested_ids <= authorization.authorized_record_ids
                or not requested_fields <= authorization.authorized_fields):
            return _out(DisclosureDecision.SCOPE_EXCEEDED, DisclosureReasonCode.SCOPE_EXCEEDED)
        if requested_fields & PROTECTED_RECORD_FIELDS:
            return _out(DisclosureDecision.SCOPE_EXCEEDED, DisclosureReasonCode.PROTECTED_FIELD_REQUESTED)
        if not requested_fields <= PUBLIC_RECORD_FIELDS:
            return _out(DisclosureDecision.SCOPE_EXCEEDED, DisclosureReasonCode.SCOPE_EXCEEDED)
        ordered_ids = tuple(r.evidence_id for r in request.package.records if r.evidence_id in requested_ids)
        if lifecycle_allows is not None and lifecycle_allows(ordered_ids) is not True:
            return _out(DisclosureDecision.LIFECYCLE_RESTRICTED, DisclosureReasonCode.LIFECYCLE_RESTRICTED)
        if authorization.one_time:
            if replay_registry is None or not replay_registry.claim(authorization.authorization_id):
                return _out(DisclosureDecision.DENIED, DisclosureReasonCode.REPLAY_DETECTED)
        field_order = tuple(sorted(requested_fields))
        records = tuple(PublicEvidenceRecord(record.evidence_id,
            tuple((name, getattr(record, name)) for name in field_order))
            for record in request.package.records if record.evidence_id in requested_ids)
        released_at = request.requested_at.isoformat().replace("+00:00", "Z")
        content_digest = disclosure_digest([asdict(record) for record in records])
        manifest_seed = {
            "schema_version": DISCLOSURE_SCHEMA_VERSION, "source_package_id": package_id,
            "source_package_digest": request.package.package_digest,
            "authorization_decision_id": authorization.decision_id,
            "disclosure_request_id": request.request_id, "requester_id": request.requester_id,
            "recipient_id": request.recipient_id, "purpose": request.purpose, "environment": request.environment,
            "disclosed_record_ids": ordered_ids, "disclosed_fields": field_order, "released_at": released_at,
            "content_digest": content_digest, "serialization_algorithm": "canonical-json-rfc8259",
            "digest_algorithm": DISCLOSURE_HASH_ALGORITHM,
        }
        release_id = disclosure_digest(manifest_seed)
        manifest = DisclosureManifest(release_id=release_id, **manifest_seed)
        manifest_digest = disclosure_digest(asdict(manifest))
        receipt_seed = {
            "receipt_version": DISCLOSURE_SCHEMA_VERSION, "release_id": release_id,
            "source_package_id": package_id, "authorization_decision_id": authorization.decision_id,
            "disclosure_request_id": request.request_id, "recipient_id": request.recipient_id,
            "purpose": request.purpose, "released_at": released_at, "content_digest": content_digest,
            "manifest_digest": manifest_digest,
            "statement": "This receipt proves what was released; it does not certify correctness, safety, compliance, or production approval.",
        }
        receipt = DisclosureReceipt(receipt_digest=disclosure_digest(receipt_seed), **receipt_seed)
        return DisclosureOutcome(DisclosureDecision.RELEASED, DisclosureReasonCode.RELEASE_CREATED,
                                 EvidenceDisclosureRelease(manifest, records, receipt))
    except Exception:
        return _out(DisclosureDecision.INTERNAL_ERROR, DisclosureReasonCode.INTERNAL_DISCLOSURE_ERROR)
