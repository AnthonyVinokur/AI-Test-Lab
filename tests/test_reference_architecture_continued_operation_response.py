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
    SqliteResponseAuthorizationRepository,
    atl_a20_remediation_request,
    authorize_settled_outcome_response,
    create_atl_a20_handoff,
    public_settled_outcome_response,
    response_lifecycle_key,
    response_manifest_digest,
    response_policy_digest,
    response_request_document,
    translate_untrusted_response_request,
    verify_atl_a20_handoff,
    verify_response_authorization,
)
from src.reference_architecture_continued_operation_response_contract import (
    AuthoritativeSettlementRecord,
    ContinuedOperationResponseError,
    ResponseManifest,
    ResponseOutcome,
    ResponsePolicy,
    ResponseReasonCode,
    ResponseType,
    SettledOutcomeResponseRequest,
)
from src.reference_architecture_continued_operation_settlement import HmacSettlementSigner
from src.reference_architecture_continued_operation_settlement_contract import (
    ProtectedOperationSettlementEvidence,
    ProtectedOperationSettlementStatus as SettlementStatus,
    SettlementReasonCode,
)


NOW = datetime(2026, 9, 16, 20, 0, tzinfo=timezone.utc)
SETTLEMENT_SIGNER = HmacSettlementSigner(b"a29-reference-signing-key-material-32-bytes-minimum")
RESPONSE_SIGNER = HmacResponseSigner(b"a30-reference-signing-key-material-32-bytes-minimum")


def h(value):
    return sha256(value.encode()).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def settlement(status=SettlementStatus.SETTLED_FAILURE):
    reason = (SettlementReasonCode.EXPECTED_POSTCONDITION_MISMATCH
              if status is not SettlementStatus.REJECTED
              else SettlementReasonCode.VERIFICATION_EVIDENCE_INVALID)
    values = {
        "contract_version": "1.0", "deployment_id": "deployment",
        "enforcement_evidence_digest": h("a26"), "execution_evidence_digest": h("a27"),
        "operation_id": "continue-serving", "execution_id": "execution-30",
        "reason_code": reason.value, "settled_at": "2026-09-16T19:59:00Z",
        "settlement_policy_id": "settlement-policy", "settlement_policy_version": "1",
        "settlement_status": status.value, "verification_evidence_digest": h("a28"),
        "verification_id": h("verification"),
    }
    domain = "ai-test-lab:atl-a.29:settlement-evidence:v1"
    evidence_digest = sha256(canonical({"domain": domain, **values})).hexdigest()
    settlement_id = sha256(canonical({"domain": domain, **values,
                                      "evidence_digest": evidence_digest})).hexdigest()
    return ProtectedOperationSettlementEvidence(
        settlement_id, status, "deployment", "continue-serving", "execution-30",
        h("verification"), h("a26"), h("a27"), h("a28"), "settlement-policy", "1",
        reason, NOW - timedelta(minutes=1), evidence_digest,
        SETTLEMENT_SIGNER.sign(bytes.fromhex(evidence_digest)),
    )


def source(status=SettlementStatus.SETTLED_FAILURE):
    return AuthoritativeSettlementRecord(
        settlement(status), True, "enforcement-request-30", h("authorization-30"),
        ("deployment", "service-primary"),
    )


def manifest(response_type=ResponseType.REMEDIATION, statuses=(SettlementStatus.SETTLED_FAILURE,), **changes):
    values = dict(
        manifest_id=f"{response_type.value}-manifest", version="1", response_type=response_type,
        permitted_settlement_statuses=statuses, remediation_capability="rollback-release",
        required_evidence=("settlement",), permitted_scopes=("deployment", "service-primary"),
        prohibited_operations=(), maximum_attempts=1, lifetime_seconds=120,
        required_roles=("incident-responder",), constraints=("verify-after-remediation",),
        post_remediation_verification_required=True,
    )
    values.update(changes)
    return ResponseManifest(**values)


def policy(manifest_value=None, **changes):
    manifest_value = manifest_value or manifest()
    values = dict(
        policy_id="response-policy", version="1",
        permitted_failure_types=(ResponseType.REMEDIATION, ResponseType.CONTAINMENT),
        permitted_suspended_types=(ResponseType.MANUAL_REVIEW, ResponseType.INVESTIGATION,
                                   ResponseType.REVERIFICATION),
        approved_manifest_references=(f"{manifest_value.manifest_id}@{manifest_value.version}",),
        permitted_scopes=("deployment", "service-primary"),
        authorized_roles=("incident-responder",), maximum_authorization_seconds=60,
        require_manual_review_for_suspended=True,
    )
    values.update(changes)
    return ResponsePolicy(**values)


def request(source_value=None, policy_value=None, manifest_value=None, **changes):
    source_value = source_value or source()
    manifest_value = manifest_value or manifest()
    policy_value = policy_value or policy(manifest_value)
    values = dict(
        response_request_id="response-request-30", response_idempotency_key="response-key-30",
        settlement_id=source_value.evidence.settlement_id,
        settlement_digest=source_value.evidence.evidence_digest,
        policy_id=policy_value.policy_id, policy_version=policy_value.version,
        policy_digest=response_policy_digest(policy_value),
        response_manifest_id=manifest_value.manifest_id,
        response_manifest_version=manifest_value.version,
        response_manifest_digest=response_manifest_digest(manifest_value),
        requested_response_type=manifest_value.response_type,
        requested_scope=("deployment",), requester_id="response-service",
        requester_role="incident-responder", requested_at=NOW,
        correlation_id="correlation-30",
    )
    values.update(changes)
    return SettledOutcomeResponseRequest(**values)


def run(source_value=None, policy_value=None, manifest_value=None, request_value=None,
        store=None, now=NOW):
    source_value = source_value or source()
    manifest_value = manifest_value or manifest()
    policy_value = policy_value or policy(manifest_value)
    request_value = request_value or request(source_value, policy_value, manifest_value)
    return authorize_settled_outcome_response(
        request_value,
        settlement_repository=InMemorySettlementRecordRepository((source_value,)),
        policy_repository=InMemoryResponsePolicyRepository((policy_value,)),
        manifest_repository=InMemoryResponseManifestRepository((manifest_value,)),
        authorization_repository=store or InMemoryResponseAuthorizationRepository(),
        settlement_signer=SETTLEMENT_SIGNER, response_signer=RESPONSE_SIGNER,
        trusted_clock=lambda: now,
    )


def test_failure_creates_one_bounded_signed_authorization_and_a20_handoff():
    result = run()
    assert (result.outcome, result.reason_code, result.committed) == (
        ResponseOutcome.AUTHORIZED, ResponseReasonCode.RESPONSE_AUTHORIZED, True)
    assert result.evidence is not None
    assert result.evidence.scope == ("deployment",) and result.evidence.maximum_attempts == 1
    assert verify_response_authorization(result.evidence, RESPONSE_SIGNER, now=NOW)
    handoff = create_atl_a20_handoff(result.evidence, signer=RESPONSE_SIGNER,
                                    trusted_clock=lambda: NOW)
    assert verify_atl_a20_handoff(
        handoff, result.evidence, signer=RESPONSE_SIGNER, trusted_clock=lambda: NOW)
    remediation = atl_a20_remediation_request(
        handoff, authorization=result.evidence, signer=RESPONSE_SIGNER,
        trusted_clock=lambda: NOW, requested_at=NOW)
    assert remediation.incident_id == result.evidence.incident_id
    assert remediation.action == "rollback-release"
    assert remediation.action_fingerprint == result.evidence.response_manifest_digest
    substituted = replace(handoff, action="different-capability")
    assert not verify_atl_a20_handoff(
        substituted, result.evidence, signer=RESPONSE_SIGNER, trusted_clock=lambda: NOW)
    with pytest.raises(ContinuedOperationResponseError):
        atl_a20_remediation_request(
            substituted, authorization=result.evidence, signer=RESPONSE_SIGNER,
            trusted_clock=lambda: NOW, requested_at=NOW)


def test_suspended_cannot_authorize_failure_assuming_remediation():
    suspended = source(SettlementStatus.SUSPENDED)
    result = run(source_value=suspended, request_value=request(suspended))
    assert (result.outcome, result.reason_code, result.committed) == (
        ResponseOutcome.MANUAL_REVIEW_REQUIRED, ResponseReasonCode.MANUAL_REVIEW_REQUIRED, False)


def test_suspended_can_issue_only_safe_manual_review_authority():
    suspended = source(SettlementStatus.SUSPENDED)
    safe_manifest = manifest(ResponseType.MANUAL_REVIEW, (SettlementStatus.SUSPENDED,),
                             remediation_capability="operator-investigation")
    safe_policy = policy(safe_manifest)
    safe_request = request(suspended, safe_policy, safe_manifest)
    result = run(suspended, safe_policy, safe_manifest, safe_request)
    assert result.outcome is ResponseOutcome.MANUAL_REVIEW_REQUIRED and result.committed
    with pytest.raises(ContinuedOperationResponseError):
        create_atl_a20_handoff(result.evidence, signer=RESPONSE_SIGNER,
                               trusted_clock=lambda: NOW)


@pytest.mark.parametrize(("status", "outcome"), [
    (SettlementStatus.SETTLED_SUCCESS, ResponseOutcome.INELIGIBLE),
    (SettlementStatus.REJECTED, ResponseOutcome.REJECTED),
])
def test_success_and_rejected_settlements_never_authorize(status, outcome):
    current = source(status)
    result = run(source_value=current, request_value=request(current))
    assert result.outcome is outcome and result.evidence is None and not result.committed


def test_tampered_uncommitted_and_missing_settlement_fail_closed():
    current = source()
    tampered_evidence = replace(current.evidence, operation_id="changed-operation")
    tampered = replace(current, evidence=tampered_evidence)
    assert run(source_value=tampered, request_value=request(current)).reason_code is ResponseReasonCode.SETTLEMENT_EVIDENCE_INVALID
    uncommitted = replace(current, committed=False)
    missing = run(source_value=uncommitted, request_value=request(current))
    assert missing.reason_code is ResponseReasonCode.SETTLEMENT_NOT_FOUND


def test_unregistered_and_digest_mismatched_policy_or_manifest_are_rejected():
    current = source(); current_manifest = manifest(); current_policy = policy(current_manifest)
    unknown_policy_request = request(current, current_policy, current_manifest, policy_version="2")
    assert run(current, current_policy, current_manifest, unknown_policy_request).reason_code is ResponseReasonCode.RESPONSE_POLICY_NOT_FOUND
    bad_policy = request(current, current_policy, current_manifest, policy_digest=h("wrong"))
    assert run(current, current_policy, current_manifest, bad_policy).reason_code is ResponseReasonCode.RESPONSE_POLICY_INVALID
    bad_manifest = request(current, current_policy, current_manifest, response_manifest_digest=h("wrong"))
    assert run(current, current_policy, current_manifest, bad_manifest).reason_code is ResponseReasonCode.RESPONSE_MANIFEST_INVALID


def test_scope_cannot_exceed_original_policy_or_manifest_scope():
    current = source(); current_manifest = manifest(); current_policy = policy(current_manifest)
    widened = request(current, current_policy, current_manifest,
                      requested_scope=("deployment", "other-resource"))
    result = run(current, current_policy, current_manifest, widened)
    assert (result.outcome, result.reason_code) == (
        ResponseOutcome.REJECTED, ResponseReasonCode.SCOPE_NOT_PERMITTED)


def test_exact_retry_replays_and_changed_idempotency_reuse_conflicts():
    current = source(); current_manifest = manifest(); current_policy = policy(current_manifest)
    current_request = request(current, current_policy, current_manifest)
    store = InMemoryResponseAuthorizationRepository()
    first = run(current, current_policy, current_manifest, current_request, store)
    assert run(current, current_policy, current_manifest, current_request, store) == first
    changed = replace(current_request, response_request_id="another-response-request")
    conflict = run(current, current_policy, current_manifest, changed, store)
    assert (conflict.outcome, conflict.reason_code, conflict.committed) == (
        ResponseOutcome.CONFLICT, ResponseReasonCode.RESPONSE_CONFLICT, False)


def test_concurrent_identical_requests_create_one_authority():
    current = source(); current_manifest = manifest(); current_policy = policy(current_manifest)
    current_request = request(current, current_policy, current_manifest)
    store = InMemoryResponseAuthorizationRepository()
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(
            lambda _: run(current, current_policy, current_manifest, current_request, store), range(8)))
    committed = [item for item in results if item.committed]
    assert committed and len({item.evidence.response_authorization_id for item in committed}) == 1
    assert all(item.outcome in {ResponseOutcome.AUTHORIZED, ResponseOutcome.DEFERRED} for item in results)


def test_sqlite_restart_recovery_preserves_original_authorization(tmp_path):
    current = source(); current_manifest = manifest(); current_policy = policy(current_manifest)
    current_request = request(current, current_policy, current_manifest)
    path = tmp_path / "response.sqlite3"
    first = run(current, current_policy, current_manifest, current_request,
                SqliteResponseAuthorizationRepository(path))
    recovered = SqliteResponseAuthorizationRepository(path).recover(response_lifecycle_key(current_request))
    assert recovered.result == first
    assert run(current, current_policy, current_manifest, current_request,
               SqliteResponseAuthorizationRepository(path)) == first


def test_expired_authorization_is_neither_consumable_nor_restored_by_replay():
    store = InMemoryResponseAuthorizationRepository()
    first = run(store=store)
    later = NOW + timedelta(seconds=61)
    replay = run(store=store, now=later)
    assert (replay.outcome, replay.reason_code, replay.evidence) == (
        ResponseOutcome.DEFERRED, ResponseReasonCode.RESPONSE_AUTHORIZATION_EXPIRED, None)
    with pytest.raises(ContinuedOperationResponseError):
        create_atl_a20_handoff(first.evidence, signer=RESPONSE_SIGNER,
                               trusted_clock=lambda: later)


def test_request_translation_is_canonical_and_rejects_authority_injection():
    current_request = request()
    document = response_request_document(current_request)
    encoded = canonical(document)
    assert translate_untrusted_response_request(document) == current_request
    assert translate_untrusted_response_request(encoded) == current_request
    document["command"] = "delete everything"
    with pytest.raises(ContinuedOperationResponseError):
        translate_untrusted_response_request(document)


def test_public_dto_is_allowlisted_and_contains_no_commands_or_secrets():
    current_request = request(); result = run(request_value=current_request)
    public = serialize_public_contract(public_settled_outcome_response(current_request, result))
    assert set(public) == {
        "schema_version", "response_authorization_id", "response_request_id", "settlement_id",
        "incident_id", "outcome", "response_type", "reason_code", "expires_at", "committed",
        "idempotent",
    }
    serialized = json.dumps(public)
    for forbidden in ("signature", "authorization_digest", "manifest_digest", "command",
                      "credential", "secret", "provider_payload", "constraint"):
        assert forbidden not in serialized


def test_complete_a26_to_a30_lineage_is_bound_and_evidence_is_immutable():
    result = run(); evidence = result.evidence
    assert evidence is not None
    assert (evidence.enforcement_evidence_digest, evidence.execution_evidence_digest,
            evidence.verification_evidence_digest, evidence.settlement_digest) == (
        h("a26"), h("a27"), h("a28"), source().evidence.evidence_digest)
    assert verify_response_authorization(evidence, RESPONSE_SIGNER)
    with pytest.raises(FrozenInstanceError):
        evidence.scope = ("wider",)
