import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from threading import Lock

import pytest

from src.public_contract import serialize_public_contract
from src.reference_architecture_continued_operation_enforcement_contract import (
    ContinuedOperationConsumptionRecord,
)
from src.reference_architecture_continued_operation_execution import (
    InMemoryContinuedOperationConsumptionRecordRepository,
    InMemoryContinuedOperationExecutionStateStore,
    InMemoryProtectedOperationManifestRepository,
    SqliteContinuedOperationExecutionStateStore,
    execute_continued_operation,
    execution_request_document,
    operation_manifest_digest,
    public_continued_operation_execution,
    translate_untrusted_execution_request,
    verify_continued_operation_execution_attestation,
)
from src.reference_architecture_continued_operation_execution_contract import (
    ContinuedOperationAdapterResult,
    ContinuedOperationExecutionError,
    ContinuedOperationExecutionOutcome as Outcome,
    ContinuedOperationExecutionPolicy,
    ContinuedOperationExecutionReasonCode as Reason,
    ContinuedOperationExecutionRequest,
    ProtectedOperationManifest,
)


NOW = datetime(2026, 9, 16, 15, 0, tzinfo=timezone.utc)


def h(value: str) -> str:
    return sha256(value.encode()).hexdigest()


def consumed(**overrides):
    values = dict(
        authorization_id=h("authorization"), authorization_digest=h("authorization-artifact"),
        enforcement_request_id="enforcement-request-27", request_binding_digest=h("binding"),
        deployment_id="deployment", consumer_id="production-gateway",
        enforcement_point_id="trusted-enforcement-gateway",
        purpose="serve-production-traffic", operation_reference="continue-serving-production",
        consumed_at=NOW - timedelta(seconds=5),
        policy_reference="continued-operation-enforcement-policy-1",
        evidence_digest=h("a26-permitted-evidence"), correlation_id="correlation-27",
    )
    values.update(overrides)
    return ContinuedOperationConsumptionRecord(**values)


def manifest(**overrides):
    values = dict(
        reference="operation-manifest-27", operation_reference="continue-serving-production",
        version="1", canonical_operation_input_digest=h("approved-operation-input"),
        permitted_adapters=("reference-adapter",),
        permitted_adapter_contract_versions=("1.0",),
        required_capabilities=("continued-operation",), timeout_seconds=30,
        permitted_deployments=("deployment",), environment_restrictions=(),
        safe_retry_classification="at-most-once", result_retention_classification="audit",
    )
    values.update(overrides)
    return ProtectedOperationManifest(**values)


def request(record=None, operation=None, **overrides):
    record = record or consumed()
    operation = operation or manifest()
    values = dict(
        execution_attempt_id="execution-attempt-27",
        enforcement_request_id=record.enforcement_request_id,
        authorization_id=record.authorization_id,
        authorization_digest=record.authorization_digest,
        enforcement_evidence_reference=record.evidence_digest,
        enforcement_evidence_digest=record.evidence_digest,
        request_binding_digest=record.request_binding_digest,
        deployment_id=record.deployment_id, consumer_id=record.consumer_id,
        enforcement_point_id=record.enforcement_point_id, purpose=record.purpose,
        operation_reference=record.operation_reference,
        operation_manifest_reference=operation.reference,
        operation_manifest_digest=operation_manifest_digest(operation),
        requested_adapter="reference-adapter", adapter_contract_version="1.0",
        execution_policy_reference="continued-operation-execution-policy-1",
        idempotency_key="idempotency-27", requested_at=NOW,
        correlation_id=record.correlation_id,
    )
    values.update(overrides)
    return ContinuedOperationExecutionRequest(**values)


def policy(**overrides):
    values = dict(
        reference="continued-operation-execution-policy-1",
        maximum_permit_to_execution_delay_seconds=60,
        permitted_adapters=("reference-adapter",),
        permitted_adapter_contract_versions=("1.0",),
    )
    values.update(overrides)
    return ContinuedOperationExecutionPolicy(**values)


class Adapter:
    identity = "reference-adapter"
    contract_version = "1.0"
    capabilities = frozenset({"continued-operation"})

    def __init__(self, outcome=Outcome.SUCCEEDED, raises=False):
        self.outcome = outcome
        self.raises = raises
        self.calls = 0
        self._lock = Lock()

    def execute(self, command):
        with self._lock:
            self.calls += 1
        if self.raises:
            raise RuntimeError("secret provider failure")
        reasons = {
            Outcome.SUCCEEDED: Reason.EXECUTION_SUCCEEDED,
            Outcome.FAILED: Reason.EXECUTION_FAILED,
            Outcome.REJECTED: Reason.PROVIDER_REJECTED,
            Outcome.TIMED_OUT: Reason.PROVIDER_TIMED_OUT,
            Outcome.OUTCOME_UNKNOWN: Reason.PROVIDER_OUTCOME_UNKNOWN,
        }
        completed = None if self.outcome is Outcome.OUTCOME_UNKNOWN else NOW
        return ContinuedOperationAdapterResult(
            command.request.execution_attempt_id, self.outcome, reasons[self.outcome],
            NOW, completed, "provider-operation-27", h("sanitized-response"),
        )


def run(req=None, *, record=None, operation=None, adapter=None, state_store=None,
        record_repository=None, manifest_repository=None, execution_policy=None, now=NOW):
    record = record or consumed()
    operation = operation or manifest()
    req = req or request(record, operation)
    adapter = adapter or Adapter()
    result = execute_continued_operation(
        req,
        consumption_repository=(record_repository or
            InMemoryContinuedOperationConsumptionRecordRepository((record,))),
        manifest_repository=(manifest_repository or
            InMemoryProtectedOperationManifestRepository((operation,))),
        policy=execution_policy or policy(), adapters={adapter.identity: adapter},
        state_store=state_store or InMemoryContinuedOperationExecutionStateStore(),
        trusted_clock=lambda: now,
    )
    return result, adapter


def canonical_wire(document):
    return json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def test_valid_consumed_permission_executes_once_and_attests_outcome():
    result, adapter = run()
    assert result.outcome is Outcome.SUCCEEDED
    assert result.reason_codes == (Reason.EXECUTION_SUCCEEDED,)
    assert adapter.calls == 1
    assert result.attestation is not None
    assert verify_continued_operation_execution_attestation(result.attestation)
    assert result.attestation.enforcement_evidence_digest == consumed().evidence_digest


def test_contract_is_frozen_versioned_canonical_and_rejects_duplicate_fields():
    req = request()
    document = execution_request_document(req)
    assert translate_untrusted_execution_request(document) == req
    assert translate_untrusted_execution_request(canonical_wire(document)) == req
    with pytest.raises(FrozenInstanceError):
        req.purpose = "changed"
    with pytest.raises(ContinuedOperationExecutionError, match="invalid"):
        translate_untrusted_execution_request({**document, "raw_command": "shutdown"})
    raw = canonical_wire(document).decode()
    duplicate = raw.replace('"authorization_id":', '"authorization_id":"' + h("forged") + '","authorization_id":', 1)
    with pytest.raises(ContinuedOperationExecutionError, match="invalid"):
        translate_untrusted_execution_request(duplicate)
    with pytest.raises(ContinuedOperationExecutionError, match="unsupported"):
        replace(req, schema_version="2.0")


@pytest.mark.parametrize("forbidden", [
    "command", "raw_command", "parameters", "arguments", "credentials", "token",
    "trusted", "permitted", "force_execute", "provider_response", "skip_verification",
])
def test_raw_command_parameter_and_trust_smuggling_is_rejected(forbidden):
    document = execution_request_document(request())
    document[forbidden] = "attacker-controlled"
    with pytest.raises(ContinuedOperationExecutionError):
        translate_untrusted_execution_request(document)


def test_missing_or_unavailable_authoritative_consumption_fails_closed():
    req = request()
    missing, adapter = run(
        req, record_repository=InMemoryContinuedOperationConsumptionRecordRepository(),
    )
    assert missing.outcome is Outcome.BLOCKED
    assert missing.reason_codes == (Reason.ENFORCEMENT_RECORD_NOT_FOUND,)
    assert adapter.calls == 0

    class ForgedResultRepository:
        def get_by_evidence_reference(self, reference):
            return {"enforcement_state": "permitted", "consumption_state": "consumed"}

    forged, adapter = run(req, record_repository=ForgedResultRepository())
    assert forged.outcome is Outcome.INDETERMINATE
    assert forged.reason_codes == (Reason.ENFORCEMENT_STATE_UNAVAILABLE,)
    assert adapter.calls == 0

    class Broken:
        def get_by_evidence_reference(self, reference):
            raise OSError("database path and password")

    unavailable, adapter = run(req, record_repository=Broken())
    assert unavailable.outcome is Outcome.INDETERMINATE
    assert unavailable.reason_codes == (Reason.ENFORCEMENT_STATE_UNAVAILABLE,)
    assert adapter.calls == 0


@pytest.mark.parametrize("field,value,reason", [
    ("authorization_id", h("other-auth"), Reason.AUTHORIZATION_MISMATCH),
    ("authorization_digest", h("other-artifact"), Reason.AUTHORIZATION_MISMATCH),
    ("enforcement_request_id", "other-request", Reason.ENFORCEMENT_REQUEST_MISMATCH),
    ("request_binding_digest", h("other-binding"), Reason.REQUEST_BINDING_MISMATCH),
    ("deployment_id", "other-deployment", Reason.DEPLOYMENT_MISMATCH),
    ("consumer_id", "other-consumer", Reason.CONSUMER_MISMATCH),
    ("enforcement_point_id", "other-point", Reason.ENFORCEMENT_POINT_MISMATCH),
    ("purpose", "other-purpose", Reason.PURPOSE_MISMATCH),
    ("operation_reference", "other-operation", Reason.OPERATION_MISMATCH),
    ("correlation_id", "other-correlation", Reason.CORRELATION_MISMATCH),
])
def test_every_a26_binding_mutation_is_blocked(field, value, reason):
    record = consumed()
    req = replace(request(record), **{field: value})
    result, adapter = run(req, record=record)
    assert result.outcome is Outcome.BLOCKED
    assert result.reason_codes == (reason,)
    assert adapter.calls == 0


def test_forged_evidence_and_manifest_substitution_are_blocked():
    record = consumed()
    forged = replace(request(record), enforcement_evidence_digest=h("forged"))
    result, adapter = run(forged, record=record)
    assert result.reason_codes == (Reason.ENFORCEMENT_EVIDENCE_MISMATCH,)
    assert adapter.calls == 0

    operation = manifest()
    substituted = replace(request(record, operation), operation_manifest_digest=h("forged"))
    result, adapter = run(substituted, record=record, operation=operation)
    assert result.reason_codes == (Reason.MANIFEST_DIGEST_MISMATCH,)
    assert adapter.calls == 0


@pytest.mark.parametrize("change,reason", [
    ({"requested_adapter": "unapproved"}, Reason.ADAPTER_NOT_PERMITTED),
    ({"adapter_contract_version": "2.0"}, Reason.ADAPTER_VERSION_UNSUPPORTED),
    ({"execution_policy_reference": "other-policy"}, Reason.EXECUTION_POLICY_MISMATCH),
])
def test_adapter_version_and_policy_allowlists_block_unapproved_execution(change, reason):
    result, adapter = run(replace(request(), **change))
    assert result.outcome is Outcome.BLOCKED
    assert result.reason_codes == (reason,)
    assert adapter.calls == 0


def test_capability_mismatch_and_expired_window_are_blocked():
    adapter = Adapter()
    adapter.capabilities = frozenset()
    result, adapter = run(adapter=adapter)
    assert result.reason_codes == (Reason.ADAPTER_CAPABILITY_MISMATCH,)
    assert adapter.calls == 0

    result, adapter = run(now=NOW + timedelta(minutes=2))
    assert result.reason_codes == (Reason.EXECUTION_WINDOW_EXPIRED,)
    assert adapter.calls == 0


@pytest.mark.parametrize("outcome,reason", [
    (Outcome.FAILED, Reason.EXECUTION_FAILED),
    (Outcome.REJECTED, Reason.PROVIDER_REJECTED),
    (Outcome.TIMED_OUT, Reason.PROVIDER_TIMED_OUT),
    (Outcome.OUTCOME_UNKNOWN, Reason.PROVIDER_OUTCOME_UNKNOWN),
])
def test_adapter_outcomes_remain_explicit_and_are_not_promoted(outcome, reason):
    result, adapter = run(adapter=Adapter(outcome))
    assert result.outcome is outcome
    assert result.reason_codes == (reason,)
    assert adapter.calls == 1
    assert verify_continued_operation_execution_attestation(result.attestation)


def test_adapter_exception_and_malformed_response_become_unknown_without_leaking_exception():
    result, adapter = run(adapter=Adapter(raises=True))
    assert result.outcome is Outcome.OUTCOME_UNKNOWN
    assert result.reason_codes == (Reason.PROVIDER_OUTCOME_UNKNOWN,)
    assert adapter.calls == 1
    assert "secret" not in json.dumps(public_continued_operation_execution(result).model_dump(mode="json"))

    class Malformed(Adapter):
        def execute(self, command):
            self.calls += 1
            return {"success": True, "token": "secret"}

    result, adapter = run(adapter=Malformed())
    assert result.outcome is Outcome.OUTCOME_UNKNOWN
    assert adapter.calls == 1


def test_exact_retry_recovers_result_without_reinvocation_and_changed_retry_conflicts():
    store = InMemoryContinuedOperationExecutionStateStore()
    adapter = Adapter()
    first, _ = run(adapter=adapter, state_store=store)
    second, _ = run(adapter=adapter, state_store=store)
    assert first.outcome is second.outcome is Outcome.SUCCEEDED
    assert second.idempotent
    assert second.reason_codes == (Reason.IDEMPOTENT_RESULT_RETURNED,)
    assert adapter.calls == 1

    changed = replace(request(), purpose="changed-purpose")
    conflict, _ = run(changed, adapter=adapter, state_store=store)
    assert conflict.outcome is Outcome.BLOCKED
    assert conflict.reason_codes in {
        (Reason.PURPOSE_MISMATCH,), (Reason.EXECUTION_REQUEST_CONFLICT,),
    }
    assert adapter.calls == 1


def test_new_attempt_cannot_reuse_consumed_authorization():
    store = InMemoryContinuedOperationExecutionStateStore()
    adapter = Adapter()
    run(adapter=adapter, state_store=store)
    changed = replace(
        request(), execution_attempt_id="execution-attempt-28", idempotency_key="idempotency-28",
    )
    result, _ = run(changed, adapter=adapter, state_store=store)
    assert result.reason_codes == (Reason.EXECUTION_ALREADY_CLAIMED,)
    assert adapter.calls == 1


@pytest.mark.parametrize("store_factory", [
    lambda tmp_path: InMemoryContinuedOperationExecutionStateStore(),
    lambda tmp_path: SqliteContinuedOperationExecutionStateStore(tmp_path / "execution.sqlite"),
])
def test_concurrent_requests_have_one_adapter_invocation(tmp_path, store_factory):
    store = store_factory(tmp_path)
    adapter = Adapter()
    with ThreadPoolExecutor(max_workers=12) as pool:
        results = list(pool.map(
            lambda _: run(adapter=adapter, state_store=store)[0], range(24),
        ))
    assert adapter.calls == 1
    assert sum(result.outcome is Outcome.SUCCEEDED for result in results) >= 1
    assert all(result.outcome in {
        Outcome.SUCCEEDED, Outcome.INDETERMINATE, Outcome.OUTCOME_UNKNOWN,
    } for result in results)


def test_sqlite_result_survives_store_recreation_and_exact_retry(tmp_path):
    path = tmp_path / "execution.sqlite"
    adapter = Adapter()
    first, _ = run(adapter=adapter, state_store=SqliteContinuedOperationExecutionStateStore(path))
    second, _ = run(adapter=adapter, state_store=SqliteContinuedOperationExecutionStateStore(path))
    assert first.outcome is second.outcome is Outcome.SUCCEEDED
    assert second.idempotent and adapter.calls == 1
    assert verify_continued_operation_execution_attestation(second.attestation)


def test_persistence_failure_after_possible_invocation_remains_unknown():
    class FailingFinalize(InMemoryContinuedOperationExecutionStateStore):
        def finalize(self, *, command_digest, result):
            raise OSError("database credentials")

    result, adapter = run(state_store=FailingFinalize())
    assert result.outcome is Outcome.OUTCOME_UNKNOWN
    assert result.reason_codes == (Reason.EXECUTION_STATE_UNAVAILABLE,)
    assert adapter.calls == 1
    assert verify_continued_operation_execution_attestation(result.attestation)


def test_attestation_mutation_fails_verification_and_command_is_domain_bound():
    record, operation = consumed(), manifest()
    req = request(record, operation)
    result, _ = run(req, record=record, operation=operation)
    assert result.attestation.execution_command_digest != req.request_binding_digest
    assert verify_continued_operation_execution_attestation(result.attestation)
    assert not verify_continued_operation_execution_attestation(
        replace(result.attestation, purpose="tampered-purpose")
    )


def test_public_projection_is_allowlisted_and_contains_no_protected_data():
    result, _ = run()
    public = public_continued_operation_execution(result)
    document = serialize_public_contract(public)
    assert set(document) == {
        "schema_version", "execution_attempt_id", "enforcement_request_id",
        "authorization_id", "deployment_id", "purpose", "operation_reference",
        "outcome", "reason_codes", "started_at", "completed_at",
        "attestation_reference", "correlation_id", "idempotent",
    }
    serialized = json.dumps(document)
    for forbidden in (
        "authorization_digest", "request_binding_digest", "manifest_digest",
        "provider_operation", "provider_response", "credentials", "database",
        "adapter_contract", "canonical_operation_input",
    ):
        assert forbidden not in serialized


def test_untrusted_clock_and_manifest_repository_failure_never_invoke_adapter():
    result, adapter = run(now=NOW.replace(microsecond=1))
    assert result.outcome is Outcome.INDETERMINATE
    assert result.reason_codes == (Reason.UNTRUSTED_TIME_SOURCE,)
    assert adapter.calls == 0

    class BrokenManifest:
        def get(self, reference):
            raise OSError("internal path")

    result, adapter = run(manifest_repository=BrokenManifest())
    assert result.outcome is Outcome.INDETERMINATE
    assert adapter.calls == 0
