from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any, Callable, Mapping

from src.reference_architecture_policy_decision_contract import (
    POLICY_DECISION_CONTRACT_VERSION, POLICY_DECISION_DIGEST_ALGORITHM,
    POLICY_DECISION_SERIALIZATION_ALGORITHM, DecisionState, IndeterminateRule,
    PolicyContract, PolicyDecision, PolicyDecisionRequest, PolicyRequirement,
    RequirementLevel, RequirementOperator, RequirementOutcome, VerifiedEvidence,
    decision_digest, decision_identifier, decision_signature, decision_utc,
)


class PolicyDocumentError(ValueError):
    pass


def canonical_decision_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def _timestamp(value: datetime) -> str:
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_time(value: object) -> datetime:
    if type(value) is not str or len(value) != 20 or not value.endswith("Z"):
        raise ValueError
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def policy_document(policy: PolicyContract) -> dict[str, Any]:
    return {
        "active_from": _timestamp(policy.active_from), "contract_version": policy.contract_version,
        "environment": policy.environment, "expires_at": _timestamp(policy.expires_at),
        "indeterminate_rule": policy.indeterminate_rule.value, "owner_id": policy.owner_id,
        "policy_id": policy.policy_id,
        "requirements": [{"evidence_type": r.evidence_type, "expected": r.expected,
                          "field": r.field, "level": r.level.value,
                          "operator": r.operator.value, "requirement_id": r.requirement_id}
                         for r in policy.requirements],
        "system_type": policy.system_type, "version": policy.version,
    }


def policy_digest(policy: PolicyContract) -> str:
    return sha256(canonical_decision_json(policy_document(policy))).hexdigest()


def translate_untrusted_policy(value: bytes | str | Mapping[str, Any]) -> PolicyContract:
    try:
        raw = value.encode() if isinstance(value, str) else value if isinstance(value, bytes) else None
        document = json.loads(raw) if raw is not None else dict(value)
        fields = {"policy_id", "version", "owner_id", "system_type", "environment", "active_from",
                  "expires_at", "requirements", "indeterminate_rule", "contract_version"}
        if not isinstance(document, dict) or set(document) != fields:
            raise ValueError
        requirements = document["requirements"]
        rfields = {"requirement_id", "evidence_type", "field", "operator", "expected", "level"}
        if not isinstance(requirements, list) or any(
            not isinstance(item, dict) or set(item) != rfields for item in requirements
        ):
            raise ValueError
        policy = PolicyContract(
            **{**document, "active_from": _parse_time(document["active_from"]),
               "expires_at": _parse_time(document["expires_at"]),
               "indeterminate_rule": IndeterminateRule(document["indeterminate_rule"]),
               "requirements": tuple(PolicyRequirement(
                   **{**item, "operator": RequirementOperator(item["operator"]),
                      "level": RequirementLevel(item["level"]),
                      "expected": tuple(item["expected"]) if item["operator"] in {"in", "not_in"}
                      and isinstance(item["expected"], list) else item["expected"]})
                   for item in requirements)})
        if raw is not None and raw != canonical_decision_json(document):
            raise ValueError
        return policy
    except Exception as error:
        raise PolicyDocumentError("Policy document is invalid.") from error


def decision_request_document(request: PolicyDecisionRequest) -> dict[str, Any]:
    return {
        "artifact_digest": request.artifact_digest,
        "environment": request.environment,
        "evaluated_at": _timestamp(request.evaluated_at),
        "evidence": [{
            "evidence_id": item.evidence_id, "package_id": item.package_id,
            "package_digest": item.package_digest, "evidence_type": item.evidence_type,
            "tenant_id": item.tenant_id, "environment": item.environment,
            "produced_at": _timestamp(item.produced_at), "values": dict(item.values),
            "provenance_verified": item.provenance_verified,
            "signer_authorized": item.signer_authorized, "ledger_admitted": item.ledger_admitted,
            "lifecycle_active": item.lifecycle_active,
            "transparency_included": item.transparency_included,
        } for item in request.evidence],
        "expires_at": _timestamp(request.expires_at), "policy": policy_document(request.policy),
        "request_id": request.request_id, "system_id": request.system_id,
        "tenant_id": request.tenant_id,
    }


def translate_untrusted_decision_request(value: bytes | str | Mapping[str, Any]) -> PolicyDecisionRequest:
    try:
        raw = value.encode() if isinstance(value, str) else value if isinstance(value, bytes) else None
        document = json.loads(raw) if raw is not None else dict(value)
        fields = {"request_id", "policy", "evidence", "tenant_id", "system_id",
                  "artifact_digest", "environment", "evaluated_at", "expires_at"}
        efields = {"evidence_id", "package_id", "package_digest", "evidence_type", "tenant_id",
                   "environment", "produced_at", "values", "provenance_verified",
                   "signer_authorized", "ledger_admitted", "lifecycle_active", "transparency_included"}
        if not isinstance(document, dict) or set(document) != fields or not isinstance(document["evidence"], list):
            raise ValueError
        if any(not isinstance(item, dict) or set(item) != efields for item in document["evidence"]):
            raise ValueError
        result = PolicyDecisionRequest(
            **{**document, "policy": translate_untrusted_policy(document["policy"]),
               "evidence": tuple(VerifiedEvidence(**{**item, "produced_at": _parse_time(item["produced_at"])})
                                 for item in document["evidence"]),
               "evaluated_at": _parse_time(document["evaluated_at"]),
               "expires_at": _parse_time(document["expires_at"])})
        if raw is not None and raw != canonical_decision_json(document):
            raise ValueError
        return result
    except Exception as error:
        raise PolicyDocumentError("Decision request document is invalid.") from error


def _requirement(requirement: PolicyRequirement, evidence: tuple[VerifiedEvidence, ...],
                 observed_at: datetime) -> RequirementOutcome:
    matches = tuple(item for item in evidence if item.evidence_type == requirement.evidence_type)
    ids = tuple(item.evidence_id for item in matches)
    if not matches:
        return RequirementOutcome(requirement.requirement_id, DecisionState.INDETERMINATE,
                                  "required_evidence_missing", ())
    if any(not item.trusted for item in matches):
        return RequirementOutcome(requirement.requirement_id, DecisionState.INDETERMINATE,
                                  "evidence_not_trusted", ids)
    values = [item.values.get(requirement.field) for item in matches if requirement.field in item.values]
    if not values:
        return RequirementOutcome(requirement.requirement_id, DecisionState.INDETERMINATE,
                                  "evidence_value_missing", ids)
    if len({canonical_decision_json(value) for value in values}) > 1:
        return RequirementOutcome(requirement.requirement_id, DecisionState.INDETERMINATE,
                                  "evidence_conflict", ids)
    value = values[0]
    try:
        op, expected = requirement.operator, requirement.expected
        passed = {
            RequirementOperator.EQUALS: lambda: value == expected,
            RequirementOperator.NOT_EQUALS: lambda: value != expected,
            RequirementOperator.MINIMUM: lambda: not isinstance(value, bool) and value >= expected,
            RequirementOperator.MAXIMUM: lambda: not isinstance(value, bool) and value <= expected,
            RequirementOperator.IN: lambda: value in expected,
            RequirementOperator.NOT_IN: lambda: value not in expected,
            RequirementOperator.PRESENT: lambda: value is not None,
            RequirementOperator.ABSENT: lambda: value is None,
            RequirementOperator.FRESH_WITHIN_SECONDS: lambda: all(
                0 <= (observed_at - item.produced_at).total_seconds() <= expected for item in matches),
        }[op]()
    except (TypeError, ValueError):
        return RequirementOutcome(requirement.requirement_id, DecisionState.INDETERMINATE,
                                  "evidence_uninterpretable", ids)
    return RequirementOutcome(requirement.requirement_id,
                              DecisionState.SATISFIED if passed else DecisionState.NOT_SATISFIED,
                              "requirement_satisfied" if passed else "requirement_failed", ids)


def evaluate_policy(request: PolicyDecisionRequest) -> PolicyDecision:
    now, policy = request.evaluated_at, request.policy
    if not policy.active_from <= now < policy.expires_at:
        return PolicyDecision(DecisionState.INVALID, "policy_expired", ())
    if len({item.evidence_id for item in request.evidence}) != len(request.evidence):
        return PolicyDecision(DecisionState.INVALID, "evidence_not_trusted", ())
    if policy.environment != request.environment or any(
        item.tenant_id != request.tenant_id or item.environment != request.environment
        or item.produced_at > now for item in request.evidence
    ):
        return PolicyDecision(DecisionState.INVALID, "evidence_not_trusted", ())
    outcomes = tuple(_requirement(item, request.evidence, now) for item in policy.requirements)
    mandatory = tuple(result for result, requirement in zip(outcomes, policy.requirements)
                      if requirement.level is RequirementLevel.MANDATORY)
    if any(item.state is DecisionState.NOT_SATISFIED for item in mandatory):
        state, reason = DecisionState.NOT_SATISFIED, "mandatory_requirement_failed"
    elif any(item.state is DecisionState.INDETERMINATE for item in mandatory):
        if policy.indeterminate_rule is IndeterminateRule.FAIL:
            state, reason = DecisionState.NOT_SATISFIED, "mandatory_requirement_failed"
        else:
            state, reason = DecisionState.INDETERMINATE, "decision_indeterminate"
    else:
        state, reason = DecisionState.SATISFIED, "policy_satisfied"
    return PolicyDecision(state, reason, outcomes)


@dataclass(frozen=True, slots=True)
class DecisionAttestation:
    attestation_id: str
    request_id: str
    evidence_package_ids: tuple[str, ...]
    evidence_package_digests: tuple[str, ...]
    policy_id: str
    policy_version: str
    policy_digest: str
    tenant_id: str
    system_id: str
    artifact_digest: str
    environment: str
    decision: PolicyDecision
    decided_at: datetime
    expires_at: datetime
    authority_id: str
    previous_attestation_id: str | None
    signature: str
    contract_version: str = POLICY_DECISION_CONTRACT_VERSION
    serialization_algorithm: str = POLICY_DECISION_SERIALIZATION_ALGORITHM
    digest_algorithm: str = POLICY_DECISION_DIGEST_ALGORITHM

    def __post_init__(self) -> None:
        decision_digest(self.attestation_id, "attestation_id")
        decision_digest(self.artifact_digest, "artifact_digest")
        decision_digest(self.policy_digest, "policy_digest")
        decision_signature(self.signature, "signature")
        for item in self.evidence_package_ids + self.evidence_package_digests:
            decision_digest(item, "evidence package binding")
        for value, name in ((self.request_id, "request_id"), (self.policy_id, "policy_id"),
                            (self.policy_version, "policy_version"), (self.tenant_id, "tenant_id"),
                            (self.system_id, "system_id"), (self.environment, "environment"),
                            (self.authority_id, "authority_id")):
            decision_identifier(value, name)
        object.__setattr__(self, "decided_at", decision_utc(self.decided_at, "decided_at"))
        object.__setattr__(self, "expires_at", decision_utc(self.expires_at, "expires_at"))


def _decision_doc(value: DecisionAttestation, *, include_signature: bool = True,
                  include_id: bool = True) -> dict[str, Any]:
    document = asdict(value)
    document["decision"]["state"] = value.decision.state.value
    for index, outcome in enumerate(value.decision.requirement_outcomes):
        document["decision"]["requirement_outcomes"][index]["state"] = outcome.state.value
    document["decided_at"], document["expires_at"] = _timestamp(value.decided_at), _timestamp(value.expires_at)
    if not include_signature:
        document.pop("signature")
    if not include_id:
        document.pop("attestation_id")
    return document


def build_decision_attestation(request: PolicyDecisionRequest, decision: PolicyDecision,
                               *, authority_id: str,
                               signer: Callable[[bytes], bytes],
                               previous_attestation_id: str | None = None) -> DecisionAttestation:
    values = dict(attestation_id="0" * 64, request_id=request.request_id,
                  evidence_package_ids=tuple(sorted({x.package_id for x in request.evidence})),
                  evidence_package_digests=tuple(sorted({x.package_digest for x in request.evidence})),
                  policy_id=request.policy.policy_id, policy_version=request.policy.version,
                  policy_digest=policy_digest(request.policy), tenant_id=request.tenant_id,
                  system_id=request.system_id, artifact_digest=request.artifact_digest,
                  environment=request.environment, decision=decision, decided_at=request.evaluated_at,
                  expires_at=request.expires_at, authority_id=authority_id,
                  previous_attestation_id=previous_attestation_id, signature="0" * 128)
    draft = DecisionAttestation(**values)
    values["attestation_id"] = sha256(canonical_decision_json(
        _decision_doc(draft, include_signature=False, include_id=False))).hexdigest()
    draft = DecisionAttestation(**values)
    values["signature"] = signer(canonical_decision_json(_decision_doc(draft, include_signature=False))).hex()
    return DecisionAttestation(**values)


def verify_decision_attestation(value: DecisionAttestation, *, policy: PolicyContract,
                                observed_at: datetime,
                                signature_verifier: Callable[[bytes, bytes], bool]) -> bool:
    try:
        observed_at = decision_utc(observed_at, "observed_at")
        if value.policy_digest != policy_digest(policy) or value.policy_id != policy.policy_id or value.policy_version != policy.version:
            return False
        expected_id = sha256(canonical_decision_json(
            _decision_doc(value, include_signature=False, include_id=False))).hexdigest()
        return (value.attestation_id == expected_id and value.decided_at <= observed_at < value.expires_at
                and signature_verifier(canonical_decision_json(_decision_doc(value, include_signature=False)),
                                       bytes.fromhex(value.signature)))
    except Exception:
        return False


@dataclass(frozen=True, slots=True)
class PublicDecisionOutcome:
    state: DecisionState
    reason_code: str
    attestation_id: str | None
    policy_id: str | None
    policy_version: str | None
    artifact_digest: str | None
    environment: str | None
    expires_at: datetime | None


def public_decision_outcome(decision: PolicyDecision, *, attestation: DecisionAttestation | None = None
                            ) -> PublicDecisionOutcome:
    return PublicDecisionOutcome(decision.state, decision.reason_code,
                                 attestation.attestation_id if attestation else None,
                                 attestation.policy_id if attestation else None,
                                 attestation.policy_version if attestation else None,
                                 attestation.artifact_digest if attestation else None,
                                 attestation.environment if attestation else None,
                                 attestation.expires_at if attestation else None)
