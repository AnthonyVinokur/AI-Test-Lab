from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from typing import Any, Callable, Mapping

from src.reference_architecture_deployment_approval import (
    ApprovalAttestation, ApprovalLifecycleEvent, canonical_approval_json,
    current_approval_state, verify_approval_attestation,
)
from src.reference_architecture_deployment_approval_contract import (
    ApprovalState, ArtifactBinding, DeploymentTarget,
)
from src.reference_architecture_deployment_authorization_contract import (
    AUTHORIZATION_CONTRACT_VERSION, AuthorizationEventType, AuthorizationLifecycleRecord,
    AuthorizationLifecycleState, AuthorizationOutcome, AuthorizationPolicy,
    AuthorizationPolicyReference, AuthorizationState, AuthorizationVerificationResult,
    DeploymentAuthorizationAttestation, DeploymentAuthorizationRequest, DeploymentContext,
    PublicAuthorizationResult, VerifiedApprovalReference, VerifiedDecisionReference,
)
from src.reference_architecture_policy_decision import (
    DecisionAttestation, canonical_decision_json, verify_decision_attestation,
)
from src.reference_architecture_policy_decision_contract import (
    DecisionState, PolicyContract, decision_utc,
)


class AuthorizationDocumentError(ValueError):
    pass


def canonical_authorization_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def _timestamp(value: datetime) -> str:
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_time(value: object) -> datetime:
    if type(value) is not str or len(value) != 20 or not value.endswith("Z"):
        raise ValueError
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def authorization_policy_document(value: AuthorizationPolicy) -> dict[str, Any]:
    return {
        "accepted_approval_versions": sorted(value.accepted_approval_versions),
        "accepted_decision_versions": sorted(value.accepted_decision_versions),
        "allowed_environments": sorted(value.allowed_environments),
        "allowed_tenants": sorted(value.allowed_tenants),
        "maximum_approval_age_seconds": value.maximum_approval_age_seconds,
        "maximum_decision_age_seconds": value.maximum_decision_age_seconds,
        "minimum_remaining_lifetime_seconds": value.minimum_remaining_lifetime_seconds,
        "policy_id": value.policy_id, "required_conditions": sorted(value.required_conditions),
        "version": value.version,
    }


def authorization_policy_digest(value: AuthorizationPolicy) -> str:
    return sha256(canonical_authorization_json(authorization_policy_document(value))).hexdigest()


def authorization_policy_reference(value: AuthorizationPolicy) -> AuthorizationPolicyReference:
    return AuthorizationPolicyReference(value.policy_id, value.version, authorization_policy_digest(value))


def authorization_request_document(value: DeploymentAuthorizationRequest) -> dict[str, Any]:
    return {
        "approval_attestation_id": value.approval_attestation_id,
        "authorization_policy": asdict(value.authorization_policy),
        "context": {**asdict(value.context), "conditions": list(value.context.conditions)},
        "contract_version": value.contract_version, "correlation_id": value.correlation_id,
        "decision_attestation_id": value.decision_attestation_id,
        "request_id": value.request_id, "requested_at": _timestamp(value.requested_at),
    }


def translate_untrusted_authorization_request(
    value: bytes | str | Mapping[str, Any],
) -> DeploymentAuthorizationRequest:
    try:
        raw = value.encode() if isinstance(value, str) else value if isinstance(value, bytes) else None
        document = json.loads(raw) if raw is not None else dict(value)
        fields = {"request_id", "decision_attestation_id", "approval_attestation_id", "context",
                  "authorization_policy", "requested_at", "correlation_id", "contract_version"}
        context_fields = {"artifact_id", "artifact_digest", "tenant_id", "environment",
                          "release_id", "scope", "conditions"}
        policy_fields = {"policy_id", "version", "digest"}
        if not isinstance(document, dict) or set(document) != fields:
            raise ValueError
        if not isinstance(document["context"], dict) or set(document["context"]) != context_fields:
            raise ValueError
        if not isinstance(document["authorization_policy"], dict) or set(
            document["authorization_policy"]
        ) != policy_fields:
            raise ValueError
        if not isinstance(document["context"]["conditions"], list):
            raise ValueError
        request = DeploymentAuthorizationRequest(
            **{**document, "context": DeploymentContext(
                **{**document["context"], "conditions": tuple(document["context"]["conditions"])}),
               "authorization_policy": AuthorizationPolicyReference(**document["authorization_policy"]),
               "requested_at": _parse_time(document["requested_at"])})
        if raw is not None and raw != canonical_authorization_json(document):
            raise ValueError
        return request
    except Exception as error:
        raise AuthorizationDocumentError("Deployment authorization request is invalid.") from error


def _decision_document_digest(value: DecisionAttestation) -> str:
    document = asdict(value)
    document["decision"]["state"] = value.decision.state.value
    for index, outcome in enumerate(value.decision.requirement_outcomes):
        document["decision"]["requirement_outcomes"][index]["state"] = outcome.state.value
    document["decided_at"] = _timestamp(value.decided_at)
    document["expires_at"] = _timestamp(value.expires_at)
    return sha256(canonical_decision_json(document)).hexdigest()


def _approval_document_digest(value: ApprovalAttestation) -> str:
    document = asdict(value)
    document["request"]["valid_from"] = _timestamp(value.request.valid_from)
    document["request"]["valid_until"] = _timestamp(value.request.valid_until)
    document["decision"]["state"] = value.decision.state.value
    document["issued_at"] = _timestamp(value.issued_at)
    return sha256(canonical_approval_json(document)).hexdigest()


def verify_decision_reference(value: DecisionAttestation, *, policy: PolicyContract,
                              observed_at: datetime,
                              signature_verifier: Callable[[bytes, bytes], bool]) -> VerifiedDecisionReference | None:
    if (value.decision.state is not DecisionState.SATISFIED or
            not verify_decision_attestation(value, policy=policy, observed_at=observed_at,
                                            signature_verifier=signature_verifier)):
        return None
    return VerifiedDecisionReference(
        value.attestation_id, _decision_document_digest(value), value.system_id, value.policy_id,
        value.policy_version, value.policy_digest, value.artifact_digest, value.tenant_id, value.environment,
        tuple(sorted(set(value.evidence_package_ids + value.evidence_package_digests))),
        value.decided_at, value.expires_at, value.contract_version,
    )


def verify_approval_reference(value: ApprovalAttestation, *,
                              history: tuple[ApprovalLifecycleEvent, ...], observed_at: datetime,
                              signature_verifier: Callable[[bytes, bytes], bool]) -> VerifiedApprovalReference | None:
    request = value.request
    if any(event.approval_id != value.approval_id
           or event.artifact_digest != request.artifact.artifact_digest
           or event.environment != request.target.environment
           or event.decision_attestation_id != request.decision_attestation_id for event in history):
        return None
    if not verify_approval_attestation(value, observed_at=observed_at,
                                       signature_verifier=signature_verifier,
                                       artifact=request.artifact, target=request.target):
        return None
    if current_approval_state(value, history, observed_at=observed_at) not in {
        ApprovalState.APPROVED, ApprovalState.APPROVED_WITH_CONDITIONS,
    }:
        return None
    return VerifiedApprovalReference(
        value.approval_id, _approval_document_digest(value), request.decision_attestation_id,
        request.artifact.artifact_digest, request.target.tenant_id, request.target.environment,
        request.artifact.release_id, request.target.purpose, value.decision.conditions,
        value.issued_at, request.valid_from, request.valid_until, value.contract_version,
    )


def authorize_deployment(
    request: DeploymentAuthorizationRequest, *, decision_attestation: DecisionAttestation | None,
    decision_policy: PolicyContract, decision_signature_verifier: Callable[[bytes, bytes], bool],
    approval_attestation: ApprovalAttestation | None,
    approval_history: tuple[ApprovalLifecycleEvent, ...],
    approval_signature_verifier: Callable[[bytes, bytes], bool],
    authorization_policy: AuthorizationPolicy,
) -> tuple[AuthorizationOutcome, VerifiedDecisionReference | None, VerifiedApprovalReference | None]:
    """Compose approved upstream verifiers without importing their private decision logic."""
    if decision_attestation is None or approval_attestation is None:
        return AuthorizationOutcome(AuthorizationState.INDETERMINATE,
                                    "authorization_indeterminate"), None, None
    if decision_attestation.contract_version not in authorization_policy.accepted_decision_versions:
        return AuthorizationOutcome(AuthorizationState.INVALID,
                                    "unsupported_attestation_version"), None, None
    if approval_attestation.contract_version not in authorization_policy.accepted_approval_versions:
        return AuthorizationOutcome(AuthorizationState.INVALID,
                                    "unsupported_attestation_version"), None, None
    if decision_attestation.decision.state is not DecisionState.SATISFIED:
        return AuthorizationOutcome(AuthorizationState.DENIED, "decision_not_satisfied"), None, None
    if request.requested_at >= decision_attestation.expires_at:
        return AuthorizationOutcome(AuthorizationState.INVALID, "decision_expired"), None, None
    approval_state = current_approval_state(approval_attestation, approval_history,
                                            observed_at=request.requested_at)
    if approval_state is ApprovalState.REVOKED:
        return AuthorizationOutcome(AuthorizationState.INVALID, "approval_revoked"), None, None
    if approval_state is ApprovalState.SUPERSEDED:
        return AuthorizationOutcome(AuthorizationState.INVALID, "approval_superseded"), None, None
    if approval_state is ApprovalState.EXPIRED:
        return AuthorizationOutcome(AuthorizationState.INVALID, "approval_expired"), None, None
    decision = verify_decision_reference(
        decision_attestation, policy=decision_policy, observed_at=request.requested_at,
        signature_verifier=decision_signature_verifier)
    approval = verify_approval_reference(
        approval_attestation, history=approval_history, observed_at=request.requested_at,
        signature_verifier=approval_signature_verifier)
    outcome = decide_deployment_authorization(request, decision=decision, approval=approval,
                                              policy=authorization_policy)
    return outcome, decision, approval


def decide_deployment_authorization(request: DeploymentAuthorizationRequest, *,
                                    decision: VerifiedDecisionReference | None,
                                    approval: VerifiedApprovalReference | None,
                                    policy: AuthorizationPolicy) -> AuthorizationOutcome:
    now = request.requested_at
    if request.authorization_policy != authorization_policy_reference(policy):
        return AuthorizationOutcome(AuthorizationState.INVALID, "policy_mismatch")
    if decision is None:
        return AuthorizationOutcome(AuthorizationState.INVALID, "decision_attestation_invalid")
    if approval is None:
        return AuthorizationOutcome(AuthorizationState.INVALID, "approval_attestation_invalid")
    if decision.attestation_id != request.decision_attestation_id:
        return AuthorizationOutcome(AuthorizationState.INVALID, "decision_attestation_mismatch")
    if approval.approval_id != request.approval_attestation_id:
        return AuthorizationOutcome(AuthorizationState.INVALID, "approval_attestation_mismatch")
    if approval.decision_attestation_id != decision.attestation_id:
        return AuthorizationOutcome(AuthorizationState.INVALID, "decision_approval_mismatch")
    context = request.context
    checks = (
        (decision.artifact_id == context.artifact_id, "artifact_mismatch"),
        (decision.artifact_digest == approval.artifact_digest == context.artifact_digest, "artifact_mismatch"),
        (decision.tenant_id == approval.tenant_id == context.tenant_id, "tenant_mismatch"),
        (decision.environment == approval.environment == context.environment, "environment_mismatch"),
        (approval.release_id == context.release_id, "release_mismatch"),
        (approval.scope == context.scope, "scope_mismatch"),
        (approval.conditions == context.conditions, "conditions_not_preserved"),
    )
    for valid, reason in checks:
        if not valid:
            return AuthorizationOutcome(AuthorizationState.DENIED, reason)
    if (decision.contract_version not in policy.accepted_decision_versions or
            approval.contract_version not in policy.accepted_approval_versions):
        return AuthorizationOutcome(AuthorizationState.INVALID, "unsupported_attestation_version")
    if context.environment not in policy.allowed_environments:
        return AuthorizationOutcome(AuthorizationState.DENIED, "environment_not_authorized")
    if context.tenant_id not in policy.allowed_tenants:
        return AuthorizationOutcome(AuthorizationState.DENIED, "tenant_not_authorized")
    if not policy.required_conditions.issubset(context.conditions):
        return AuthorizationOutcome(AuthorizationState.DENIED, "conditions_not_preserved")
    if not decision.decided_at <= now < decision.expires_at:
        return AuthorizationOutcome(AuthorizationState.INVALID, "decision_expired")
    if not approval.valid_from <= now < approval.expires_at:
        return AuthorizationOutcome(AuthorizationState.INVALID, "approval_expired")
    if (now - decision.decided_at).total_seconds() > policy.maximum_decision_age_seconds:
        return AuthorizationOutcome(AuthorizationState.DENIED, "decision_expired")
    if (now - approval.issued_at).total_seconds() > policy.maximum_approval_age_seconds:
        return AuthorizationOutcome(AuthorizationState.DENIED, "approval_expired")
    expires_at = min(decision.expires_at, approval.expires_at)
    if (expires_at - now).total_seconds() < policy.minimum_remaining_lifetime_seconds:
        return AuthorizationOutcome(AuthorizationState.DENIED, "authorization_lifetime_insufficient")
    return AuthorizationOutcome(AuthorizationState.AUTHORIZED, "deployment_authorized", now,
                                expires_at, approval.conditions)


def _attestation_document(value: DeploymentAuthorizationAttestation, *, include_signature: bool = True,
                          include_identity: bool = True, include_payload_digest: bool = True) -> dict[str, Any]:
    document = asdict(value)
    document["outcome"] = value.outcome.value
    for name in ("issued_at", "valid_from", "expires_at"):
        document[name] = _timestamp(getattr(value, name))
    if not include_signature:
        document.pop("signature")
    if not include_identity:
        document.pop("authorization_id")
    if not include_payload_digest:
        document.pop("payload_digest")
    return document


def build_deployment_authorization_attestation(
    request: DeploymentAuthorizationRequest, outcome: AuthorizationOutcome, *,
    decision: VerifiedDecisionReference, approval: VerifiedApprovalReference,
    issuer_id: str, key_id: str, signer: Callable[[bytes], bytes],
) -> DeploymentAuthorizationAttestation:
    if not outcome.authorized or outcome.valid_from is None or outcome.expires_at is None:
        raise ValueError("only an authorized outcome may produce an attestation.")
    values: dict[str, Any] = dict(
        authorization_id="0" * 64, outcome=outcome.state,
        artifact_id=request.context.artifact_id, artifact_digest=request.context.artifact_digest,
        release_id=request.context.release_id, tenant_id=request.context.tenant_id,
        environment=request.context.environment, scope=request.context.scope,
        decision_attestation_id=decision.attestation_id,
        decision_attestation_digest=decision.attestation_digest,
        approval_attestation_id=approval.approval_id,
        approval_attestation_digest=approval.approval_digest,
        authorization_policy_id=request.authorization_policy.policy_id,
        authorization_policy_version=request.authorization_policy.version,
        authorization_policy_digest=request.authorization_policy.digest,
        conditions=outcome.preserved_conditions, issued_at=request.requested_at,
        valid_from=outcome.valid_from, expires_at=outcome.expires_at,
        issuer_id=issuer_id, key_id=key_id, correlation_id=request.correlation_id,
        payload_digest="0" * 64, signature="0" * 128,
    )
    draft = DeploymentAuthorizationAttestation(**values)
    values["payload_digest"] = sha256(canonical_authorization_json(
        _attestation_document(draft, include_signature=False, include_identity=False,
                              include_payload_digest=False))).hexdigest()
    draft = DeploymentAuthorizationAttestation(**values)
    values["authorization_id"] = sha256(canonical_authorization_json(
        _attestation_document(draft, include_signature=False, include_identity=False))).hexdigest()
    draft = DeploymentAuthorizationAttestation(**values)
    values["signature"] = signer(canonical_authorization_json(
        _attestation_document(draft, include_signature=False))).hex()
    return DeploymentAuthorizationAttestation(**values)


def append_authorization_lifecycle_record(
    history: tuple[AuthorizationLifecycleRecord, ...], *, authorization_id: str,
    event_type: AuthorizationEventType, actor_id: str, reason_code: str, occurred_at: datetime,
) -> tuple[AuthorizationLifecycleRecord, ...]:
    occurred_at = decision_utc(occurred_at, "occurred_at")
    previous = history[-1].record_id if history else None
    seed = {"actor_id": actor_id, "authorization_id": authorization_id,
            "event_type": event_type.value, "occurred_at": _timestamp(occurred_at),
            "previous_record_id": previous, "reason_code": reason_code}
    record = AuthorizationLifecycleRecord(sha256(canonical_authorization_json(seed)).hexdigest(),
                                          authorization_id, event_type, actor_id, reason_code,
                                          occurred_at, previous)
    return history + (record,)


def verify_authorization_history(history: tuple[AuthorizationLifecycleRecord, ...]) -> bool:
    seen: set[str] = set()
    previous: str | None = None
    first_id = history[0].authorization_id if history else None
    previous_time: datetime | None = None
    for record in history:
        seed = {"actor_id": record.actor_id, "authorization_id": record.authorization_id,
                "event_type": record.event_type.value, "occurred_at": _timestamp(record.occurred_at),
                "previous_record_id": record.previous_record_id, "reason_code": record.reason_code}
        if (record.record_id in seen or record.record_id != sha256(canonical_authorization_json(seed)).hexdigest()
                or record.previous_record_id != previous or record.authorization_id != first_id
                or (previous_time is not None and record.occurred_at < previous_time)):
            return False
        seen.add(record.record_id)
        previous, previous_time = record.record_id, record.occurred_at
    return True


def verify_deployment_authorization(
    value: DeploymentAuthorizationAttestation | None, *,
    history: tuple[AuthorizationLifecycleRecord, ...], observed_at: datetime,
    signature_verifier: Callable[[str, bytes, bytes], bool], context: DeploymentContext,
) -> AuthorizationVerificationResult:
    if value is None:
        return AuthorizationVerificationResult(False, False, False, None,
                                               AuthorizationLifecycleState.INVALID,
                                               "authorization_missing", None, None, (), None)
    try:
        observed_at = decision_utc(observed_at, "observed_at")
        expected_payload = sha256(canonical_authorization_json(
            _attestation_document(value, include_signature=False, include_identity=False,
                                  include_payload_digest=False))).hexdigest()
        expected_id = sha256(canonical_authorization_json(
            _attestation_document(value, include_signature=False, include_identity=False))).hexdigest()
        authentic = (value.contract_version == AUTHORIZATION_CONTRACT_VERSION
                     and value.payload_digest == expected_payload and value.authorization_id == expected_id
                     and signature_verifier(value.key_id, canonical_authorization_json(
                         _attestation_document(value, include_signature=False)), bytes.fromhex(value.signature)))
        if not authentic or not verify_authorization_history(history):
            raise ValueError
        matching = (value.artifact_id == context.artifact_id
                    and value.artifact_digest == context.artifact_digest
                    and value.tenant_id == context.tenant_id and value.environment == context.environment
                    and value.release_id == context.release_id and value.scope == context.scope
                    and value.conditions == context.conditions)
        if not matching:
            return AuthorizationVerificationResult(True, True, False, value.authorization_id,
                                                   AuthorizationLifecycleState.ACTIVE,
                                                   "authorization_not_applicable", value.artifact_digest,
                                                   value.environment, value.conditions, value.expires_at)
        state = AuthorizationLifecycleState.ACTIVE
        reason = "deployment_authorized"
        if observed_at < value.valid_from:
            state, reason = AuthorizationLifecycleState.INVALID, "authorization_not_yet_active"
        elif observed_at >= value.expires_at:
            state, reason = AuthorizationLifecycleState.EXPIRED, "authorization_expired"
        elif history and history[-1].event_type is AuthorizationEventType.REVOKED:
            state, reason = AuthorizationLifecycleState.REVOKED, "authorization_revoked"
        elif history and history[-1].event_type is AuthorizationEventType.SUPERSEDED:
            state, reason = AuthorizationLifecycleState.SUPERSEDED, "authorization_superseded"
        active = state is AuthorizationLifecycleState.ACTIVE
        return AuthorizationVerificationResult(True, active, active, value.authorization_id, state,
                                               reason, value.artifact_digest, value.environment,
                                               value.conditions, value.expires_at)
    except Exception:
        return AuthorizationVerificationResult(False, False, False, value.authorization_id,
                                               AuthorizationLifecycleState.INVALID,
                                               "authorization_invalid", value.artifact_digest,
                                               value.environment, (), value.expires_at)


def public_authorization_result(outcome: AuthorizationOutcome, *,
                                attestation: DeploymentAuthorizationAttestation | None = None,
                                request: DeploymentAuthorizationRequest | None = None,
) -> PublicAuthorizationResult:
    return PublicAuthorizationResult(
        outcome.authorized and attestation is not None, outcome.state, outcome.reason_code,
        attestation.authorization_id if attestation else None, AUTHORIZATION_CONTRACT_VERSION,
        request.context.artifact_id if request else None,
        request.context.artifact_digest if request else None,
        request.context.environment if request else None,
        attestation.issued_at if attestation else None, attestation.expires_at if attestation else None,
    )
