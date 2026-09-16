import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone
from hashlib import sha256

import pytest

from src.public_contract import serialize_public_contract
from src.reference_architecture_continued_operation_response import (
    HmacResponseSigner,
    InMemoryResponseAuthorizationRepository,
    InMemoryResponseManifestRepository,
    InMemoryResponsePolicyRepository,
    InMemorySettlementRecordRepository,
    atl_a20_remediation_request,
    authorize_settled_outcome_response,
    create_atl_a20_handoff,
    response_manifest_digest,
    response_policy_digest,
)
from src.reference_architecture_continued_operation_response_contract import (
    AuthoritativeSettlementRecord,
    ResponseManifest,
    ResponsePolicy,
    ResponseType,
    SettledOutcomeResponseRequest,
)
from src.reference_architecture_continued_operation_settlement import HmacSettlementSigner
from src.reference_architecture_continued_operation_settlement_contract import (
    ProtectedOperationSettlementEvidence,
    ProtectedOperationSettlementStatus,
    SettlementReasonCode,
)
from src.reference_architecture_deployment_recovery import sign_decision, verify_post_remediation
from src.reference_architecture_deployment_recovery_contract import (
    RecoveryDecisionStatus,
    RecoveryExecutionAttestation,
    RecoveryExecutionStatus,
)
from src.reference_architecture_response_outcome_reconciliation import (
    HmacReconciliationSigner,
    InMemoryPostRemediationVerificationRecordRepository,
    InMemoryReconciliationPolicyRepository,
    InMemoryRemediationDecisionRecordRepository,
    InMemoryRemediationExecutionRecordRepository,
    InMemoryResponseAuthorizationRecordRepository,
    InMemoryResponseReconciliationRepository,
    ReconciliationPersistenceError,
    SqliteResponseReconciliationRepository,
    post_remediation_verification_digest,
    public_response_outcome_reconciliation,
    reconcile_authorized_response,
    reconciliation_lifecycle_key,
    reconciliation_request_document,
    remediation_decision_digest,
    remediation_execution_digest,
    translate_untrusted_reconciliation_request,
    verify_closure_handoff,
    verify_reconciliation_evidence,
)
from src.reference_architecture_response_outcome_reconciliation_contract import (
    AuthoritativePostRemediationVerificationRecord,
    AuthoritativeRemediationDecisionRecord,
    AuthoritativeRemediationExecutionRecord,
    AuthoritativeResponseAuthorizationRecord,
    ReconciliationOutcome,
    ReconciliationPolicy,
    ReconciliationReasonCode,
    ResponseOutcomeReconciliationError,
    ResponseOutcomeReconciliationRequest,
)


NOW = datetime(2026, 9, 16, 21, 0, tzinfo=timezone.utc)
SETTLEMENT_SIGNER = HmacSettlementSigner(b"a29-reference-signing-key-material-32-bytes-minimum")
RESPONSE_SIGNER = HmacResponseSigner(b"a30-reference-signing-key-material-32-bytes-minimum")
RECONCILIATION_SIGNER = HmacReconciliationSigner(
    b"a31-reference-signing-key-material-32-bytes-minimum"
)


def h(value):
    return sha256(value.encode()).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def authorized_response():
    values = {
        "contract_version": "1.0", "deployment_id": "deployment",
        "enforcement_evidence_digest": h("a26"), "execution_evidence_digest": h("a27"),
        "operation_id": "continue-serving", "execution_id": "execution-31",
        "reason_code": SettlementReasonCode.EXPECTED_POSTCONDITION_MISMATCH.value,
        "settled_at": "2026-09-16T20:59:00Z", "settlement_policy_id": "settlement-policy",
        "settlement_policy_version": "1",
        "settlement_status": ProtectedOperationSettlementStatus.SETTLED_FAILURE.value,
        "verification_evidence_digest": h("a28"), "verification_id": h("verification"),
    }
    domain = "ai-test-lab:atl-a.29:settlement-evidence:v1"
    evidence_digest = sha256(canonical({"domain": domain, **values})).hexdigest()
    settlement_id = sha256(canonical({"domain": domain, **values,
                                      "evidence_digest": evidence_digest})).hexdigest()
    settlement = ProtectedOperationSettlementEvidence(
        settlement_id, ProtectedOperationSettlementStatus.SETTLED_FAILURE,
        "deployment", "continue-serving", "execution-31", h("verification"),
        h("a26"), h("a27"), h("a28"), "settlement-policy", "1",
        SettlementReasonCode.EXPECTED_POSTCONDITION_MISMATCH, NOW - timedelta(minutes=1),
        evidence_digest, SETTLEMENT_SIGNER.sign(bytes.fromhex(evidence_digest)),
    )
    source = AuthoritativeSettlementRecord(
        settlement, True, "enforcement-request-31", h("original-authorization"),
        ("deployment", "service-primary"),
    )
    manifest = ResponseManifest(
        "rollback-manifest", "1", ResponseType.REMEDIATION,
        (ProtectedOperationSettlementStatus.SETTLED_FAILURE,), "rollback-release",
        ("settlement",), ("deployment", "service-primary"), (), 1, 120,
        ("incident-responder",), ("verify-after-remediation",), True,
    )
    policy = ResponsePolicy(
        "response-policy", "1", (ResponseType.REMEDIATION,), (),
        ("rollback-manifest@1",), ("deployment", "service-primary"),
        ("incident-responder",), 60, True,
    )
    request = SettledOutcomeResponseRequest(
        "response-request-31", "response-key-31", settlement_id, evidence_digest,
        policy.policy_id, policy.version, response_policy_digest(policy), manifest.manifest_id,
        manifest.version, response_manifest_digest(manifest), ResponseType.REMEDIATION,
        ("deployment",), "response-service", "incident-responder", NOW, "correlation-31",
    )
    result = authorize_settled_outcome_response(
        request, settlement_repository=InMemorySettlementRecordRepository((source,)),
        policy_repository=InMemoryResponsePolicyRepository((policy,)),
        manifest_repository=InMemoryResponseManifestRepository((manifest,)),
        authorization_repository=InMemoryResponseAuthorizationRepository(),
        settlement_signer=SETTLEMENT_SIGNER, response_signer=RESPONSE_SIGNER,
        trusted_clock=lambda: NOW,
    )
    return result.evidence


def records(*, verification="passed", execution_status=RecoveryExecutionStatus.EXECUTED,
            capability="rollback-release", scope=("deployment",),
            constraints=("verify-after-remediation",), attempt=1):
    authorization = authorized_response()
    handoff = create_atl_a20_handoff(authorization, signer=RESPONSE_SIGNER,
                                    trusted_clock=lambda: NOW)
    remediation = atl_a20_remediation_request(
        handoff, authorization=authorization, signer=RESPONSE_SIGNER,
        trusted_clock=lambda: NOW, requested_at=NOW,
    )
    decision = sign_decision(
        remediation, RecoveryDecisionStatus.APPROVED, NOW + timedelta(seconds=55),
        "recovery-authority",
    )
    execution = RecoveryExecutionAttestation(
        remediation, execution_status, h("before"), h("after"), NOW + timedelta(seconds=10)
    )
    flags = {"passed": (True, True), "failed": (True, False), "unavailable": (None, None)}
    integrity, outcome = flags[verification]
    post_verification = verify_post_remediation(
        execution, integrity_verified=integrity, outcome_verified=outcome,
        integrity_evidence_digest=h("integrity"), outcome_evidence_digest=h("outcome"),
        verified_at=NOW + timedelta(seconds=15),
    )
    decision_record = AuthoritativeRemediationDecisionRecord(
        "remediation-decision-31", remediation_decision_digest(decision), decision,
        authorization.response_authorization_id, True,
    )
    execution_record = AuthoritativeRemediationExecutionRecord(
        "execution-attestation-31", remediation_execution_digest(execution), execution,
        authorization.response_authorization_id, decision_record.remediation_decision_id,
        capability, scope, constraints, authorization.response_manifest_digest, attempt, True,
    )
    verification_record = AuthoritativePostRemediationVerificationRecord(
        "post-remediation-verification-31", post_remediation_verification_digest(post_verification),
        post_verification, execution_record.execution_attestation_id, scope, True,
    )
    return authorization, decision_record, execution_record, verification_record


def reconciliation_request(authorization=None, **changes):
    authorization = authorization or authorized_response()
    values = dict(
        request_id="reconciliation-request-31", idempotency_key="reconciliation-key-31",
        response_authorization_id=authorization.response_authorization_id,
        remediation_decision_id="remediation-decision-31",
        execution_attestation_id="execution-attestation-31",
        post_remediation_verification_id="post-remediation-verification-31",
        reconciliation_policy_version="1", requested_at=NOW + timedelta(seconds=20),
    )
    values.update(changes)
    return ResponseOutcomeReconciliationRequest(**values)


def run(*, current_records=None, request=None, store=None, now=None):
    current_records = current_records or records()
    authorization, decision, execution, verification = current_records
    request = request or reconciliation_request(authorization)
    policy = ReconciliationPolicy("response-reconciliation-policy", "1", "1",
                                  "close-verified-incident", 120)
    return reconcile_authorized_response(
        request,
        authorization_repository=InMemoryResponseAuthorizationRecordRepository(
            (AuthoritativeResponseAuthorizationRecord(authorization, True),)),
        decision_repository=InMemoryRemediationDecisionRecordRepository((decision,)),
        execution_repository=InMemoryRemediationExecutionRecordRepository((execution,)),
        verification_repository=InMemoryPostRemediationVerificationRecordRepository((verification,)),
        policy_repository=InMemoryReconciliationPolicyRepository((policy,)),
        reconciliation_repository=store or InMemoryResponseReconciliationRepository(),
        response_signer=RESPONSE_SIGNER, reconciliation_signer=RECONCILIATION_SIGNER,
        trusted_clock=lambda: now or NOW + timedelta(seconds=20),
    )


def test_verified_recovery_is_signed_and_alone_creates_a21_handoff():
    store = InMemoryResponseReconciliationRepository()
    commit = run(store=store)
    assert commit.evidence.outcome is ReconciliationOutcome.VERIFIED_RECOVERY
    assert commit.evidence.closure_eligible and commit.closure_handoff is not None
    assert verify_reconciliation_evidence(commit.evidence, RECONCILIATION_SIGNER)
    assert verify_closure_handoff(
        commit.closure_handoff, reconciliation_repository=store,
        signer=RECONCILIATION_SIGNER, trusted_clock=lambda: NOW + timedelta(seconds=21),
        required_policy_version="1",
    )


@pytest.mark.parametrize(("verification", "outcome", "reason"), [
    ("failed", ReconciliationOutcome.RESPONSE_FAILED,
     ReconciliationReasonCode.RECOVERY_VERIFICATION_FAILED),
    ("unavailable", ReconciliationOutcome.RESPONSE_INDETERMINATE,
     ReconciliationReasonCode.RECOVERY_VERIFICATION_INCONCLUSIVE),
])
def test_failed_and_inconclusive_verification_keep_incident_open(verification, outcome, reason):
    commit = run(current_records=records(verification=verification))
    assert commit.evidence.outcome is outcome
    assert commit.evidence.reason_codes == (reason,)
    assert not commit.evidence.closure_eligible and commit.closure_handoff is None


@pytest.mark.parametrize(("changes", "reason"), [
    ({"capability": "expanded-capability"}, ReconciliationReasonCode.CAPABILITY_MISMATCH),
    ({"scope": ("deployment", "other")}, ReconciliationReasonCode.SCOPE_EXPANSION),
    ({"constraints": ()}, ReconciliationReasonCode.CONSTRAINTS_WEAKENED),
    ({"attempt": 2}, ReconciliationReasonCode.ATTEMPT_LIMIT_EXCEEDED),
])
def test_capability_scope_constraints_and_attempt_tampering_are_rejected(changes, reason):
    commit = run(current_records=records(**changes))
    assert commit.evidence.outcome is ReconciliationOutcome.REJECTED
    assert commit.evidence.reason_codes == (reason,)
    assert commit.closure_handoff is None


def test_verification_for_a_different_target_is_rejected():
    authorization, decision, execution, verification = records()
    verification = replace(verification, target_scope=("service-primary",))
    commit = run(current_records=(authorization, decision, execution, verification))
    assert commit.evidence.outcome is ReconciliationOutcome.REJECTED
    assert commit.evidence.reason_codes == (ReconciliationReasonCode.VERIFICATION_EVIDENCE_INVALID,)


def test_tampered_and_uncommitted_authoritative_records_never_advance():
    authorization, decision, execution, verification = records()
    tampered = replace(execution, execution_digest=h("tampered"))
    rejected = run(current_records=(authorization, decision, tampered, verification))
    assert rejected.evidence.outcome is ReconciliationOutcome.REJECTED
    uncommitted = reconcile_authorized_response(
            reconciliation_request(authorization),
            authorization_repository=InMemoryResponseAuthorizationRecordRepository(
                (AuthoritativeResponseAuthorizationRecord(authorization, False),)),
            decision_repository=InMemoryRemediationDecisionRecordRepository((decision,)),
            execution_repository=InMemoryRemediationExecutionRecordRepository((execution,)),
            verification_repository=InMemoryPostRemediationVerificationRecordRepository((verification,)),
            policy_repository=InMemoryReconciliationPolicyRepository((
                ReconciliationPolicy("policy", "1", "1", "close-incident", 60),)),
            reconciliation_repository=InMemoryResponseReconciliationRepository(),
            response_signer=RESPONSE_SIGNER, reconciliation_signer=RECONCILIATION_SIGNER,
            trusted_clock=lambda: NOW + timedelta(seconds=20),
        )
    assert uncommitted.evidence.outcome is ReconciliationOutcome.REJECTED
    assert uncommitted.evidence.reason_codes == (ReconciliationReasonCode.AUTHORIZATION_INVALID,)


def test_expired_unexecuted_authorization_is_committed_without_handoff():
    authorization, decision, _, _ = records()
    request = reconciliation_request(authorization)
    policy = ReconciliationPolicy("policy", "1", "1", "close-incident", 60)
    store = InMemoryResponseReconciliationRepository()
    commit = reconcile_authorized_response(
        request,
        authorization_repository=InMemoryResponseAuthorizationRecordRepository(
            (AuthoritativeResponseAuthorizationRecord(authorization, True),)),
        decision_repository=InMemoryRemediationDecisionRecordRepository((decision,)),
        execution_repository=InMemoryRemediationExecutionRecordRepository(),
        verification_repository=InMemoryPostRemediationVerificationRecordRepository(),
        policy_repository=InMemoryReconciliationPolicyRepository((policy,)),
        reconciliation_repository=store, response_signer=RESPONSE_SIGNER,
        reconciliation_signer=RECONCILIATION_SIGNER,
        trusted_clock=lambda: NOW + timedelta(seconds=61),
    )
    assert commit.evidence.outcome is ReconciliationOutcome.EXPIRED_UNEXECUTED
    assert not commit.evidence.closure_eligible and commit.closure_handoff is None


def test_exact_retry_is_byte_equivalent_and_changed_key_reuse_conflicts():
    current = records(); request = reconciliation_request(current[0])
    store = InMemoryResponseReconciliationRepository()
    first = run(current_records=current, request=request, store=store)
    assert run(current_records=current, request=request, store=store) == first
    changed = replace(request, request_id="changed-request")
    with pytest.raises(ResponseOutcomeReconciliationError, match="IDEMPOTENCY_CONFLICT"):
        run(current_records=current, request=changed, store=store)


def test_concurrent_requests_create_one_authoritative_reconciliation():
    current = records(); request = reconciliation_request(current[0])
    store = InMemoryResponseReconciliationRepository()
    def invoke(_):
        try:
            return run(current_records=current, request=request, store=store)
        except ResponseOutcomeReconciliationError:
            return None
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(invoke, range(8)))
    committed = [item for item in results if item is not None]
    assert committed
    assert len({item.evidence.reconciliation_id for item in committed}) == 1


def test_sqlite_restart_returns_same_atomic_reconciliation_and_handoff(tmp_path):
    current = records(); request = reconciliation_request(current[0])
    path = tmp_path / "reconciliation.sqlite3"
    first = run(current_records=current, request=request,
                store=SqliteResponseReconciliationRepository(path))
    restarted = SqliteResponseReconciliationRepository(path)
    recovered = restarted.recover(reconciliation_lifecycle_key(request))
    assert recovered.commit == first
    assert restarted.get_handoff(first.closure_handoff.handoff_id) == first.closure_handoff


def test_atomic_commit_failure_exposes_neither_reconciliation_nor_handoff():
    class FailingStore(InMemoryResponseReconciliationRepository):
        def commit(self, **kwargs):
            raise ReconciliationPersistenceError("injected failure")
    store = FailingStore()
    with pytest.raises(ResponseOutcomeReconciliationError, match="REPOSITORY_UNAVAILABLE"):
        run(store=store)
    assert store._by_id == {} and store._handoffs == {}


def test_public_dto_is_allowlisted_and_redacted():
    evidence = run().evidence
    public = serialize_public_contract(public_response_outcome_reconciliation(evidence))
    assert set(public) == {
        "schema_version", "reconciliation_id", "incident_id", "outcome", "reason_codes",
        "closure_eligible", "policy_version", "created_at", "protected_operation_id",
        "settlement_id", "response_authorization_id", "remediation_decision_id",
        "execution_attestation_id", "post_remediation_verification_id",
    }
    encoded = json.dumps(public)
    for forbidden in ("signature", "signer", "constraint", "manifest", "capability",
                      "evidence_digest", "before_digest", "after_digest"):
        assert forbidden not in encoded


def test_request_translation_rejects_caller_supplied_authority_and_evidence_is_immutable():
    request = reconciliation_request()
    document = reconciliation_request_document(request)
    assert translate_untrusted_reconciliation_request(document) == request
    assert translate_untrusted_reconciliation_request(canonical(document)) == request
    document["outcome"] = "verified_recovery"
    with pytest.raises(ResponseOutcomeReconciliationError):
        translate_untrusted_reconciliation_request(document)
    evidence = run().evidence
    with pytest.raises(FrozenInstanceError):
        evidence.actual_scope = ("wider",)


def test_complete_a26_through_a31_lineage_is_bound():
    evidence = run().evidence
    assert evidence.settlement_digest == authorized_response().settlement_digest
    assert evidence.response_authorization_digest == authorized_response().authorization_digest
    assert evidence.protected_operation_id == "continue-serving"
    assert verify_reconciliation_evidence(evidence, RECONCILIATION_SIGNER)
