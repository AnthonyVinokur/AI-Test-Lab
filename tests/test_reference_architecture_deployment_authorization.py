from __future__ import annotations

import json
from dataclasses import FrozenInstanceError, asdict, replace
from datetime import datetime, timedelta, timezone

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from src.reference_architecture_deployment_approval import (
    append_approval_event, build_approval_attestation, decide_approval,
)
from src.reference_architecture_deployment_approval_contract import (
    ApprovalEventType, ApprovalRules, ApproverGrant,
)
from src.reference_architecture_deployment_authorization import (
    append_authorization_lifecycle_record, authorization_policy_digest,
    authorize_deployment,
    authorization_policy_reference, authorization_request_document,
    build_deployment_authorization_attestation, canonical_authorization_json,
    decide_deployment_authorization, public_authorization_result,
    translate_untrusted_authorization_request, verify_approval_reference,
    verify_authorization_history, verify_decision_reference,
    verify_deployment_authorization,
)
from src.reference_architecture_deployment_authorization_contract import (
    AUTHORIZATION_CONTRACT_VERSION, AuthorizationEventType, AuthorizationLifecycleState,
    AuthorizationPolicy, AuthorizationState, DeploymentAuthorizationRequest, DeploymentContext,
)
from src.reference_architecture_policy_decision import build_decision_attestation, evaluate_policy
from tests.test_reference_architecture_deployment_approval import (
    DECISION_KEY, KEY as APPROVAL_KEY, approval_request, artifact, target,
)
from tests.test_reference_architecture_policy_decision import policy, request


NOW = datetime(2026, 9, 15, 12, tzinfo=timezone.utc)
AUTHORIZATION_KEY = Ed25519PrivateKey.generate()


def verify_with(key):
    def verifier(payload: bytes, signature: bytes) -> bool:
        try:
            key.public_key().verify(signature, payload)
            return True
        except Exception:
            return False
    return verifier


def authorization_verifier(key_id: str, payload: bytes, signature: bytes) -> bool:
    return key_id == "authorization-key-1" and verify_with(AUTHORIZATION_KEY)(payload, signature)


def decision_attestation(**request_changes):
    req = request(**request_changes)
    return req, build_decision_attestation(req, evaluate_policy(req), authority_id="quality-gate",
                                           signer=DECISION_KEY.sign)


def approval_attestation(decision, **request_changes):
    req = approval_request(decision_attestation_id=decision.attestation_id, **request_changes)
    grant = ApproverGrant("approver", req.target.tenant_id, frozenset({req.target.environment}),
                          frozenset({req.policy_category}), frozenset({"release"}), 10, 7200,
                          NOW - timedelta(days=1), NOW + timedelta(days=1))
    outcome = decide_approval(req, decision_attestation=decision, decision_attestation_valid=True,
                              approver_grants=(grant,), approver_ids=("approver",),
                              rules=ApprovalRules(), evaluator_id="evaluator", observed_at=NOW)
    return build_approval_attestation(req, outcome, issued_at=NOW, signer=APPROVAL_KEY.sign)


def auth_policy(**changes):
    values = dict(policy_id="deployment-authz", version="3",
                  accepted_decision_versions=frozenset({"1.0"}),
                  accepted_approval_versions=frozenset({"1.0"}),
                  allowed_environments=frozenset({"production"}),
                  allowed_tenants=frozenset({"tenant-a"}),
                  maximum_decision_age_seconds=3600, maximum_approval_age_seconds=3600,
                  minimum_remaining_lifetime_seconds=60,
                  required_conditions=frozenset({"canary-required"}))
    values.update(changes)
    return AuthorizationPolicy(**values)


def context(**changes):
    values = dict(artifact_id="system-a", artifact_digest="4" * 64,
                  tenant_id="tenant-a", environment="production", release_id="release-9",
                  scope="customer-support", conditions=("canary-required",))
    values.update(changes)
    return DeploymentContext(**values)


def auth_request(decision, approval, **changes):
    values = dict(request_id="authorization-request-1",
                  decision_attestation_id=decision.attestation_id,
                  approval_attestation_id=approval.approval_id, context=context(),
                  authorization_policy=authorization_policy_reference(auth_policy()),
                  requested_at=NOW, correlation_id="trace-14")
    values.update(changes)
    return DeploymentAuthorizationRequest(**values)


def trusted_inputs(*, approval_changes=None):
    source_request, decision = decision_attestation()
    approval = approval_attestation(
        decision, conditions=("canary-required",), **(approval_changes or {}))
    decision_ref = verify_decision_reference(
        decision, policy=source_request.policy, observed_at=NOW,
        signature_verifier=verify_with(DECISION_KEY))
    approval_ref = verify_approval_reference(
        approval, history=(), observed_at=NOW, signature_verifier=verify_with(APPROVAL_KEY))
    assert decision_ref is not None and approval_ref is not None
    return decision, approval, decision_ref, approval_ref


def authorized_bundle():
    decision, approval, decision_ref, approval_ref = trusted_inputs()
    req = auth_request(decision, approval)
    outcome = decide_deployment_authorization(req, decision=decision_ref,
                                              approval=approval_ref, policy=auth_policy())
    attestation = build_deployment_authorization_attestation(
        req, outcome, decision=decision_ref, approval=approval_ref,
        issuer_id="authorization-service", key_id="authorization-key-1",
        signer=AUTHORIZATION_KEY.sign)
    return req, outcome, attestation


def test_request_contract_is_immutable_and_strict_translation_rejects_unknown_fields():
    decision, approval, _, _ = trusted_inputs()
    value = auth_request(decision, approval)
    document = authorization_request_document(value)
    assert translate_untrusted_authorization_request(canonical_authorization_json(document)) == value
    with pytest.raises(FrozenInstanceError):
        value.correlation_id = "changed"  # type: ignore[misc]
    with pytest.raises(ValueError, match="request is invalid"):
        translate_untrusted_authorization_request({**document, "private_policy": {}})
    with pytest.raises(ValueError, match="request is invalid"):
        translate_untrusted_authorization_request(json.dumps(document, indent=2))
    with pytest.raises(ValueError):
        replace(value, contract_version="2.0")


def test_upstream_attestations_enter_only_through_their_approved_verifiers():
    source_request, decision = decision_attestation()
    approval = approval_attestation(decision, conditions=("canary-required",))
    assert verify_decision_reference(decision, policy=source_request.policy, observed_at=NOW,
                                     signature_verifier=verify_with(DECISION_KEY)) is not None
    assert verify_decision_reference(replace(decision, artifact_digest="9" * 64),
                                     policy=source_request.policy, observed_at=NOW,
                                     signature_verifier=verify_with(DECISION_KEY)) is None
    assert verify_approval_reference(approval, history=(), observed_at=NOW,
                                     signature_verifier=verify_with(APPROVAL_KEY)) is not None
    assert verify_approval_reference(replace(approval, signature="0" * 128), history=(),
                                     observed_at=NOW,
                                     signature_verifier=verify_with(APPROVAL_KEY)) is None


def test_exact_cross_attestation_binding_authorizes_deterministically():
    decision, approval, decision_ref, approval_ref = trusted_inputs()
    req = auth_request(decision, approval)
    first = decide_deployment_authorization(req, decision=decision_ref,
                                            approval=approval_ref, policy=auth_policy())
    second = decide_deployment_authorization(req, decision=decision_ref,
                                             approval=approval_ref, policy=auth_policy())
    assert first == second
    assert first.state is AuthorizationState.AUTHORIZED
    assert first.reason_code == "deployment_authorized"


@pytest.mark.parametrize(("change", "reason"), [
    ({"artifact_id": "system-b"}, "artifact_mismatch"),
    ({"artifact_digest": "9" * 64}, "artifact_mismatch"),
    ({"tenant_id": "tenant-b"}, "tenant_mismatch"),
    ({"environment": "staging"}, "environment_mismatch"),
    ({"release_id": "release-10"}, "release_mismatch"),
    ({"scope": "internal-search"}, "scope_mismatch"),
    ({"conditions": ()}, "conditions_not_preserved"),
])
def test_context_substitution_fails_closed(change, reason):
    decision, approval, decision_ref, approval_ref = trusted_inputs()
    req = auth_request(decision, approval, context=context(**change))
    result = decide_deployment_authorization(req, decision=decision_ref,
                                             approval=approval_ref, policy=auth_policy())
    assert result.state is AuthorizationState.DENIED
    assert result.reason_code == reason


def test_unrelated_attestations_missing_inputs_and_policy_substitution_fail_closed():
    decision, approval, decision_ref, approval_ref = trusted_inputs()
    req = auth_request(decision, approval)
    assert decide_deployment_authorization(req, decision=None, approval=approval_ref,
                                           policy=auth_policy()).state is AuthorizationState.INVALID
    assert decide_deployment_authorization(req, decision=decision_ref, approval=None,
                                           policy=auth_policy()).state is AuthorizationState.INVALID
    substituted = auth_policy(version="4")
    assert decide_deployment_authorization(req, decision=decision_ref, approval=approval_ref,
                                           policy=substituted).reason_code == "policy_mismatch"
    unrelated = replace(approval_ref, decision_attestation_id="9" * 64)
    assert decide_deployment_authorization(req, decision=decision_ref, approval=unrelated,
                                           policy=auth_policy()).reason_code == "decision_approval_mismatch"


def test_integration_boundary_normalizes_missing_revoked_and_expired_upstream_inputs():
    source_request, decision = decision_attestation()
    approval = approval_attestation(decision, conditions=("canary-required",))
    req = auth_request(decision, approval)
    arguments = dict(request=req, decision_policy=source_request.policy,
                     decision_signature_verifier=verify_with(DECISION_KEY),
                     approval_history=(), approval_signature_verifier=verify_with(APPROVAL_KEY),
                     authorization_policy=auth_policy())
    missing, _, _ = authorize_deployment(
        decision_attestation=None, approval_attestation=approval, **arguments)
    assert missing.state is AuthorizationState.INDETERMINATE
    assert missing.reason_code == "authorization_indeterminate"
    history = append_approval_event(
        (), approval_id=approval.approval_id, event_type=ApprovalEventType.REVOKED,
        actor_id="security", reason_code="incident", occurred_at=NOW,
        artifact_digest=approval.request.artifact.artifact_digest,
        environment=approval.request.target.environment,
        decision_attestation_id=decision.attestation_id)
    revoked, _, _ = authorize_deployment(
        decision_attestation=decision, approval_attestation=approval,
        **{**arguments, "approval_history": history})
    assert revoked.state is AuthorizationState.INVALID
    assert revoked.reason_code == "approval_revoked"
    expired_request = replace(req, requested_at=decision.expires_at)
    expired, _, _ = authorize_deployment(
        decision_attestation=decision, approval_attestation=approval,
        **{**arguments, "request": expired_request})
    assert expired.reason_code == "decision_expired"


def test_versions_age_lifetime_tenant_environment_and_conditions_are_policy_controlled():
    decision, approval, decision_ref, approval_ref = trusted_inputs()
    req = auth_request(decision, approval)
    cases = (
        (auth_policy(accepted_decision_versions=frozenset({"2.0"})), "unsupported_attestation_version"),
        (auth_policy(allowed_tenants=frozenset({"tenant-b"})), "tenant_not_authorized"),
        (auth_policy(allowed_environments=frozenset({"staging"})), "environment_not_authorized"),
        (auth_policy(required_conditions=frozenset({"manual-release"})), "conditions_not_preserved"),
        (auth_policy(minimum_remaining_lifetime_seconds=7200), "authorization_lifetime_insufficient"),
    )
    for item, reason in cases:
        bound = replace(req, authorization_policy=authorization_policy_reference(item))
        assert decide_deployment_authorization(bound, decision=decision_ref, approval=approval_ref,
                                               policy=item).reason_code == reason


def test_only_success_can_issue_immutable_integrity_protected_attestation():
    req, outcome, value = authorized_bundle()
    with pytest.raises(ValueError):
        build_deployment_authorization_attestation(
            req, replace(outcome, state=AuthorizationState.DENIED),
            decision=trusted_inputs()[2], approval=trusted_inputs()[3], issuer_id="issuer",
            key_id="key", signer=AUTHORIZATION_KEY.sign)
    with pytest.raises(FrozenInstanceError):
        value.environment = "staging"  # type: ignore[misc]
    result = verify_deployment_authorization(value, history=(), observed_at=NOW,
                                             signature_verifier=authorization_verifier,
                                             context=req.context)
    assert result.valid and result.active and result.applicable
    assert result.reason_code == "deployment_authorized"
    changed = replace(value, environment="staging")
    assert not verify_deployment_authorization(changed, history=(), observed_at=NOW,
                                               signature_verifier=authorization_verifier,
                                               context=req.context).valid


def test_safe_verifier_rejects_substitution_expiration_revocation_and_supersession():
    req, _, value = authorized_bundle()
    substituted = verify_deployment_authorization(value, history=(), observed_at=NOW,
                                                  signature_verifier=authorization_verifier,
                                                  context=context(environment="staging"))
    assert substituted.valid and not substituted.applicable
    assert substituted.reason_code == "authorization_not_applicable"
    expired = verify_deployment_authorization(value, history=(), observed_at=value.expires_at,
                                              signature_verifier=authorization_verifier,
                                              context=req.context)
    assert expired.lifecycle_state is AuthorizationLifecycleState.EXPIRED
    history = append_authorization_lifecycle_record(
        (), authorization_id=value.authorization_id, event_type=AuthorizationEventType.ISSUED,
        actor_id="authorization-service", reason_code="issued", occurred_at=NOW)
    revoked = append_authorization_lifecycle_record(
        history, authorization_id=value.authorization_id, event_type=AuthorizationEventType.REVOKED,
        actor_id="security", reason_code="security-event", occurred_at=NOW + timedelta(seconds=1))
    superseded = append_authorization_lifecycle_record(
        history, authorization_id=value.authorization_id, event_type=AuthorizationEventType.SUPERSEDED,
        actor_id="release", reason_code="new-release", occurred_at=NOW + timedelta(seconds=1))
    assert verify_deployment_authorization(value, history=revoked, observed_at=NOW + timedelta(seconds=2),
                                           signature_verifier=authorization_verifier,
                                           context=req.context).reason_code == "authorization_revoked"
    assert verify_deployment_authorization(value, history=superseded, observed_at=NOW + timedelta(seconds=2),
                                           signature_verifier=authorization_verifier,
                                           context=req.context).reason_code == "authorization_superseded"


def test_lifecycle_chain_detects_reordering_mutation_and_mixed_authorizations():
    _, _, value = authorized_bundle()
    first = append_authorization_lifecycle_record(
        (), authorization_id=value.authorization_id, event_type=AuthorizationEventType.ISSUED,
        actor_id="issuer", reason_code="issued", occurred_at=NOW)
    second = append_authorization_lifecycle_record(
        first, authorization_id=value.authorization_id, event_type=AuthorizationEventType.REVOKED,
        actor_id="security", reason_code="incident", occurred_at=NOW + timedelta(seconds=1))
    assert verify_authorization_history(second)
    assert not verify_authorization_history(tuple(reversed(second)))
    assert not verify_authorization_history((replace(second[0], reason_code="changed"), second[1]))
    assert not verify_authorization_history((second[0], replace(second[1], authorization_id="9" * 64)))


def test_public_projection_is_deterministic_and_contains_no_private_state():
    req, outcome, value = authorized_bundle()
    public = public_authorization_result(outcome, attestation=value, request=req)
    assert public.authorized and public.contract_version == AUTHORIZATION_CONTRACT_VERSION
    serialized = json.dumps(asdict(public), default=str, sort_keys=True)
    for protected in ("signature", "key_id", "issuer_id", "policy_digest", "required_conditions",
                      "maximum_decision_age_seconds", "approver_ids", "risk_level"):
        assert protected not in serialized
    denied = public_authorization_result(
        replace(outcome, state=AuthorizationState.DENIED, reason_code="artifact_mismatch"),
        request=req)
    assert not denied.authorized and denied.authorization_id is None
