from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError, asdict, replace
from datetime import datetime, timedelta, timezone

import pytest

from src.reference_architecture_deployment_admission import (
    AdmissionDocumentError, DeploymentAdmissionGateway, InMemoryEnforcementStateStore,
    SafeAuthorizationVerifierAdapter, admission_request_document, admit_deployment,
    canonicalize_deployment_request, enforcement_policy_reference, public_admission_result,
    translate_untrusted_admission_request,
)
from src.reference_architecture_deployment_admission_contract import (
    ADMISSION_CONTRACT_VERSION, AdmissionDecision, AdmissionEnforcementPolicy,
    AuthorizationUsage, DeploymentAdmissionRequest, VerifiedAuthorizationReference,
)
from tests.test_reference_architecture_deployment_authorization import (
    authorization_verifier, authorized_bundle,
)


NOW = datetime(2026, 9, 15, 12, tzinfo=timezone.utc)


def policy(**changes):
    values = dict(policy_id="deployment-admission", version="1",
                  allowed_operations=frozenset({"release"}),
                  allowed_environment_classifications=frozenset({"restricted"}),
                  usage=AuthorizationUsage.SINGLE_USE,
                  minimum_remaining_validity_seconds=30, maximum_clock_skew_seconds=0)
    values.update(changes)
    return AdmissionEnforcementPolicy(**values)


def request(**changes):
    current_policy = changes.pop("policy", policy())
    values = dict(admission_request_id="admission-request-1",
                  deployment_attempt_id="deployment-attempt-1", authorization_id="1" * 64,
                  artifact_id="system-a", artifact_digest="4" * 64, release_id="release-9",
                  tenant_id="tenant-a", target_environment="production",
                  environment_classification="restricted", deployment_scope="customer-support",
                  operation="release", configuration_digest="7" * 64,
                  requested_conditions=("canary-required",), requested_at=NOW,
                  evaluation_time=NOW, correlation_id="trace-1",
                  enforcement_policy=enforcement_policy_reference(current_policy),
                  idempotency_key="retry-1")
    values.update(changes)
    return DeploymentAdmissionRequest(**values)


def trusted(req):
    return VerifiedAuthorizationReference(
        req.authorization_id, req.artifact_id, req.artifact_digest, req.release_id,
        req.tenant_id, req.target_environment, req.deployment_scope,
        req.requested_conditions, "deployment-authz", NOW - timedelta(seconds=1),
        NOW + timedelta(hours=1))


class Verifier:
    def __init__(self, result=None, reason="deployment_authorized", error=None):
        self.result, self.reason, self.error = result, reason, error

    def verify(self, authorization, **kwargs):
        if self.error:
            raise self.error
        return self.result, self.reason


class Executor:
    def __init__(self, error=None):
        self.calls, self.error = [], error

    def execute(self, req, receipt):
        self.calls.append((req, receipt))
        if self.error:
            raise self.error


class FailedStore:
    def consume(self, **kwargs):
        raise TimeoutError("private storage detail")


def decision(req, *, verifier=None, selected_policy=None, store=None, authorization=None):
    return admit_deployment(
        req, authorization=authorization, authorization_history=(),
        verifier=verifier or Verifier(trusted(req)), policy=selected_policy or policy(),
        state_store=store or InMemoryEnforcementStateStore())


def test_contract_is_immutable_and_rejects_privileged_or_invalid_input():
    req = request()
    with pytest.raises(FrozenInstanceError):
        req.operation = "delete"  # type: ignore[misc]
    document = admission_request_document(req)
    assert translate_untrusted_admission_request(document) == req
    for change in ({"permitted": True}, {"unknown": "field"}):
        with pytest.raises(AdmissionDocumentError, match="request is invalid"):
            translate_untrusted_admission_request({**document, **change})
    for field in ("authorization_id", "configuration_digest", "evaluation_time"):
        invalid = dict(document)
        invalid.pop(field)
        with pytest.raises(AdmissionDocumentError):
            translate_untrusted_admission_request(invalid)


def test_translation_requires_canonical_json_and_supported_version():
    document = admission_request_document(request())
    canonical = json.dumps(document, sort_keys=True, separators=(",", ":")).encode()
    assert translate_untrusted_admission_request(canonical) == request()
    with pytest.raises(AdmissionDocumentError):
        translate_untrusted_admission_request(json.dumps(document))
    document["contract_version"] = "2.0"
    with pytest.raises(AdmissionDocumentError):
        translate_untrusted_admission_request(document)


def test_canonical_identity_is_deterministic_and_binds_every_security_field():
    req = request()
    original = canonicalize_deployment_request(req)
    assert original == canonicalize_deployment_request(req)
    changes = dict(artifact_digest="8" * 64, tenant_id="tenant-b", target_environment="staging",
                   release_id="release-10", deployment_scope="all", operation="rollback",
                   configuration_digest="9" * 64, requested_conditions=("manual",),
                   authorization_id="2" * 64, deployment_attempt_id="attempt-2")
    for field, value in changes.items():
        assert canonicalize_deployment_request(replace(req, **{field: value})).digest != original.digest


@pytest.mark.parametrize(("field", "value", "reason"), (
    ("artifact_id", "system-b", "artifact_mismatch"),
    ("artifact_digest", "8" * 64, "digest_mismatch"),
    ("tenant_id", "tenant-b", "tenant_mismatch"),
    ("target_environment", "staging", "environment_mismatch"),
    ("release_id", "release-10", "release_mismatch"),
    ("deployment_scope", "expanded", "scope_mismatch"),
    ("requested_conditions", ("manual",), "conditions_not_preserved"),
))
def test_exact_authorization_binding_blocks_substitution(field, value, reason):
    req = request()
    result = decision(replace(req, **{field: value}), verifier=Verifier(trusted(req)))
    assert result.decision is AdmissionDecision.BLOCKED
    assert result.reason_codes == (reason,)


def test_policy_operation_environment_clock_and_lifetime_fail_closed():
    req = request()
    cases = (
        (replace(req, operation="delete"), policy(), "operation_not_authorized"),
        (replace(req, environment_classification="public"), policy(), "environment_mismatch"),
        (replace(req, evaluation_time=NOW + timedelta(seconds=1)), policy(), "authorization_invalid"),
        (request(policy=policy(minimum_remaining_validity_seconds=7200)),
         policy(minimum_remaining_validity_seconds=7200), "authorization_expired"),
    )
    for candidate, selected, reason in cases:
        assert decision(candidate, selected_policy=selected,
                        verifier=Verifier(trusted(candidate))).reason_codes == (reason,)


def test_missing_invalid_and_unavailable_authorization_never_permit():
    req = request()
    cases = (
        (Verifier(None, "authorization_missing"), AdmissionDecision.INDETERMINATE, "authorization_missing"),
        (Verifier(None, "authorization_revoked"), AdmissionDecision.INVALID, "authorization_revoked"),
        (Verifier(error=TimeoutError("secret")), AdmissionDecision.INDETERMINATE, "verifier_unavailable"),
    )
    for verifier, expected, reason in cases:
        result = decision(req, verifier=verifier)
        assert result.decision is expected and not result.permitted
        assert result.reason_codes == (reason,)


def test_policy_substitution_and_store_failure_fail_closed_without_leaking_errors():
    req = request()
    changed = policy(version="2")
    assert decision(req, selected_policy=changed).reason_codes == ("enforcement_indeterminate",)
    failed = decision(req, store=FailedStore())
    assert failed.decision is AdmissionDecision.INDETERMINATE
    assert failed.reason_codes == ("lifecycle_state_unavailable",)


def test_atomic_single_use_idempotency_replay_and_concurrency():
    req = request()
    store = InMemoryEnforcementStateStore()
    first = decision(req, store=store)
    retry = decision(req, store=store)
    replay = decision(replace(req, deployment_attempt_id="attempt-2", idempotency_key="retry-2"),
                      verifier=Verifier(trusted(req)), store=store)
    assert first.permitted and retry.permitted and retry.idempotent_replay
    assert retry.receipt == first.receipt
    assert replay.reason_codes == ("authorization_replayed",)

    second_store = InMemoryEnforcementStateStore()
    attempts = [replace(req, deployment_attempt_id=f"attempt-{index}", idempotency_key=f"key-{index}")
                for index in range(12)]
    with ThreadPoolExecutor(max_workers=12) as pool:
        outcomes = list(pool.map(lambda item: decision(item, verifier=Verifier(trusted(req)),
                                                       store=second_store), attempts))
    assert sum(item.permitted for item in outcomes) == 1


def test_gateway_invokes_executor_once_only_after_new_permission():
    req = request()
    executor = Executor()
    gateway = DeploymentAdmissionGateway(Verifier(trusted(req)), policy(),
                                         InMemoryEnforcementStateStore(), executor)
    first = gateway.admit(req, authorization=None)
    retry = gateway.admit(req, authorization=None)
    assert first.permitted and retry.idempotent_replay and len(executor.calls) == 1

    blocked_executor = Executor()
    blocked_gateway = DeploymentAdmissionGateway(Verifier(None, "authorization_invalid"), policy(),
                                                 InMemoryEnforcementStateStore(), blocked_executor)
    assert not blocked_gateway.admit(req, authorization=None).permitted
    assert blocked_executor.calls == []


def test_executor_exception_is_indeterminate_not_permission():
    req = request()
    gateway = DeploymentAdmissionGateway(Verifier(trusted(req)), policy(),
                                         InMemoryEnforcementStateStore(),
                                         Executor(RuntimeError("provider secret")))
    result = gateway.admit(req, authorization=None)
    assert result.decision is AdmissionDecision.INDETERMINATE and not result.permitted
    assert result.reason_codes == ("enforcement_indeterminate",)


def test_real_atl_a14_safe_verifier_is_the_trust_boundary():
    _, _, authorization = authorized_bundle()
    req = request(authorization_id=authorization.authorization_id)
    adapter = SafeAuthorizationVerifierAdapter(authorization_verifier)
    result = decision(req, verifier=adapter, authorization=authorization)
    assert result.permitted
    changed = replace(req, artifact_digest="8" * 64, idempotency_key="changed")
    assert not decision(changed, verifier=adapter, authorization=authorization).permitted


def test_public_projection_is_allowlisted_deterministic_and_sanitized():
    req = request()
    result = decision(req)
    public = public_admission_result(req, result)
    assert public.permitted and public.contract_version == ADMISSION_CONTRACT_VERSION
    serialized = json.dumps(asdict(public), default=str, sort_keys=True)
    for protected in ("allowed_operations", "minimum_remaining_validity_seconds", "signature",
                      "key_id", "authorization_policy_id", "consumption_reference"):
        assert protected not in serialized
    assert json.dumps(asdict(public), default=str, sort_keys=True) == serialized
