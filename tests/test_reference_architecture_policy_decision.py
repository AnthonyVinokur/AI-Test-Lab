from __future__ import annotations

import json
from dataclasses import FrozenInstanceError, asdict, replace
from datetime import datetime, timedelta, timezone

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from src.reference_architecture_policy_decision import (
    build_decision_attestation, canonical_decision_json, evaluate_policy, policy_digest,
    decision_request_document, policy_document, public_decision_outcome,
    translate_untrusted_decision_request, translate_untrusted_policy,
    verify_decision_attestation,
)
from src.reference_architecture_policy_decision_contract import (
    DecisionState, IndeterminateRule, PolicyContract, PolicyDecisionRequest,
    PolicyRequirement, RequirementLevel, RequirementOperator, VerifiedEvidence,
)


NOW = datetime(2026, 9, 15, 12, tzinfo=timezone.utc)
KEY = Ed25519PrivateKey.generate()


def policy(*requirements: PolicyRequirement, **changes: object) -> PolicyContract:
    values = dict(policy_id="enterprise-prod", version="7", owner_id="governance",
                  system_type="llm", environment="production", active_from=NOW - timedelta(days=1),
                  expires_at=NOW + timedelta(days=30), requirements=requirements or (
                      PolicyRequirement("score", "metric", "score", RequirementOperator.MINIMUM, .7),))
    values.update(changes)
    return PolicyContract(**values)  # type: ignore[arg-type]


def evidence(**changes: object) -> VerifiedEvidence:
    values = dict(evidence_id="1" * 64, package_id="2" * 64, package_digest="3" * 64,
                  evidence_type="metric", tenant_id="tenant-a", environment="production",
                  produced_at=NOW - timedelta(minutes=1), values={"score": .8},
                  provenance_verified=True, signer_authorized=True, ledger_admitted=True,
                  lifecycle_active=True, transparency_included=True)
    values.update(changes)
    return VerifiedEvidence(**values)  # type: ignore[arg-type]


def request(**changes: object) -> PolicyDecisionRequest:
    values = dict(request_id="request-1", policy=policy(), evidence=(evidence(),),
                  tenant_id="tenant-a", system_id="system-a", artifact_digest="4" * 64,
                  environment="production", evaluated_at=NOW, expires_at=NOW + timedelta(hours=1))
    values.update(changes)
    return PolicyDecisionRequest(**values)  # type: ignore[arg-type]


def verifier(payload: bytes, signature: bytes) -> bool:
    try:
        KEY.public_key().verify(signature, payload)
        return True
    except Exception:
        return False


def test_contracts_are_immutable_versioned_and_policy_is_content_bound():
    value = policy()
    with pytest.raises(FrozenInstanceError):
        value.version = "8"  # type: ignore[misc]
    assert policy_digest(value) == policy_digest(value)
    assert policy_digest(value) != policy_digest(replace(value, version="8"))


def test_strict_policy_translation_round_trips_and_rejects_attacks():
    document = policy_document(policy())
    raw = canonical_decision_json(document)
    assert translate_untrusted_policy(raw) == policy()
    attacks = [{**document, "extra": True}, {k: v for k, v in document.items() if k != "owner_id"},
               {**document, "version": ""}, {**document, "contract_version": "2.0"},
               {**document, "requirements": document["requirements"] * 2}]
    for attack in attacks:
        with pytest.raises(ValueError, match="Policy document is invalid"):
            translate_untrusted_policy(attack)
    with pytest.raises(ValueError):
        translate_untrusted_policy(json.dumps(document, indent=2))


def test_strict_decision_request_translation_keeps_untrusted_dtos_outside_core():
    value = request()
    document = decision_request_document(value)
    assert translate_untrusted_decision_request(canonical_decision_json(document)) == value
    with pytest.raises(ValueError, match="Decision request document is invalid"):
        translate_untrusted_decision_request({**document, "internal_weight": 10})


@pytest.mark.parametrize(("operator", "expected", "value", "state"), [
    (RequirementOperator.EQUALS, "ok", "ok", DecisionState.SATISFIED),
    (RequirementOperator.NOT_EQUALS, "bad", "ok", DecisionState.SATISFIED),
    (RequirementOperator.MINIMUM, .7, .8, DecisionState.SATISFIED),
    (RequirementOperator.MAXIMUM, .7, .8, DecisionState.NOT_SATISFIED),
    (RequirementOperator.IN, ("a", "b"), "a", DecisionState.SATISFIED),
    (RequirementOperator.NOT_IN, ("bad",), "ok", DecisionState.SATISFIED),
    (RequirementOperator.PRESENT, None, "ok", DecisionState.SATISFIED),
])
def test_public_operators_are_deterministic(operator, expected, value, state):
    requirement = PolicyRequirement("r", "metric", "value", operator, expected)
    result = evaluate_policy(request(policy=policy(requirement), evidence=(evidence(values={"value": value}),)))
    assert result.state is state
    assert result == evaluate_policy(request(policy=policy(requirement), evidence=(evidence(values={"value": value}),)))


def test_untrusted_missing_conflicting_stale_and_mismatched_evidence_fail_closed():
    assert evaluate_policy(request(evidence=(evidence(provenance_verified=False),))).state is DecisionState.INDETERMINATE
    assert evaluate_policy(request(evidence=())).reason_code == "decision_indeterminate"
    conflict = (evidence(), evidence(evidence_id="5" * 64, values={"score": .9}))
    assert evaluate_policy(request(evidence=conflict)).state is DecisionState.INDETERMINATE
    assert evaluate_policy(request(environment="staging")).state is DecisionState.INVALID
    freshness = PolicyRequirement("fresh", "metric", "score",
                                  RequirementOperator.FRESH_WITHIN_SECONDS, 30)
    assert evaluate_policy(request(policy=policy(freshness))).state is DecisionState.NOT_SATISFIED


def test_warning_and_optional_failures_do_not_fail_mandatory_gate():
    requirements = (PolicyRequirement("must", "metric", "score", RequirementOperator.MINIMUM, .7),
                    PolicyRequirement("warn", "metric", "score", RequirementOperator.MINIMUM, .9,
                                      RequirementLevel.WARNING))
    result = evaluate_policy(request(policy=policy(*requirements)))
    assert result.state is DecisionState.SATISFIED
    assert result.requirement_outcomes[1].state is DecisionState.NOT_SATISFIED


def test_policy_controls_indeterminate_aggregation_and_never_silently_passes():
    assert evaluate_policy(request(evidence=())).state is DecisionState.INDETERMINATE
    failing = policy(indeterminate_rule=IndeterminateRule.FAIL)
    assert evaluate_policy(request(policy=failing, evidence=())).state is DecisionState.NOT_SATISFIED


def test_signed_attestation_binds_every_decision_input_and_detects_substitution():
    req = request()
    result = evaluate_policy(req)
    attestation = build_decision_attestation(req, result, authority_id="quality-gate",
                                             signer=KEY.sign)
    assert verify_decision_attestation(attestation, policy=req.policy, observed_at=NOW,
                                       signature_verifier=verifier)
    attacks = (replace(attestation, artifact_digest="9" * 64),
               replace(attestation, environment="staging"),
               replace(attestation, decision=replace(result, state=DecisionState.NOT_SATISFIED)),
               replace(attestation, evidence_package_ids=("8" * 64,)))
    assert all(not verify_decision_attestation(item, policy=req.policy, observed_at=NOW,
                                               signature_verifier=verifier) for item in attacks)
    assert not verify_decision_attestation(attestation, policy=replace(req.policy, version="8"),
                                           observed_at=NOW, signature_verifier=verifier)


def test_expired_attestation_fails_and_public_outcome_does_not_leak_internals():
    req = request()
    result = evaluate_policy(req)
    attestation = build_decision_attestation(req, result, authority_id="quality-gate", signer=KEY.sign)
    assert not verify_decision_attestation(attestation, policy=req.policy,
                                           observed_at=req.expires_at, signature_verifier=verifier)
    public = public_decision_outcome(result, attestation=attestation)
    serialized = json.dumps(asdict(public), default=str)
    assert public.reason_code == "policy_satisfied"
    for protected in ("signature", "authority_id", "expected", "values", "weight"):
        assert protected not in serialized
