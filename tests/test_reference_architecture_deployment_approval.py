from __future__ import annotations

import json
from dataclasses import asdict, replace
from datetime import datetime, timedelta, timezone

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from src.reference_architecture_deployment_approval import (
    append_approval_event, approval_request_document, build_approval_attestation,
    canonical_approval_json, current_approval_state, decide_approval,
    public_approval_outcome, translate_untrusted_approval_request, verify_approval_attestation,
    verify_approval_history, verify_deployment_authorization,
)
from src.reference_architecture_deployment_approval_contract import (
    ApprovalEventType, ApprovalRequest, ApprovalRules, ApprovalState, ApproverGrant,
    ArtifactBinding, DeploymentTarget,
)
from src.reference_architecture_policy_decision import build_decision_attestation, evaluate_policy
from tests.test_reference_architecture_policy_decision import KEY as DECISION_KEY, policy, request


NOW = datetime(2026, 9, 15, 12, tzinfo=timezone.utc)
KEY = Ed25519PrivateKey.generate()


def artifact(**changes: object) -> ArtifactBinding:
    values = dict(artifact_digest="4" * 64, configuration_digest="5" * 64,
                  provider="provider-a", model_version="v2.4", release_id="release-9",
                  prompt_version="p3", dataset_version="d8")
    values.update(changes)
    return ArtifactBinding(**values)  # type: ignore[arg-type]


def target(**changes: object) -> DeploymentTarget:
    values = dict(tenant_id="tenant-a", environment="production", region="us-east",
                  purpose="customer-support")
    values.update(changes)
    return DeploymentTarget(**values)  # type: ignore[arg-type]


def approval_request(**changes: object) -> ApprovalRequest:
    decision = build_decision_attestation(request(), evaluate_policy(request()),
                                          authority_id="quality-gate", signer=DECISION_KEY.sign)
    values = dict(request_id="approval-request", decision_attestation_id=decision.attestation_id,
                  artifact=artifact(), target=target(), requester_id="requester",
                  policy_category="enterprise", risk_level=5, valid_from=NOW,
                  valid_until=NOW + timedelta(hours=1), conditions=())
    values.update(changes)
    return ApprovalRequest(**values)  # type: ignore[arg-type]


def decision_attestation():
    req = request()
    return build_decision_attestation(req, evaluate_policy(req), authority_id="quality-gate",
                                      signer=DECISION_KEY.sign)


def grant(actor: str = "approver", **changes: object) -> ApproverGrant:
    values = dict(actor_id=actor, tenant_id="tenant-a", environments=frozenset({"production"}),
                  policy_categories=frozenset({"enterprise"}), roles=frozenset({"release"}),
                  max_risk_level=7, max_duration_seconds=7200,
                  valid_from=NOW - timedelta(days=1), valid_until=NOW + timedelta(days=1))
    values.update(changes)
    return ApproverGrant(**values)  # type: ignore[arg-type]


def signature_verifier(payload: bytes, signature: bytes) -> bool:
    try:
        KEY.public_key().verify(signature, payload)
        return True
    except Exception:
        return False


def approve(req=None, attestation=None, **changes):
    req, attestation = req or approval_request(), attestation or decision_attestation()
    values = dict(request=req, decision_attestation=attestation,
                  decision_attestation_valid=True, approver_grants=(grant(),),
                  approver_ids=("approver",), rules=ApprovalRules(), evaluator_id="evaluator",
                  observed_at=NOW)
    values.update(changes)
    return decide_approval(**values)


def test_strict_translation_round_trip_rejects_unknown_environment_and_bad_documents():
    document = approval_request_document(approval_request())
    raw = canonical_approval_json(document)
    assert translate_untrusted_approval_request(raw, allowed_environments=frozenset({"production"})) == approval_request()
    with pytest.raises(ValueError):
        translate_untrusted_approval_request({**document, "extra": True})
    with pytest.raises(ValueError):
        translate_untrusted_approval_request(document, allowed_environments=frozenset({"staging"}))
    with pytest.raises(ValueError):
        translate_untrusted_approval_request(json.dumps(document, indent=2))


def test_valid_decision_authority_and_exact_bindings_produce_approval():
    result = approve()
    assert result.state is ApprovalState.APPROVED
    assert result.reason_code == "deployment_authorized"


def test_decision_artifact_environment_and_tenant_substitution_fail_closed():
    assert approve(decision_attestation_valid=False).state is ApprovalState.INVALID
    assert approve(req=approval_request(artifact=artifact(artifact_digest="9" * 64))).reason_code == "artifact_mismatch"
    assert approve(req=approval_request(target=target(environment="staging"))).reason_code == "environment_mismatch"
    bad = replace(decision_attestation(), decision=replace(decision_attestation().decision,
                                                           state=decision_attestation().decision.state.NOT_SATISFIED))
    assert approve(attestation=bad).reason_code == "decision_not_satisfied"


def test_approver_scope_duration_risk_and_role_are_enforced():
    assert approve(approver_grants=(grant(max_risk_level=4),)).reason_code == "approver_not_authorized"
    assert approve(approver_grants=(grant(max_duration_seconds=10),)).reason_code == "approver_not_authorized"
    assert approve(rules=ApprovalRules(required_roles=frozenset({"security"}))).reason_code == "quorum_not_satisfied"
    assert approve(approver_grants=(grant(environments=frozenset({"staging"})),)).reason_code == "approver_not_authorized"


def test_separation_of_duties_unique_identity_and_quorum_are_deterministic():
    assert approve(approver_ids=("evaluator",), approver_grants=(grant("evaluator"),)).reason_code == "approver_not_authorized"
    assert approve(approver_ids=("approver", "approver"), rules=ApprovalRules(quorum=2)).reason_code == "quorum_not_satisfied"
    assert approve(approver_ids=("requester",), approver_grants=(grant("requester"),)).state is ApprovalState.PENDING
    grants = (grant("a", roles=frozenset({"release"})), grant("b", roles=frozenset({"security"})))
    result = approve(approver_ids=("a", "b"), approver_grants=grants,
                     rules=ApprovalRules(quorum=2, required_roles=frozenset({"security"})))
    assert result.state is ApprovalState.APPROVED


def test_conditions_are_preserved_and_signed_attestation_detects_tampering():
    req = approval_request(conditions=("canary-required",))
    result = approve(req=req)
    assert result.state is ApprovalState.APPROVED_WITH_CONDITIONS
    value = build_approval_attestation(req, result, issued_at=NOW, signer=KEY.sign)
    assert verify_approval_attestation(value, observed_at=NOW, signature_verifier=signature_verifier,
                                       artifact=req.artifact, target=req.target)
    attacks = (replace(value, decision=replace(result, conditions=())),
               replace(value, request=replace(req, valid_until=NOW + timedelta(days=1))),
               replace(value, request=replace(req, target=target(environment="staging"))))
    assert all(not verify_approval_attestation(item, observed_at=NOW,
                                               signature_verifier=signature_verifier,
                                               artifact=req.artifact, target=req.target) for item in attacks)


def test_append_only_lifecycle_detects_rollback_revocation_expiration_and_supersession():
    req = approval_request()
    value = build_approval_attestation(req, approve(req=req), issued_at=NOW, signer=KEY.sign)
    history = append_approval_event((), approval_id=value.approval_id,
                                    event_type=ApprovalEventType.APPROVED, actor_id="approver",
                                    reason_code="authorized", occurred_at=NOW,
                                    artifact_digest=req.artifact.artifact_digest,
                                    environment=req.target.environment,
                                    decision_attestation_id=req.decision_attestation_id)
    revoked = append_approval_event(history, approval_id=value.approval_id,
                                    event_type=ApprovalEventType.REVOKED, actor_id="security",
                                    reason_code="security_event", occurred_at=NOW + timedelta(minutes=1),
                                    artifact_digest=req.artifact.artifact_digest,
                                    environment=req.target.environment,
                                    decision_attestation_id=req.decision_attestation_id)
    assert revoked[-1].previous_event_id == history[-1].event_id
    assert verify_approval_history(revoked)
    assert not verify_approval_history((revoked[1], revoked[0]))
    assert not verify_approval_history((replace(revoked[0], environment="staging"), revoked[1]))
    assert current_approval_state(value, revoked, observed_at=NOW + timedelta(minutes=2)) is ApprovalState.REVOKED
    assert current_approval_state(value, history, observed_at=req.valid_until) is ApprovalState.EXPIRED


def test_public_verifier_is_minimal_and_never_leaks_governance_details():
    req = approval_request(conditions=("canary-required",))
    value = build_approval_attestation(req, approve(req=req), issued_at=NOW, signer=KEY.sign)
    public = public_approval_outcome(value)
    serialized = json.dumps(asdict(public), default=str)
    assert public.authorized and public.reason_code == "deployment_authorized"
    assert public_approval_outcome(value, state=ApprovalState.REVOKED).reason_code == "approval_revoked"
    assert public_approval_outcome(None).reason_code == "approval_missing"
    verified = verify_deployment_authorization(value, history=(), observed_at=NOW,
                                               signature_verifier=signature_verifier,
                                               artifact=req.artifact, target=req.target)
    assert verified.authorized
    substituted = verify_deployment_authorization(value, history=(), observed_at=NOW,
                                                  signature_verifier=signature_verifier,
                                                  artifact=artifact(artifact_digest="9" * 64),
                                                  target=req.target)
    assert not substituted.authorized and substituted.reason_code == "approval_attestation_invalid"
    for protected in ("signature", "approver_ids", "requester_id", "risk_level", "roles"):
        assert protected not in serialized
