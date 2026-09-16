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
    execute_continued_operation,
    operation_manifest_digest,
)
from src.reference_architecture_continued_operation_execution_contract import (
    ContinuedOperationAdapterResult,
    ContinuedOperationExecutionOutcome as ExecutionOutcome,
    ContinuedOperationExecutionPolicy,
    ContinuedOperationExecutionReasonCode as ExecutionReason,
    ContinuedOperationExecutionRequest,
    ProtectedOperationManifest,
)
from src.reference_architecture_continued_operation_reconciliation import (
    InMemoryAuthoritativeExecutionEvidenceRepository,
    InMemoryOutcomeVerificationManifestRepository,
    InMemoryReconciliationEvidenceRepository,
    ObserverRegistry,
    ReconciliationCommitStatusUnknown,
    SqliteReconciliationEvidenceRepository,
    derive_expected_postcondition,
    normalize_observation,
    public_continued_operation_reconciliation,
    reconcile_continued_operation,
    reconciliation_request_document,
    translate_untrusted_reconciliation_request,
    verify_reconciliation_attestation,
)
from src.reference_architecture_continued_operation_reconciliation_contract import (
    AuthoritativeExecutionEvidence,
    ContinuedOperationReconciliationError,
    ContinuedOperationReconciliationRequest,
    ContinuedOperationVerificationPolicy,
    ObservationValueState,
    OutcomeVerificationManifest,
    PostconditionKind,
    ProviderObservation,
    ReconciliationField,
    ReconciliationOutcome as Outcome,
    ReconciliationReasonCode as Reason,
)


START = datetime(2026, 9, 16, 15, 0, tzinfo=timezone.utc)
NOW = START + timedelta(seconds=5)


def h(value: str) -> str:
    return sha256(value.encode()).hexdigest()


def field(name, value=None, state=ObservationValueState.PRESENT):
    return ReconciliationField(name, state, value)


def consumed():
    return ContinuedOperationConsumptionRecord(
        authorization_id=h("authorization"), authorization_digest=h("authorization-artifact"),
        enforcement_request_id="enforcement-request-28", request_binding_digest=h("binding"),
        deployment_id="deployment", consumer_id="production-gateway",
        enforcement_point_id="trusted-enforcement-gateway",
        purpose="serve-production-traffic", operation_reference="continue-serving-production",
        consumed_at=START - timedelta(seconds=5),
        policy_reference="continued-operation-enforcement-policy-1",
        evidence_digest=h("a26-permitted-evidence"), correlation_id="correlation-28",
    )


def operation_manifest():
    return ProtectedOperationManifest(
        reference="operation-manifest-28", operation_reference="continue-serving-production",
        version="1", canonical_operation_input_digest=h("canonical-parameters"),
        permitted_adapters=("reference-adapter",),
        permitted_adapter_contract_versions=("1.0",),
        required_capabilities=("continued-operation",), timeout_seconds=30,
        permitted_deployments=("deployment",), environment_restrictions=(),
        safe_retry_classification="at-most-once", result_retention_classification="audit",
    )


class ExecutionAdapter:
    identity = "reference-adapter"
    contract_version = "1.0"
    capabilities = frozenset({"continued-operation"})

    def __init__(self, outcome=ExecutionOutcome.SUCCEEDED):
        self.outcome = outcome

    def execute(self, command):
        reasons = {
            ExecutionOutcome.SUCCEEDED: ExecutionReason.EXECUTION_SUCCEEDED,
            ExecutionOutcome.FAILED: ExecutionReason.EXECUTION_FAILED,
            ExecutionOutcome.OUTCOME_UNKNOWN: ExecutionReason.PROVIDER_OUTCOME_UNKNOWN,
        }
        return ContinuedOperationAdapterResult(
            command.request.execution_attempt_id, self.outcome, reasons[self.outcome],
            START, None if self.outcome is ExecutionOutcome.OUTCOME_UNKNOWN else START,
            "provider-operation-28", h("sanitized-provider-response"),
        )


def authoritative_execution(outcome=ExecutionOutcome.SUCCEEDED):
    record = consumed()
    operation = operation_manifest()
    execution_request = ContinuedOperationExecutionRequest(
        execution_attempt_id="execution-attempt-28",
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
        idempotency_key="execution-idempotency-28", requested_at=START,
        correlation_id=record.correlation_id,
    )
    result = execute_continued_operation(
        execution_request,
        consumption_repository=InMemoryContinuedOperationConsumptionRecordRepository((record,)),
        manifest_repository=InMemoryProtectedOperationManifestRepository((operation,)),
        policy=ContinuedOperationExecutionPolicy(
            "continued-operation-execution-policy-1", 60,
            ("reference-adapter",), ("1.0",),
        ),
        adapters={"reference-adapter": ExecutionAdapter(outcome)},
        state_store=InMemoryContinuedOperationExecutionStateStore(),
        trusted_clock=lambda: START,
    )
    assert result.attestation is not None
    return AuthoritativeExecutionEvidence(
        result.attestation.attestation_digest, execution_request, record, operation,
        result.attestation, True,
    )


def verification_manifest(**overrides):
    operation = operation_manifest()
    values = dict(
        reference="outcome-manifest-28", version="1",
        operation_manifest_reference=operation.reference,
        operation_manifest_version=operation.version,
        operation_manifest_digest=operation_manifest_digest(operation),
        operation_reference=operation.operation_reference,
        canonical_parameter_digest=operation.canonical_operation_input_digest,
        provider="reference-provider", resource_type="service",
        target_resource_id="service-primary",
        postcondition_kind=PostconditionKind.LIFECYCLE_STATE_EQUALS,
        expected_fields=(field("lifecycle_state", "active"),),
        observer_version="1.0", required_observation_capability="read-service-state",
    )
    values.update(overrides)
    return OutcomeVerificationManifest(**values)


def request(evidence=None, manifest=None, **overrides):
    evidence = evidence or authoritative_execution()
    manifest = manifest or verification_manifest()
    record = evidence.consumption_record
    execution = evidence.request
    values = dict(
        reconciliation_request_id="reconciliation-request-28",
        execution_attestation_reference=evidence.evidence_reference,
        execution_attempt_id=execution.execution_attempt_id,
        enforcement_request_id=record.enforcement_request_id,
        authorization_id=record.authorization_id,
        deployment_id=record.deployment_id, consumer_id=record.consumer_id,
        enforcement_point_id=record.enforcement_point_id, purpose=record.purpose,
        operation_reference=record.operation_reference,
        target_resource_id=manifest.target_resource_id,
        canonical_parameter_digest=manifest.canonical_parameter_digest,
        operation_manifest_reference=execution.operation_manifest_reference,
        operation_manifest_digest=execution.operation_manifest_digest,
        execution_adapter_identity=execution.requested_adapter,
        execution_adapter_version=execution.adapter_contract_version,
        verification_manifest_reference=manifest.reference,
        verification_policy_reference="continued-operation-verification-policy-1",
        requested_observer_identity="reference-observer",
        requested_observer_version=manifest.observer_version,
        verification_round_id="verification-round-1",
        idempotency_key="reconciliation-idempotency-28", requested_at=NOW,
        correlation_id=record.correlation_id,
    )
    values.update(overrides)
    return ContinuedOperationReconciliationRequest(**values)


def observation(*fields, observed_at=START + timedelta(seconds=3), complete=True,
                provider="reference-provider", volatile=()):
    return ProviderObservation(
        provider, "service", "service-primary", observed_at,
        tuple(sorted(fields, key=lambda value: value.name)), complete, volatile,
    )


class Observer:
    identity = "reference-observer"
    version = "1.0"
    provider = "reference-provider"
    resource_type = "service"
    operation_reference = "continue-serving-production"
    manifest_version = "1"
    capabilities = frozenset({"read-service-state"})
    read_only = True
    enabled = True
    revoked = False

    def __init__(self, values=None, raises=False):
        self.values = values if values is not None else (
            observation(field("lifecycle_state", "active")),
        )
        self.raises = raises
        self.calls = 0
        self._lock = Lock()

    def observe(self, observation_request):
        with self._lock:
            self.calls += 1
        if self.raises:
            raise RuntimeError("provider token and secret response")
        return self.values


def policy(**overrides):
    values = dict(
        reference="continued-operation-verification-policy-1",
        maximum_observation_age_seconds=30,
        verification_window_seconds=60,
        observation_timeout_seconds=10,
    )
    values.update(overrides)
    return ContinuedOperationVerificationPolicy(**values)


def run(*, evidence=None, manifest=None, observer=None, req=None, store=None,
        now=NOW, verification_policy=None, execution_repository=None,
        manifest_repository=None, registry=None):
    evidence = evidence or authoritative_execution()
    manifest = manifest or verification_manifest()
    req = req or request(evidence, manifest)
    observer = observer or Observer()
    result = reconcile_continued_operation(
        req,
        execution_repository=(execution_repository or
            InMemoryAuthoritativeExecutionEvidenceRepository((evidence,))),
        manifest_repository=(manifest_repository or
            InMemoryOutcomeVerificationManifestRepository((manifest,))),
        policy=verification_policy or policy(),
        observer_registry=registry or ObserverRegistry((observer,)),
        evidence_repository=store or InMemoryReconciliationEvidenceRepository(),
        trusted_clock=lambda: now,
    )
    return result, observer


def canonical_wire(document):
    return json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def test_valid_a27_execution_with_fresh_expected_state_is_verified():
    result, observer = run()
    assert result.outcome is Outcome.VERIFIED
    assert result.reason_code is Reason.EXPECTED_STATE_OBSERVED
    assert observer.calls == 1
    assert result.attestation is not None
    assert verify_reconciliation_attestation(result.attestation)


def test_success_response_with_contradictory_state_is_mismatch():
    observer = Observer((observation(field("lifecycle_state", "inactive")),))
    result, _ = run(observer=observer)
    assert result.outcome is Outcome.MISMATCH
    assert result.reason_code is Reason.EXPECTED_STATE_MISMATCH


@pytest.mark.parametrize("execution_outcome", [
    ExecutionOutcome.OUTCOME_UNKNOWN, ExecutionOutcome.FAILED,
])
def test_failed_or_uncertain_a27_claim_does_not_suppress_independent_observation(execution_outcome):
    evidence = authoritative_execution(execution_outcome)
    result, observer = run(evidence=evidence, req=request(evidence))
    assert result.outcome is Outcome.VERIFIED
    assert observer.calls == 1


@pytest.mark.parametrize(("observer", "expected_reason"), [
    (Observer(()), Reason.OBSERVATION_UNAVAILABLE),
    (Observer((observation(field("lifecycle_state", None, ObservationValueState.UNKNOWN)),)),
     Reason.OBSERVATION_PARTIAL),
    (Observer((observation(field("lifecycle_state", "active"), complete=False),)),
     Reason.OBSERVATION_PARTIAL),
    (Observer(raises=True), Reason.OBSERVATION_UNAVAILABLE),
])
def test_missing_partial_and_failed_observations_are_indeterminate(observer, expected_reason):
    result, _ = run(observer=observer)
    assert result.outcome is Outcome.INDETERMINATE
    assert result.reason_code is expected_reason


def test_stale_pre_execution_future_and_conflicting_observations_fail_closed():
    stale, _ = run(observer=Observer((observation(
        field("lifecycle_state", "active"), observed_at=START + timedelta(seconds=1),
    ),)), now=START + timedelta(seconds=40))
    assert (stale.outcome, stale.reason_code) == (Outcome.INDETERMINATE, Reason.OBSERVATION_STALE)

    before, _ = run(observer=Observer((observation(
        field("lifecycle_state", "active"), observed_at=START - timedelta(seconds=1),
    ),)))
    assert before.reason_code is Reason.OBSERVATION_PRECEDES_EXECUTION

    future, _ = run(observer=Observer((observation(
        field("lifecycle_state", "active"), observed_at=NOW + timedelta(seconds=1),
    ),)))
    assert (future.outcome, future.reason_code) == (Outcome.INVALID, Reason.OBSERVATION_TIME_INVALID)

    conflicting, _ = run(observer=Observer((
        observation(field("lifecycle_state", "active")),
        observation(field("lifecycle_state", "inactive"), observed_at=START + timedelta(seconds=4)),
    )))
    assert conflicting.reason_code is Reason.OBSERVATIONS_CONFLICT


def test_substituted_execution_binding_and_uncommitted_evidence_are_invalid():
    evidence = authoritative_execution()
    substituted = request(evidence, deployment_id="other-deployment")
    result, observer = run(evidence=evidence, req=substituted)
    assert result.outcome is Outcome.INVALID
    assert result.reason_code is Reason.EXECUTION_BINDING_MISMATCH
    assert observer.calls == 0

    uncommitted = replace(evidence, committed=False)
    result, observer = run(evidence=uncommitted, req=request(evidence))
    assert result.outcome is Outcome.INVALID
    assert observer.calls == 0


def test_caller_cannot_supply_or_weaken_expected_postcondition():
    document = reconciliation_request_document(request())
    document["expected_postcondition"] = {"kind": "resource_exists"}
    with pytest.raises(ContinuedOperationReconciliationError):
        translate_untrusted_reconciliation_request(document)

    manifest = verification_manifest(expected_fields=(field("lifecycle_state", "active"),))
    expected = derive_expected_postcondition(authoritative_execution(), manifest)
    assert expected.fields == manifest.expected_fields
    with pytest.raises(FrozenInstanceError):
        expected.fields = ()


def test_request_translation_is_strict_canonical_and_rejects_duplicates():
    req = request()
    document = reconciliation_request_document(req)
    assert translate_untrusted_reconciliation_request(document) == req
    assert translate_untrusted_reconciliation_request(canonical_wire(document)) == req
    duplicate = canonical_wire(document).decode().replace(
        '"purpose":', '"purpose":"weakened","purpose":', 1,
    )
    with pytest.raises(ContinuedOperationReconciliationError):
        translate_untrusted_reconciliation_request(duplicate)
    with pytest.raises(ContinuedOperationReconciliationError):
        replace(req, schema_version="2.0")


@pytest.mark.parametrize(("change", "reason"), [
    ({"version": "2.0"}, Reason.OBSERVER_NOT_FOUND),
    ({"enabled": False}, Reason.OBSERVER_DISABLED),
    ({"revoked": True}, Reason.OBSERVER_REVOKED),
    ({"read_only": False}, Reason.OBSERVER_NOT_READ_ONLY),
    ({"capabilities": frozenset()}, Reason.OBSERVER_CAPABILITY_MISMATCH),
])
def test_only_exact_enabled_read_only_capable_observer_can_run(change, reason):
    class ChangedObserver(Observer):
        pass

    for name, value in change.items():
        setattr(ChangedObserver, name, value)
    observer = ChangedObserver()
    result, _ = run(observer=observer)
    assert result.outcome is Outcome.INVALID
    assert result.reason_code is reason
    assert observer.calls == 0


def test_ambiguous_observer_registration_fails_closed():
    first, second = Observer(), Observer()
    result, _ = run(observer=first, registry=ObserverRegistry((first, second)))
    assert result.reason_code is Reason.OBSERVER_AMBIGUOUS
    assert first.calls == second.calls == 0


def test_normalization_removes_manifest_irrelevant_volatile_fields_deterministically():
    left = observation(
        field("lifecycle_state", "active"), field("request_nonce", "one"),
        volatile=("request_nonce",),
    )
    right = observation(
        field("lifecycle_state", "active"), field("request_nonce", "two"),
        volatile=("request_nonce",),
    )
    assert normalize_observation(left) == normalize_observation(right)


@pytest.mark.parametrize(("kind", "expected_fields", "observed_fields", "outcome"), [
    (PostconditionKind.RESOURCE_EXISTS, (), (field("exists", True),), Outcome.VERIFIED),
    (PostconditionKind.RESOURCE_ABSENT, (), (field("exists", False),), Outcome.VERIFIED),
    (PostconditionKind.FIELDS_EQUAL, (field("replicas", 3),),
     (field("replicas", 3),), Outcome.VERIFIED),
    (PostconditionKind.REVISION_ADVANCED, (field("revision", 4),),
     (field("revision", 5),), Outcome.VERIFIED),
    (PostconditionKind.ATTRIBUTES_MATCH, (field("mode", "safe"),),
     (field("mode", "unsafe"),), Outcome.MISMATCH),
])
def test_manifest_defined_postcondition_kinds(kind, expected_fields, observed_fields, outcome):
    manifest = verification_manifest(postcondition_kind=kind, expected_fields=expected_fields)
    result, _ = run(
        manifest=manifest,
        observer=Observer((observation(*observed_fields),)),
        req=request(manifest=manifest),
    )
    assert result.outcome is outcome


def test_exact_retry_returns_committed_result_without_observing_again_and_change_conflicts():
    evidence = authoritative_execution()
    manifest = verification_manifest()
    req = request(evidence, manifest)
    observer = Observer()
    store = InMemoryReconciliationEvidenceRepository()
    first, _ = run(evidence=evidence, manifest=manifest, req=req, observer=observer, store=store)
    second, _ = run(evidence=evidence, manifest=manifest, req=req, observer=observer, store=store)
    assert second == first
    assert observer.calls == 1

    changed = replace(req, verification_round_id="changed-round")
    conflict, _ = run(
        evidence=evidence, manifest=manifest, req=changed, observer=observer, store=store,
    )
    assert (conflict.outcome, conflict.reason_code) == (
        Outcome.INVALID, Reason.RECONCILIATION_REQUEST_CONFLICT,
    )


def test_later_round_creates_new_immutable_evidence():
    evidence = authoritative_execution()
    manifest = verification_manifest()
    store = InMemoryReconciliationEvidenceRepository()
    first, _ = run(
        evidence=evidence, manifest=manifest, req=request(evidence, manifest), store=store,
    )
    later_request = request(
        evidence, manifest, reconciliation_request_id="reconciliation-request-28-round-2",
        verification_round_id="verification-round-2", idempotency_key="idempotency-round-2",
    )
    second, _ = run(
        evidence=evidence, manifest=manifest, req=later_request, store=store,
    )
    assert first.attestation is not None and second.attestation is not None
    assert first.attestation.reconciliation_id != second.attestation.reconciliation_id
    assert verify_reconciliation_attestation(first.attestation)


def test_concurrent_requests_have_one_observer_winner():
    evidence = authoritative_execution()
    manifest = verification_manifest()
    req = request(evidence, manifest)
    observer = Observer()
    store = InMemoryReconciliationEvidenceRepository()

    def invoke():
        return run(
            evidence=evidence, manifest=manifest, req=req, observer=observer, store=store,
        )[0]

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: invoke(), range(8)))
    assert observer.calls == 1
    assert sum(result.outcome is Outcome.VERIFIED for result in results) >= 1
    assert all(result.reason_code in {
        Reason.EXPECTED_STATE_OBSERVED, Reason.RECONCILIATION_IN_PROGRESS,
    } for result in results)


def test_sqlite_repository_recovers_exact_committed_result(tmp_path):
    evidence = authoritative_execution()
    manifest = verification_manifest()
    req = request(evidence, manifest)
    path = tmp_path / "reconciliation.sqlite3"
    first, observer = run(
        evidence=evidence, manifest=manifest, req=req,
        store=SqliteReconciliationEvidenceRepository(path),
    )
    second, _ = run(
        evidence=evidence, manifest=manifest, req=req, observer=observer,
        store=SqliteReconciliationEvidenceRepository(path),
    )
    assert second == first
    assert observer.calls == 1


def test_unknown_commit_is_not_reported_as_newly_verified():
    class UnknownCommitStore(InMemoryReconciliationEvidenceRepository):
        def commit(self, **kwargs):
            raise ReconciliationCommitStatusUnknown("disk acknowledgement lost")

    result, _ = run(store=UnknownCommitStore())
    assert result.outcome is Outcome.INDETERMINATE
    assert result.reason_code is Reason.COMMIT_STATUS_UNKNOWN
    assert result.attestation is None


def test_public_projection_is_allowlisted_and_contains_no_sensitive_material():
    result, _ = run()
    public = public_continued_operation_reconciliation(result)
    document = serialize_public_contract(public)
    assert set(document) == {
        "schema_version", "reconciliation_id", "execution_attempt_id",
        "operation_reference", "outcome", "reason_code", "observed_at",
        "evidence_issued_at",
    }
    serialized = json.dumps(document)
    for forbidden in (
        "authorization", "provider_response", "canonical_parameter", "observer",
        "manifest", "correlation", "token", "digest", "exception",
    ):
        assert forbidden not in serialized


def test_contracts_reject_mutable_nested_values_and_ambiguous_fields():
    with pytest.raises(ContinuedOperationReconciliationError):
        ReconciliationField("config", ObservationValueState.PRESENT, {"mutable": True})
    with pytest.raises(ContinuedOperationReconciliationError):
        ReconciliationField("state", ObservationValueState.UNKNOWN, "active")
    with pytest.raises(ContinuedOperationReconciliationError):
        ProviderObservation(
            "provider", "service", "resource", NOW,
            (field("z", 1), field("a", 2)), True,
        )


def test_verification_window_expiry_does_not_call_observer():
    observer = Observer()
    result, _ = run(observer=observer, now=START + timedelta(seconds=61))
    assert (result.outcome, result.reason_code) == (
        Outcome.INDETERMINATE, Reason.VERIFICATION_WINDOW_EXPIRED,
    )
    assert observer.calls == 0
