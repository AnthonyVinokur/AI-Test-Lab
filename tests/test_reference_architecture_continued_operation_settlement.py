import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone
from hashlib import sha256

import pytest

from src.public_contract import serialize_public_contract
from src.reference_architecture_continued_operation_enforcement_contract import ContinuedOperationConsumptionRecord
from src.reference_architecture_continued_operation_execution import (
    InMemoryContinuedOperationConsumptionRecordRepository,
    InMemoryContinuedOperationExecutionStateStore,
    InMemoryProtectedOperationManifestRepository,
    execute_continued_operation,
    operation_manifest_digest,
)
from src.reference_architecture_continued_operation_execution_contract import (
    ContinuedOperationAdapterResult,
    ContinuedOperationExecutionOutcome,
    ContinuedOperationExecutionPolicy,
    ContinuedOperationExecutionReasonCode,
    ContinuedOperationExecutionRequest,
    ProtectedOperationManifest,
)
from src.reference_architecture_continued_operation_reconciliation import (
    InMemoryAuthoritativeExecutionEvidenceRepository,
    InMemoryOutcomeVerificationManifestRepository,
    InMemoryReconciliationEvidenceRepository,
    ObserverRegistry,
    reconcile_continued_operation,
)
from src.reference_architecture_continued_operation_reconciliation_contract import (
    AuthoritativeExecutionEvidence,
    ContinuedOperationReconciliationRequest,
    ContinuedOperationVerificationPolicy,
    ObservationValueState,
    OutcomeVerificationManifest,
    PostconditionKind,
    ProviderObservation,
    ReconciliationField,
    ReconciliationOutcome,
)
from src.reference_architecture_continued_operation_settlement import (
    HmacSettlementSigner,
    InMemorySettlementEvidenceRepository,
    InMemorySettlementPolicyRepository,
    InMemoryVerificationEvidenceRepository,
    SettlementCommitStatusUnknown,
    SqliteSettlementEvidenceRepository,
    public_protected_operation_settlement,
    settle_protected_operation,
    settlement_lifecycle_key,
    settlement_request_document,
    translate_untrusted_settlement_request,
    verify_settlement_evidence,
)
from src.reference_architecture_continued_operation_settlement_contract import (
    AuthoritativeVerificationEvidence,
    ContinuedOperationSettlementError,
    ProtectedOperationSettlementPolicy,
    ProtectedOperationSettlementRequest,
    ProtectedOperationSettlementStatus as Status,
    SettlementReasonCode as Reason,
)


START = datetime(2026, 9, 16, 17, 0, tzinfo=timezone.utc)
NOW = START + timedelta(seconds=5)
SIGNER = HmacSettlementSigner(b"a29-reference-signing-key-material-32-bytes-minimum")


def h(value):
    return sha256(value.encode()).hexdigest()


def field(value):
    return ReconciliationField("lifecycle_state", ObservationValueState.PRESENT, value)


def consumption():
    return ContinuedOperationConsumptionRecord(
        h("authorization"), h("authorization-artifact"), "enforcement-request-29",
        h("binding"), "deployment", "gateway", "enforcement-point",
        "serve-production", "continue-serving", START - timedelta(seconds=10),
        "enforcement-policy", h("a26-evidence"), "correlation-29",
    )


def operation_manifest():
    return ProtectedOperationManifest(
        "operation-manifest-29", "continue-serving", "1", h("parameters"),
        ("reference-adapter",), ("1.0",), ("continued-operation",), 30,
        ("deployment",), (), "at-most-once", "audit",
    )


class Adapter:
    identity = "reference-adapter"
    contract_version = "1.0"
    capabilities = frozenset({"continued-operation"})

    def execute(self, command):
        return ContinuedOperationAdapterResult(
            command.request.execution_attempt_id, ContinuedOperationExecutionOutcome.SUCCEEDED,
            ContinuedOperationExecutionReasonCode.EXECUTION_SUCCEEDED,
            START, START, "provider-operation-29", h("response"),
        )


def execution_evidence():
    record = consumption()
    manifest = operation_manifest()
    request = ContinuedOperationExecutionRequest(
        "execution-29", record.enforcement_request_id, record.authorization_id,
        record.authorization_digest, record.evidence_digest, record.evidence_digest,
        record.request_binding_digest, record.deployment_id, record.consumer_id,
        record.enforcement_point_id, record.purpose, record.operation_reference,
        manifest.reference, operation_manifest_digest(manifest), "reference-adapter", "1.0",
        "execution-policy", "execution-idempotency-29", START, record.correlation_id,
    )
    result = execute_continued_operation(
        request,
        consumption_repository=InMemoryContinuedOperationConsumptionRecordRepository((record,)),
        manifest_repository=InMemoryProtectedOperationManifestRepository((manifest,)),
        policy=ContinuedOperationExecutionPolicy(
            "execution-policy", 60, ("reference-adapter",), ("1.0",),
        ),
        adapters={"reference-adapter": Adapter()},
        state_store=InMemoryContinuedOperationExecutionStateStore(),
        trusted_clock=lambda: START,
    )
    assert result.attestation is not None
    return AuthoritativeExecutionEvidence(
        result.attestation.attestation_digest, request, record, manifest,
        result.attestation, True,
    )


class Observer:
    identity = "settlement-observer"
    version = "1.0"
    provider = "reference-provider"
    resource_type = "service"
    operation_reference = "continue-serving"
    manifest_version = "1"
    capabilities = frozenset({"read-state"})
    read_only = True
    enabled = True
    revoked = False

    def __init__(self, value):
        self.value = value
        self.calls = 0

    def observe(self, request):
        self.calls += 1
        if self.value is None:
            return ()
        return (ProviderObservation(
            "reference-provider", "service",
            "wrong-resource" if self.value == "__invalid__" else "service-primary",
            START + timedelta(seconds=2),
            (field(self.value),), True,
        ),)


def verification_source(value="active"):
    execution = execution_evidence()
    operation = execution.operation_manifest
    manifest = OutcomeVerificationManifest(
        "verification-manifest-29", "1", operation.reference, operation.version,
        operation_manifest_digest(operation), operation.operation_reference,
        operation.canonical_operation_input_digest, "reference-provider", "service",
        "service-primary", PostconditionKind.LIFECYCLE_STATE_EQUALS, (field("active"),),
        "1.0", "read-state",
    )
    request = ContinuedOperationReconciliationRequest(
        "verification-request-29", execution.evidence_reference,
        execution.request.execution_attempt_id, execution.consumption_record.enforcement_request_id,
        execution.consumption_record.authorization_id, "deployment", "gateway",
        "enforcement-point", "serve-production", "continue-serving", "service-primary",
        operation.canonical_operation_input_digest, operation.reference,
        operation_manifest_digest(operation), "reference-adapter", "1.0",
        manifest.reference, "verification-policy", "settlement-observer", "1.0",
        "verification-round-29", "verification-idempotency-29", NOW, "correlation-29",
    )
    result = reconcile_continued_operation(
        request,
        execution_repository=InMemoryAuthoritativeExecutionEvidenceRepository((execution,)),
        manifest_repository=InMemoryOutcomeVerificationManifestRepository((manifest,)),
        policy=ContinuedOperationVerificationPolicy("verification-policy", 30, 60, 10),
        observer_registry=ObserverRegistry((Observer(value),)),
        evidence_repository=InMemoryReconciliationEvidenceRepository(),
        trusted_clock=lambda: NOW,
    )
    assert result.attestation is not None
    return AuthoritativeVerificationEvidence(result.attestation, execution, True)


def settlement_policy(**changes):
    values = dict(
        policy_id="settlement-policy", version="1",
        allowed_verification_policy_ids=("verification-policy",),
        maximum_verification_age_seconds=30, mismatch_is_terminal=True,
        indeterminate_requires_review=True, require_execution_attestation=True,
        require_complete_evidence_chain=True,
    )
    values.update(changes)
    return ProtectedOperationSettlementPolicy(**values)


def settlement_request(source=None, **changes):
    source = source or verification_source()
    attestation = source.attestation
    values = dict(
        settlement_request_id="settlement-request-29", deployment_id="deployment",
        operation_id="continue-serving", execution_id="execution-29",
        verification_id=attestation.reconciliation_id,
        verification_evidence_digest=attestation.reconciliation_digest,
        settlement_policy_id="settlement-policy", settlement_policy_version="1",
        requested_at=NOW, requester_id="settlement-service", correlation_id="correlation-29",
    )
    values.update(changes)
    return ProtectedOperationSettlementRequest(**values)


def run(source=None, request=None, policy=None, store=None, now=NOW):
    source = source or verification_source()
    request = request or settlement_request(source)
    return settle_protected_operation(
        request,
        verification_repository=InMemoryVerificationEvidenceRepository((source,)),
        policy_repository=InMemorySettlementPolicyRepository((policy or settlement_policy(),)),
        settlement_repository=store or InMemorySettlementEvidenceRepository(),
        signer=SIGNER, trusted_clock=lambda: now,
    )


@pytest.mark.parametrize(("value", "status", "reason"), [
    ("active", Status.SETTLED_SUCCESS, Reason.EXPECTED_POSTCONDITION_VERIFIED),
    ("inactive", Status.SETTLED_FAILURE, Reason.EXPECTED_POSTCONDITION_MISMATCH),
    (None, Status.SUSPENDED, Reason.VERIFICATION_INDETERMINATE),
])
def test_deterministic_verified_mismatch_and_indeterminate_mapping(value, status, reason):
    result = run(source=verification_source(value))
    assert (result.status, result.reason_code, result.committed) == (status, reason, True)
    assert result.evidence is not None and verify_settlement_evidence(result.evidence, SIGNER)


def test_authoritative_invalid_a28_outcome_maps_to_durable_rejected():
    source = verification_source("__invalid__")
    assert source.attestation.outcome is ReconciliationOutcome.INVALID
    result = run(source=source)
    assert (result.status, result.reason_code, result.committed) == (
        Status.REJECTED, Reason.VERIFICATION_EVIDENCE_INVALID, True,
    )


def test_tampered_a28_attestation_is_rejected_without_settlement():
    source = verification_source()
    tampered = replace(source.attestation, outcome=ReconciliationOutcome.INVALID)
    result = run(source=replace(source, attestation=tampered))
    assert (result.status, result.reason_code, result.committed) == (
        Status.REJECTED, Reason.VERIFICATION_EVIDENCE_INVALID, False,
    )


def test_tamper_binding_unknown_policy_and_policy_allowlist_fail_closed():
    source = verification_source()
    wrong_binding = run(
        source=source, request=settlement_request(source, deployment_id="other-deployment"),
    )
    assert wrong_binding.reason_code is Reason.LIFECYCLE_BINDING_MISMATCH
    unknown = run(
        source=source,
        request=settlement_request(source, settlement_policy_version="2"),
    )
    assert unknown.reason_code is Reason.SETTLEMENT_POLICY_NOT_FOUND
    forbidden = run(source=source, policy=settlement_policy(
        allowed_verification_policy_ids=("another-policy",),
    ))
    assert forbidden.reason_code is Reason.SETTLEMENT_POLICY_NOT_ALLOWED


def test_stale_verification_suspends_and_never_promotes_to_success():
    source = verification_source()
    result = run(source=source, now=NOW + timedelta(seconds=31))
    assert (result.status, result.reason_code, result.committed) == (
        Status.SUSPENDED, Reason.VERIFICATION_EVIDENCE_EXPIRED, True,
    )


def test_nonterminal_mismatch_policy_can_only_make_result_stricter():
    result = run(
        source=verification_source("inactive"),
        policy=settlement_policy(mismatch_is_terminal=False),
    )
    assert result.status is Status.SUSPENDED


def test_exact_retry_is_idempotent_and_changed_request_conflicts():
    source = verification_source()
    request = settlement_request(source)
    store = InMemorySettlementEvidenceRepository()
    first = run(source=source, request=request, store=store)
    second = run(source=source, request=request, store=store)
    assert second == first
    changed = replace(request, requester_id="another-service")
    conflict = run(source=source, request=changed, store=store)
    assert (conflict.status, conflict.reason_code, conflict.committed) == (
        Status.REJECTED, Reason.CONFLICTING_SETTLEMENT, False,
    )


def test_concurrent_settlement_has_one_immutable_winner():
    source = verification_source()
    request = settlement_request(source)
    store = InMemorySettlementEvidenceRepository()
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(
            lambda _: run(source=source, request=request, store=store), range(8),
        ))
    committed = [result for result in results if result.committed]
    assert committed and len({result.evidence.settlement_id for result in committed}) == 1
    assert all(result.status in {Status.SETTLED_SUCCESS, Status.SUSPENDED} for result in results)


def test_sqlite_recovers_committed_and_distinguishes_interrupted_record(tmp_path):
    source = verification_source()
    request = settlement_request(source)
    path = tmp_path / "settlement.sqlite3"
    first = run(source=source, request=request, store=SqliteSettlementEvidenceRepository(path))
    recovered = SqliteSettlementEvidenceRepository(path).recover(settlement_lifecycle_key(request))
    assert recovered.result == first
    second = run(source=source, request=request, store=SqliteSettlementEvidenceRepository(path))
    assert second == first

    pending_path = tmp_path / "pending.sqlite3"
    pending = SqliteSettlementEvidenceRepository(pending_path)
    pending.claim(
        lifecycle_key=settlement_lifecycle_key(request),
        settlement_request_id=request.settlement_request_id,
        request_digest=h("different-request-digest"),
    )
    assert pending.recover(settlement_lifecycle_key(request)).result is None


def test_unknown_commit_never_returns_successful_settlement():
    class UnknownCommitStore(InMemorySettlementEvidenceRepository):
        def commit(self, **kwargs):
            raise SettlementCommitStatusUnknown("acknowledgement lost")

    result = run(store=UnknownCommitStore())
    assert (result.status, result.reason_code, result.committed) == (
        Status.SUSPENDED, Reason.SETTLEMENT_COMMIT_INDETERMINATE, False,
    )


def test_request_translation_is_strict_canonical_and_rejects_evidence_injection():
    request = settlement_request()
    document = settlement_request_document(request)
    encoded = json.dumps(document, sort_keys=True, separators=(",", ":")).encode()
    assert translate_untrusted_settlement_request(document) == request
    assert translate_untrusted_settlement_request(encoded) == request
    document["verification_evidence"] = {"outcome": "verified"}
    with pytest.raises(ContinuedOperationSettlementError):
        translate_untrusted_settlement_request(document)
    with pytest.raises(ContinuedOperationSettlementError):
        replace(request, schema_version="2")


def test_public_projection_is_allowlisted_and_excludes_protected_fields():
    source = verification_source()
    request = settlement_request(source)
    result = run(source=source, request=request)
    public = serialize_public_contract(public_protected_operation_settlement(request, result))
    assert set(public) == {
        "schema_version", "settlement_id", "settlement_request_id", "deployment_id",
        "operation_id", "execution_id", "verification_id", "status", "reason_code",
        "settled_at", "committed", "idempotent",
    }
    serialized = json.dumps(public)
    for forbidden in ("signature", "evidence_digest", "authorization", "provider", "secret", "exception"):
        assert forbidden not in serialized


def test_contracts_and_evidence_are_immutable():
    result = run()
    assert result.evidence is not None
    with pytest.raises(FrozenInstanceError):
        result.evidence.settlement_status = Status.REJECTED
