from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError, asdict, replace
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from threading import Lock

import pytest

from src.reference_architecture_deployment_admission_contract import AdmissionDecision, DeploymentAdmissionReceipt
from src.reference_architecture_deployment_execution import (
    ExecutionDocumentError, InMemoryExecutionStateStore, SafeAdmissionReceiptVerifierAdapter,
    canonicalize_execution_command, execute_deployment, execution_policy_reference,
    execution_request_document, public_execution_result, translate_untrusted_execution_request,
    verify_execution_attestation,
)
from src.reference_architecture_deployment_execution_contract import (
    DeploymentExecutionRequest, ExecutionOutcome, ExecutionPolicy, ProviderExecutionResult,
    VerifiedAdmissionReference,
)


NOW = datetime(2026, 9, 15, 16, tzinfo=timezone.utc)


def policy(**changes):
    values = dict(policy_id="execution-policy", version="1", permitted_adapters=frozenset({"reference"}),
        adapter_contract_versions=frozenset({"1.0"}), permitted_operations=frozenset({"release"}),
        environment_classifications=frozenset({"restricted"}), required_capabilities=frozenset({"deploy"}),
        timeout_seconds=60, maximum_attempts=1, minimum_receipt_lifetime_seconds=30)
    values.update(changes)
    return ExecutionPolicy(**values)


def request(**changes):
    selected = changes.pop("policy", policy())
    values = dict(execution_attempt_id="execution-1", admission_receipt_id="a" * 64,
        deployment_request_digest="b" * 64, authorization_id="c" * 64,
        artifact_id="system-a", artifact_digest="d" * 64, tenant_id="tenant-a",
        target_environment="production", environment_classification="restricted",
        release_id="release-9", operation="release", deployment_scope="customer-support",
        configuration_digest="e" * 64, idempotency_key="key-1", requested_adapter="reference",
        adapter_contract_version="1.0", evaluation_time=NOW, trace_reference="trace-1",
        execution_policy=execution_policy_reference(selected), required_conditions=("canary",))
    values.update(changes)
    return DeploymentExecutionRequest(**values)


def receipt(req=None):
    req = req or request()
    return DeploymentAdmissionReceipt(req.admission_receipt_id, "deployment-attempt-1", req.authorization_id,
        req.deployment_request_digest, AdmissionDecision.PERMITTED, "admission-policy", "1", "f" * 64,
        NOW - timedelta(seconds=10), "consumption-1", req.trace_reference, "1" * 64)


def admission(req=None, **changes):
    req = req or request()
    values = dict(receipt_id=req.admission_receipt_id, deployment_request_digest=req.deployment_request_digest,
        authorization_id=req.authorization_id, artifact_id=req.artifact_id, artifact_digest=req.artifact_digest,
        tenant_id=req.tenant_id, environment=req.target_environment,
        environment_classification=req.environment_classification, release_id=req.release_id,
        operation=req.operation, scope=req.deployment_scope, configuration_digest=req.configuration_digest,
        conditions=req.required_conditions, admission_policy_id="admission-policy",
        admitted_at=NOW - timedelta(seconds=10), valid_until=NOW + timedelta(hours=1),
        admission_contract_version="1.0", consumption_reference="consumption-1")
    values.update(changes)
    return VerifiedAdmissionReference(**values)


class Verifier:
    def __init__(self, value=None, error=None): self.value, self.error = value, error
    def verify(self, supplied, req):
        if self.error: raise self.error
        return self.value if self.value is not None else admission(req)


class Adapter:
    identity = "reference"
    contract_version = "1.0"
    capabilities = frozenset({"deploy"})
    def __init__(self, error=None, result=None): self.calls, self.error, self.result = 0, error, result; self.lock = Lock()
    def execute(self, command):
        with self.lock: self.calls += 1
        if self.error: raise self.error
        return self.result or ProviderExecutionResult("adapter-execution-1", "provider-op-1",
            ExecutionOutcome.SUCCEEDED, NOW, NOW + timedelta(seconds=2),
            sha256(b"safe-normalized-response").hexdigest(), "deployment_succeeded",
            command.request.artifact_digest, command.request.target_environment)


def run(req=None, *, verified=None, adapter=None, store=None, selected_policy=None, supplied_receipt=None):
    req = req or request(); adapter = adapter or Adapter()
    return execute_deployment(req, receipt=supplied_receipt or receipt(req),
        verifier=Verifier(verified), policy=selected_policy or policy(), adapters={"reference": adapter},
        state_store=store or InMemoryExecutionStateStore())


def test_contract_translation_is_strict_bounded_canonical_and_immutable():
    req = request(); document = execution_request_document(req)
    assert translate_untrusted_execution_request(document) == req
    canonical = json.dumps(document, sort_keys=True, separators=(",", ":")).encode()
    assert translate_untrusted_execution_request(canonical) == req
    with pytest.raises(FrozenInstanceError): req.operation = "delete"  # type: ignore[misc]
    attacks = ({**document, "trusted": True}, {**document, "unknown": 1},
               {**document, "contract_version": "2.0"})
    for attack in attacks:
        with pytest.raises(ExecutionDocumentError): translate_untrusted_execution_request(attack)
    duplicate = canonical[:-1] + b',"operation":"release"}'
    with pytest.raises(ExecutionDocumentError): translate_untrusted_execution_request(duplicate)
    with pytest.raises(ExecutionDocumentError): translate_untrusted_execution_request(b"{" + b" " * 40_000 + b"}")


def test_safe_receipt_verifier_requires_real_permitted_matching_receipt():
    req = request(); adapter = SafeAdmissionReceiptVerifierAdapter(lambda supplied, candidate: admission(candidate))
    assert adapter.verify(receipt(req), req) == admission(req)
    assert adapter.verify(None, req) is None
    assert adapter.verify(replace(receipt(req), receipt_id="2" * 64), req) is None
    assert adapter.verify(replace(receipt(req), outcome=AdmissionDecision.BLOCKED), req) is None


def test_command_identity_is_deterministic_and_binds_security_fields():
    req = request(); original = canonicalize_execution_command(req, admission(req)).execution_command_digest
    assert original == canonicalize_execution_command(req, admission(req)).execution_command_digest
    changes = dict(artifact_digest="1" * 64, tenant_id="tenant-b", target_environment="staging",
        release_id="release-10", operation="rollback", deployment_scope="all",
        configuration_digest="2" * 64, requested_adapter="other", execution_attempt_id="execution-2",
        idempotency_key="key-2", required_conditions=("manual",))
    for field, value in changes.items():
        changed = replace(req, **{field: value})
        assert canonicalize_execution_command(changed, admission(changed)).execution_command_digest != original


@pytest.mark.parametrize(("change", "reason"), (
    ({"receipt_id": "2" * 64}, "receipt_mismatch"), ({"artifact_id": "system-b"}, "artifact_mismatch"),
    ({"artifact_digest": "2" * 64}, "artifact_digest_mismatch"), ({"tenant_id": "tenant-b"}, "tenant_mismatch"),
    ({"environment": "staging"}, "environment_mismatch"), ({"release_id": "release-10"}, "release_mismatch"),
    ({"configuration_digest": "3" * 64}, "configuration_mismatch"), ({"operation": "rollback"}, "operation_mismatch"),
    ({"conditions": ("manual",)}, "conditions_mismatch"),
))
def test_exact_admission_binding_blocks_substitution(change, reason):
    req = request(); result = run(req, verified=admission(req, **change))
    assert result.outcome is ExecutionOutcome.BLOCKED and result.reason_code == reason


def test_policy_registry_capability_lifetime_and_verifier_fail_closed():
    req = request(); adapter = Adapter()
    assert run(req, adapter=adapter, selected_policy=policy(version="2")).reason_code == "execution_policy_mismatch"
    assert run(req, verified=admission(req, valid_until=NOW)).reason_code == "admission_expired"
    incapable = Adapter(); incapable.capabilities = frozenset()  # type: ignore[misc]
    assert run(req, adapter=incapable).reason_code == "adapter_capability_mismatch"
    result = execute_deployment(req, receipt=receipt(req), verifier=Verifier(error=TimeoutError("secret")),
        policy=policy(), adapters={"reference": adapter}, state_store=InMemoryExecutionStateStore())
    assert result.outcome is ExecutionOutcome.INDETERMINATE
    assert result.reason_code == "admission_verifier_unavailable" and adapter.calls == 0


def test_atomic_claim_idempotency_conflict_and_concurrency_invoke_once():
    req = request(); store = InMemoryExecutionStateStore(); adapter = Adapter()
    first = run(req, adapter=adapter, store=store); replay = run(req, adapter=adapter, store=store)
    assert first.outcome is ExecutionOutcome.SUCCEEDED and replay.idempotent_replay and adapter.calls == 1
    conflict = run(replace(req, execution_attempt_id="execution-2"), adapter=adapter, store=store)
    assert conflict.reason_code == "idempotency_conflict" and adapter.calls == 1
    second_key = run(replace(req, execution_attempt_id="execution-3", idempotency_key="key-2"),
                     adapter=adapter, store=store)
    assert second_key.reason_code == "idempotency_conflict" and adapter.calls == 1

    concurrent_store = InMemoryExecutionStateStore(); concurrent_adapter = Adapter()
    with ThreadPoolExecutor(max_workers=12) as pool:
        results = list(pool.map(lambda _: run(req, adapter=concurrent_adapter, store=concurrent_store), range(12)))
    assert concurrent_adapter.calls == 1
    assert any(item.outcome is ExecutionOutcome.SUCCEEDED for item in results)


def test_provider_exception_becomes_attested_unknown_and_is_not_retried():
    req = request(); store = InMemoryExecutionStateStore(); adapter = Adapter(error=ConnectionError("credential=secret"))
    result = run(req, adapter=adapter, store=store)
    assert result.outcome is ExecutionOutcome.OUTCOME_UNKNOWN and result.attestation is not None
    assert result.reason_code == "provider_outcome_unknown"
    replay = run(req, adapter=adapter, store=store)
    assert replay.idempotent_replay and replay.outcome is ExecutionOutcome.OUTCOME_UNKNOWN and adapter.calls == 1
    assert "secret" not in json.dumps(asdict(result.attestation), default=str)


def test_attestation_and_public_projection_are_deterministic_allowlists():
    req = request(); first = run(req); second = run(req)
    assert first.attestation == second.attestation
    assert first.attestation and verify_execution_attestation(first.attestation)
    assert not verify_execution_attestation(replace(first.attestation, release_id="changed"))
    public = public_execution_result(req, first); encoded = json.dumps(asdict(public), default=str, sort_keys=True)
    assert public.outcome is ExecutionOutcome.SUCCEEDED
    for protected in ("required_capabilities", "timeout_seconds", "provider_response_digest",
                      "provider_operation_reference", "previous_state_reference", "configuration_digest"):
        assert protected not in encoded
    assert encoded == json.dumps(asdict(public_execution_result(req, first)), default=str, sort_keys=True)


class FailedStore:
    def claim(self, **kwargs): raise TimeoutError("private store endpoint")


def test_state_store_failure_blocks_before_adapter():
    adapter = Adapter(); result = run(adapter=adapter, store=FailedStore())
    assert result.outcome is ExecutionOutcome.INDETERMINATE
    assert result.reason_code == "execution_state_unavailable" and adapter.calls == 0
