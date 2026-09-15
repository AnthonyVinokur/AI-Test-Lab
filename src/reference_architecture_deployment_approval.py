from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any, Callable, Mapping

from src.reference_architecture_deployment_approval_contract import (
    APPROVAL_CONTRACT_VERSION, ApprovalDecision, ApprovalEventType, ApprovalRequest,
    ApprovalRules, ApprovalState, ApproverGrant, ArtifactBinding, DeploymentTarget,
)
from src.reference_architecture_policy_decision import DecisionAttestation
from src.reference_architecture_policy_decision_contract import DecisionState, decision_digest, decision_signature, decision_utc


class ApprovalDocumentError(ValueError):
    pass


def canonical_approval_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def _timestamp(value: datetime) -> str:
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_time(value: object) -> datetime:
    if type(value) is not str or len(value) != 20 or not value.endswith("Z"):
        raise ValueError
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def approval_request_document(value: ApprovalRequest) -> dict[str, Any]:
    document = asdict(value)
    document["valid_from"], document["valid_until"] = _timestamp(value.valid_from), _timestamp(value.valid_until)
    return document


def translate_untrusted_approval_request(value: bytes | str | Mapping[str, Any], *,
                                         allowed_environments: frozenset[str] | None = None) -> ApprovalRequest:
    try:
        raw = value.encode() if isinstance(value, str) else value if isinstance(value, bytes) else None
        document = json.loads(raw) if raw is not None else dict(value)
        fields = {"request_id", "decision_attestation_id", "artifact", "target", "requester_id",
                  "policy_category", "risk_level", "valid_from", "valid_until", "conditions",
                  "contract_version"}
        afields = {"artifact_digest", "configuration_digest", "provider", "model_version",
                   "release_id", "prompt_version", "dataset_version"}
        tfields = {"tenant_id", "environment", "region", "purpose"}
        if not isinstance(document, dict) or set(document) != fields:
            raise ValueError
        if not isinstance(document["artifact"], dict) or set(document["artifact"]) != afields:
            raise ValueError
        if not isinstance(document["target"], dict) or set(document["target"]) != tfields:
            raise ValueError
        target = DeploymentTarget(**document["target"])
        if allowed_environments is not None and target.environment not in allowed_environments:
            raise ValueError
        request = ApprovalRequest(**{**document, "artifact": ArtifactBinding(**document["artifact"]),
                                     "target": target, "conditions": tuple(document["conditions"]),
                                     "valid_from": _parse_time(document["valid_from"]),
                                     "valid_until": _parse_time(document["valid_until"])})
        if raw is not None and raw != canonical_approval_json(document):
            raise ValueError
        return request
    except Exception as error:
        raise ApprovalDocumentError("Approval request document is invalid.") from error


def decide_approval(request: ApprovalRequest, *, decision_attestation: DecisionAttestation,
                    decision_attestation_valid: bool, approver_grants: tuple[ApproverGrant, ...],
                    approver_ids: tuple[str, ...], rules: ApprovalRules,
                    evaluator_id: str, observed_at: datetime) -> ApprovalDecision:
    observed_at = decision_utc(observed_at, "observed_at")
    if not decision_attestation_valid:
        return ApprovalDecision(ApprovalState.INVALID, "approval_attestation_invalid", ())
    if decision_attestation.decision.state is not DecisionState.SATISFIED:
        return ApprovalDecision(ApprovalState.DENIED, "decision_not_satisfied", ())
    if (request.decision_attestation_id != decision_attestation.attestation_id or
            request.artifact.artifact_digest != decision_attestation.artifact_digest):
        return ApprovalDecision(ApprovalState.DENIED, "artifact_mismatch", ())
    if (request.target.tenant_id != decision_attestation.tenant_id or
            request.target.environment != decision_attestation.environment):
        return ApprovalDecision(ApprovalState.DENIED, "environment_mismatch", ())
    if not (decision_attestation.decided_at <= observed_at < decision_attestation.expires_at):
        return ApprovalDecision(ApprovalState.DENIED, "decision_not_satisfied", ())
    unique = tuple(dict.fromkeys(approver_ids))
    if len(unique) != len(approver_ids):
        return ApprovalDecision(ApprovalState.PENDING, "quorum_not_satisfied", unique)
    grants = {grant.actor_id: grant for grant in approver_grants}
    authorized: list[str] = []
    roles: set[str] = set()
    duration = int((request.valid_until - request.valid_from).total_seconds())
    for actor in unique:
        grant = grants.get(actor)
        if grant is None or not (grant.valid_from <= observed_at < grant.valid_until):
            continue
        if (grant.tenant_id != request.target.tenant_id or request.target.environment not in grant.environments
                or request.policy_category not in grant.policy_categories
                or request.risk_level > grant.max_risk_level or duration > grant.max_duration_seconds):
            continue
        if rules.prohibit_evaluator and actor == evaluator_id:
            continue
        authorized.append(actor)
        roles.update(grant.roles)
    if any(actor not in authorized for actor in unique):
        return ApprovalDecision(ApprovalState.DENIED, "approver_not_authorized", tuple(authorized))
    if rules.prohibit_sole_requester and len(authorized) == 1 and authorized[0] == request.requester_id:
        return ApprovalDecision(ApprovalState.PENDING, "quorum_not_satisfied", tuple(authorized))
    if len(authorized) < rules.quorum or not rules.required_roles.issubset(roles):
        return ApprovalDecision(ApprovalState.PENDING, "quorum_not_satisfied", tuple(authorized))
    state = ApprovalState.APPROVED_WITH_CONDITIONS if request.conditions else ApprovalState.APPROVED
    return ApprovalDecision(state, "deployment_authorized", tuple(sorted(authorized)), request.conditions)


@dataclass(frozen=True, slots=True)
class ApprovalAttestation:
    approval_id: str
    request: ApprovalRequest
    decision: ApprovalDecision
    issued_at: datetime
    previous_approval_id: str | None
    signature: str
    contract_version: str = APPROVAL_CONTRACT_VERSION

    def __post_init__(self) -> None:
        decision_digest(self.approval_id, "approval_id")
        decision_signature(self.signature, "signature")
        if self.previous_approval_id is not None:
            decision_digest(self.previous_approval_id, "previous_approval_id")
        object.__setattr__(self, "issued_at", decision_utc(self.issued_at, "issued_at"))


def _attestation_doc(value: ApprovalAttestation, *, signature: bool = True,
                     identity: bool = True) -> dict[str, Any]:
    document = asdict(value)
    document["request"] = approval_request_document(value.request)
    document["decision"]["state"] = value.decision.state.value
    document["issued_at"] = _timestamp(value.issued_at)
    if not signature:
        document.pop("signature")
    if not identity:
        document.pop("approval_id")
    return document


def build_approval_attestation(request: ApprovalRequest, decision: ApprovalDecision, *,
                               issued_at: datetime, signer: Callable[[bytes], bytes],
                               previous_approval_id: str | None = None) -> ApprovalAttestation:
    values = dict(approval_id="0" * 64, request=request, decision=decision, issued_at=issued_at,
                  previous_approval_id=previous_approval_id, signature="0" * 128)
    draft = ApprovalAttestation(**values)
    values["approval_id"] = sha256(canonical_approval_json(
        _attestation_doc(draft, signature=False, identity=False))).hexdigest()
    draft = ApprovalAttestation(**values)
    values["signature"] = signer(canonical_approval_json(_attestation_doc(draft, signature=False))).hex()
    return ApprovalAttestation(**values)


def verify_approval_attestation(value: ApprovalAttestation, *, observed_at: datetime,
                                signature_verifier: Callable[[bytes, bytes], bool],
                                artifact: ArtifactBinding, target: DeploymentTarget) -> bool:
    try:
        observed_at = decision_utc(observed_at, "observed_at")
        expected = sha256(canonical_approval_json(
            _attestation_doc(value, signature=False, identity=False))).hexdigest()
        return (value.approval_id == expected and value.request.artifact == artifact
                and value.request.target == target and value.request.valid_from <= observed_at < value.request.valid_until
                and value.decision.state in {ApprovalState.APPROVED, ApprovalState.APPROVED_WITH_CONDITIONS}
                and signature_verifier(canonical_approval_json(_attestation_doc(value, signature=False)),
                                       bytes.fromhex(value.signature)))
    except Exception:
        return False


@dataclass(frozen=True, slots=True)
class ApprovalLifecycleEvent:
    event_id: str
    approval_id: str
    event_type: ApprovalEventType
    actor_id: str
    reason_code: str
    occurred_at: datetime
    previous_event_id: str | None
    artifact_digest: str
    environment: str
    decision_attestation_id: str


def append_approval_event(history: tuple[ApprovalLifecycleEvent, ...], *, approval_id: str,
                          event_type: ApprovalEventType, actor_id: str, reason_code: str,
                          occurred_at: datetime, artifact_digest: str, environment: str,
                          decision_attestation_id: str) -> tuple[ApprovalLifecycleEvent, ...]:
    previous = history[-1].event_id if history else None
    seed = {"actor_id": actor_id, "approval_id": approval_id, "artifact_digest": artifact_digest,
            "decision_attestation_id": decision_attestation_id, "environment": environment,
            "event_type": event_type.value, "occurred_at": _timestamp(decision_utc(occurred_at, "occurred_at")),
            "previous_event_id": previous, "reason_code": reason_code}
    event = ApprovalLifecycleEvent(sha256(canonical_approval_json(seed)).hexdigest(), approval_id,
                                   event_type, actor_id, reason_code, decision_utc(occurred_at, "occurred_at"),
                                   previous, artifact_digest, environment, decision_attestation_id)
    return history + (event,)


def current_approval_state(attestation: ApprovalAttestation,
                           history: tuple[ApprovalLifecycleEvent, ...], *, observed_at: datetime) -> ApprovalState:
    observed_at = decision_utc(observed_at, "observed_at")
    if not verify_approval_history(history):
        return ApprovalState.INVALID
    if observed_at >= attestation.request.valid_until:
        return ApprovalState.EXPIRED
    terminal = {ApprovalEventType.REVOKED: ApprovalState.REVOKED,
                ApprovalEventType.SUPERSEDED: ApprovalState.SUPERSEDED,
                ApprovalEventType.DENIED: ApprovalState.DENIED}
    return terminal.get(history[-1].event_type, attestation.decision.state) if history else attestation.decision.state


def verify_approval_history(history: tuple[ApprovalLifecycleEvent, ...]) -> bool:
    """Verify ordering, hash linkage, context continuity, and duplicate-free event identities."""
    if not history:
        return True
    first = history[0]
    seen: set[str] = set()
    previous: str | None = None
    previous_time: datetime | None = None
    for event in history:
        seed = {"actor_id": event.actor_id, "approval_id": event.approval_id,
                "artifact_digest": event.artifact_digest,
                "decision_attestation_id": event.decision_attestation_id,
                "environment": event.environment, "event_type": event.event_type.value,
                "occurred_at": _timestamp(event.occurred_at),
                "previous_event_id": event.previous_event_id, "reason_code": event.reason_code}
        if (event.event_id in seen or event.event_id != sha256(canonical_approval_json(seed)).hexdigest()
                or event.previous_event_id != previous or event.approval_id != first.approval_id
                or event.artifact_digest != first.artifact_digest
                or event.environment != first.environment
                or event.decision_attestation_id != first.decision_attestation_id
                or (previous_time is not None and event.occurred_at < previous_time)):
            return False
        seen.add(event.event_id)
        previous, previous_time = event.event_id, event.occurred_at
    return True


@dataclass(frozen=True, slots=True)
class PublicApprovalOutcome:
    authorized: bool
    state: ApprovalState
    reason_code: str
    approval_id: str | None
    artifact_digest: str | None
    environment: str | None
    conditions: tuple[str, ...]
    valid_until: datetime | None


def public_approval_outcome(attestation: ApprovalAttestation | None, *, state: ApprovalState | None = None
                            ) -> PublicApprovalOutcome:
    if attestation is None:
        return PublicApprovalOutcome(False, ApprovalState.INVALID, "approval_missing", None, None, None, (), None)
    state = state or attestation.decision.state
    reasons = {ApprovalState.APPROVED: "deployment_authorized",
               ApprovalState.APPROVED_WITH_CONDITIONS: "deployment_authorized",
               ApprovalState.PENDING: "approval_pending", ApprovalState.EXPIRED: "approval_expired",
               ApprovalState.REVOKED: "approval_revoked", ApprovalState.SUPERSEDED: "approval_missing",
               ApprovalState.DENIED: attestation.decision.reason_code,
               ApprovalState.INVALID: "approval_attestation_invalid"}
    return PublicApprovalOutcome(state in {ApprovalState.APPROVED, ApprovalState.APPROVED_WITH_CONDITIONS},
                                 state, reasons[state], attestation.approval_id,
                                 attestation.request.artifact.artifact_digest,
                                 attestation.request.target.environment,
                                 attestation.decision.conditions, attestation.request.valid_until)


def verify_deployment_authorization(attestation: ApprovalAttestation | None, *,
                                    history: tuple[ApprovalLifecycleEvent, ...],
                                    observed_at: datetime,
                                    signature_verifier: Callable[[bytes, bytes], bool],
                                    artifact: ArtifactBinding,
                                    target: DeploymentTarget) -> PublicApprovalOutcome:
    """Fail-closed enforcement interface exposing only the stable public projection."""
    if attestation is None:
        return public_approval_outcome(None)
    if not verify_approval_attestation(attestation, observed_at=observed_at,
                                       signature_verifier=signature_verifier,
                                       artifact=artifact, target=target):
        return public_approval_outcome(attestation, state=ApprovalState.INVALID)
    return public_approval_outcome(
        attestation, state=current_approval_state(attestation, history, observed_at=observed_at)
    )
