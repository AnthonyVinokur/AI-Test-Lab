import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError, replace
from datetime import timedelta

import pytest

from src.public_contract import serialize_public_contract
from src.reference_architecture_continued_operation_enforcement import (
    ConsumptionOutcomeUnknownError,
    ConsumptionPersistenceError,
    InMemoryContinuedOperationAuthorizationRepository,
    InMemoryContinuedOperationConsumptionLedger,
    SqliteContinuedOperationConsumptionLedger,
    continued_operation_authorization_digest,
    enforce_continued_operation,
    enforcement_binding_digest,
    enforcement_request_document,
    public_continued_operation_enforcement,
    translate_untrusted_enforcement_request,
)
from src.reference_architecture_continued_operation_enforcement_contract import (
    ContinuedOperationEnforcementBinding,
    ContinuedOperationEnforcementError,
    ContinuedOperationEnforcementPolicy,
    ContinuedOperationEnforcementReasonCode as Reason,
    ContinuedOperationEnforcementRequest,
    ContinuedOperationEnforcementState as State,
    StoredContinuedOperationAuthorization,
)
from src.reference_architecture_deployment_continued_operation_authorization_contract import (
    ContinuedOperationLifecycleState as Lifecycle,
)
from tests.test_reference_architecture_deployment_continued_operation_authorization import (
    authorization_key_contract,
    authorized_artifact,
)
from tests.test_reference_architecture_deployment_recovery import NOW


def stored(*, lifecycle=Lifecycle.ACTIVE, upstream_active=True):
    artifact = authorized_artifact()
    return StoredContinuedOperationAuthorization(
        "authorization-reference-1", artifact,
        continued_operation_authorization_digest(artifact),
        authorization_key_contract(), lifecycle, upstream_active,
    )


def request(value=None, **overrides):
    value = value or stored()
    arguments = dict(
        authorization_reference=value.reference,
        authorization_digest=value.artifact_digest,
        enforcement_request_id="enforcement-request-1",
        deployment_id="deployment",
        consumer_id="production-gateway",
        enforcement_point_id="trusted-enforcement-gateway",
        purpose="serve-production-traffic",
        requested_at=NOW,
        operation_reference="continue-serving-production",
        policy_reference="continued-operation-enforcement-policy-1",
        correlation_id="correlation-1",
    )
    arguments.update(overrides)
    return ContinuedOperationEnforcementRequest(**arguments)


def policy(*, lifecycle=Lifecycle.ACTIVE, bindings=None, expires_at=NOW + timedelta(hours=1)):
    return ContinuedOperationEnforcementPolicy(
        "continued-operation-enforcement-policy-1",
        "continued-operation-policy", "1", NOW - timedelta(hours=1),
        expires_at, lifecycle,
        bindings or (ContinuedOperationEnforcementBinding(
            "deployment", "production-gateway", "trusted-enforcement-gateway",
            "serve-production-traffic", "continue-serving-production",
        ),),
    )


def context(value=None, ledger=None):
    value = value or stored()
    return value, InMemoryContinuedOperationAuthorizationRepository((value,)), (
        ledger or InMemoryContinuedOperationConsumptionLedger()
    )


def enforce(req=None, *, value=None, repository=None, ledger=None, enforcement_policy=None,
            now=NOW):
    value = value or stored()
    repository = repository or InMemoryContinuedOperationAuthorizationRepository((value,))
    ledger = ledger or InMemoryContinuedOperationConsumptionLedger()
    return enforce_continued_operation(
        req or request(value), authorization_repository=repository,
        consumption_ledger=ledger, policy=enforcement_policy or policy(),
        trusted_clock=lambda: now,
    )


def canonical_wire(document):
    return json.dumps(document, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode()


def test_valid_exactly_bound_authorization_is_atomically_consumed_and_permitted():
    value, repository, ledger = context()
    result = enforce(request(value), value=value, repository=repository, ledger=ledger)
    assert result.permitted and result.enforcement_state is State.PERMITTED
    assert result.reason_codes == (Reason.AUTHORIZATION_CONSUMED,)
    assert result.consumption_record == ledger.get(value.artifact.authorization_id)
    assert result.consumption_record.evidence_digest == result.evidence.evidence_digest
    assert result.evidence.request_binding_digest == enforcement_binding_digest(request(value))


def test_contracts_are_frozen_strict_versioned_and_canonical():
    req = request()
    document = enforcement_request_document(req)
    assert translate_untrusted_enforcement_request(document) == req
    assert translate_untrusted_enforcement_request(canonical_wire(document)) == req
    with pytest.raises(FrozenInstanceError):
        req.purpose = "changed"
    with pytest.raises(ContinuedOperationEnforcementError):
        translate_untrusted_enforcement_request({**document, "unknown": "field"})
    with pytest.raises(ContinuedOperationEnforcementError):
        translate_untrusted_enforcement_request(json.dumps(document).encode())
    with pytest.raises(ContinuedOperationEnforcementError, match="unsupported"):
        replace(req, schema_version="2.0")


@pytest.mark.parametrize("field,value,reason", [
    ("deployment_id", "other-deployment", Reason.DEPLOYMENT_MISMATCH),
    ("consumer_id", "other-consumer", Reason.CONSUMER_MISMATCH),
    ("purpose", "diagnostics", Reason.PURPOSE_MISMATCH),
    ("policy_reference", "other-policy", Reason.POLICY_MISMATCH),
])
def test_signed_authorization_binding_mismatches_fail_closed(field, value, reason):
    stored_value = stored()
    result = enforce(request(stored_value, **{field: value}), value=stored_value)
    assert not result.permitted and result.enforcement_state is State.BLOCKED
    assert result.reason_codes == (reason,)


@pytest.mark.parametrize("field,value,reason", [
    ("enforcement_point_id", "other-gateway", Reason.ENFORCEMENT_POINT_MISMATCH),
    ("operation_reference", "restart-deployment", Reason.OPERATION_MISMATCH),
])
def test_a26_policy_supplies_exact_point_and_operation_binding(field, value, reason):
    stored_value = stored()
    result = enforce(request(stored_value, **{field: value}), value=stored_value)
    assert result.enforcement_state is State.BLOCKED
    assert result.reason_codes == (reason,)


def test_digest_substitution_and_missing_authorization_are_blocked():
    value = stored()
    mismatch = enforce(request(value, authorization_digest="0" * 64), value=value)
    missing = enforce(
        request(value, authorization_reference="missing-reference"), value=value,
        repository=InMemoryContinuedOperationAuthorizationRepository(),
    )
    assert mismatch.reason_codes == (Reason.AUTHORIZATION_DIGEST_MISMATCH,)
    assert missing.reason_codes == (Reason.AUTHORIZATION_NOT_FOUND,)


@pytest.mark.parametrize("lifecycle,upstream,reason", [
    (Lifecycle.REVOKED, True, Reason.AUTHORIZATION_REVOKED),
    (Lifecycle.SUPERSEDED, True, Reason.AUTHORIZATION_SUPERSEDED),
    (Lifecycle.ACTIVE, False, Reason.UPSTREAM_STATE_INACTIVE),
])
def test_inactive_lifecycle_states_block(lifecycle, upstream, reason):
    value = stored(lifecycle=lifecycle, upstream_active=upstream)
    assert enforce(request(value), value=value).reason_codes == (reason,)


def test_expired_and_not_yet_valid_authorizations_block():
    value = stored()
    expired = enforce(request(value), value=value, now=value.artifact.expires_at)
    early = enforce(
        request(value, requested_at=value.artifact.not_before - timedelta(seconds=2)),
        value=value, now=value.artifact.not_before - timedelta(seconds=1),
    )
    assert expired.reason_codes == (Reason.AUTHORIZATION_EXPIRED,)
    assert early.reason_codes == (Reason.AUTHORIZATION_NOT_YET_VALID,)


def test_exact_retry_is_idempotent_and_changed_retry_is_conflict():
    value, repository, ledger = context()
    req = request(value)
    first = enforce(req, value=value, repository=repository, ledger=ledger)
    retry = enforce(req, value=value, repository=repository, ledger=ledger)
    changed = enforce(
        replace(req, operation_reference="changed-operation"), value=value,
        repository=repository, ledger=ledger,
        enforcement_policy=policy(bindings=(ContinuedOperationEnforcementBinding(
            "deployment", "production-gateway", "trusted-enforcement-gateway",
            "serve-production-traffic", "changed-operation",
        ),)),
    )
    assert first.permitted and retry.permitted and retry.idempotent
    assert retry.reason_codes == (Reason.IDEMPOTENT_RESULT_RETURNED,)
    assert retry.consumption_record is first.consumption_record
    assert changed.reason_codes == (Reason.REQUEST_ID_CONFLICT,)


def test_consumed_authorization_cannot_be_reused_by_different_request():
    value, repository, ledger = context()
    first = enforce(request(value), value=value, repository=repository, ledger=ledger)
    replay = enforce(
        request(value, enforcement_request_id="enforcement-request-2",
                correlation_id="correlation-2"),
        value=value, repository=repository, ledger=ledger,
    )
    assert first.permitted and not replay.permitted
    assert replay.reason_codes == (Reason.AUTHORIZATION_ALREADY_CONSUMED,)
    assert replay.evidence.previous_consumption_reference == first.consumption_record.evidence_digest


def test_concurrent_distinct_requests_have_exactly_one_winner():
    value, repository, ledger = context()
    requests = tuple(
        request(value, enforcement_request_id=f"enforcement-request-{index}",
                correlation_id=f"correlation-{index}")
        for index in range(12)
    )
    with ThreadPoolExecutor(max_workers=12) as pool:
        results = tuple(pool.map(
            lambda item: enforce(item, value=value, repository=repository, ledger=ledger),
            requests,
        ))
    assert sum(result.permitted for result in results) == 1
    assert {result.reason_codes[0] for result in results} <= {
        Reason.AUTHORIZATION_CONSUMED, Reason.AUTHORIZATION_ALREADY_CONSUMED,
    }


def test_lifecycle_is_rechecked_inside_atomic_boundary():
    value, repository, ledger = context()

    class RevokingLedger:
        def consume(self, **kwargs):
            repository.set_lifecycle(value.reference, Lifecycle.REVOKED, upstream_active=True)
            return ledger.consume(**kwargs)

    result = enforce(request(value), value=value, repository=repository, ledger=RevokingLedger())
    assert result.reason_codes == (Reason.AUTHORIZATION_REVOKED,)
    assert ledger.get(value.artifact.authorization_id) is None


@pytest.mark.parametrize("error,reason", [
    (ConsumptionPersistenceError("rolled back"), Reason.CONSUMPTION_PERSISTENCE_FAILED),
    (ConsumptionOutcomeUnknownError("unknown"), Reason.CONSUMPTION_STATE_UNAVAILABLE),
])
def test_storage_failure_and_unknown_commit_outcome_never_permit(error, reason):
    class FailingLedger:
        def consume(self, **kwargs):
            raise error

    result = enforce(ledger=FailingLedger())
    assert result.enforcement_state is State.INDETERMINATE and not result.permitted
    assert result.reason_codes == (reason,)


def test_sqlite_ledger_is_durable_and_enforces_storage_uniqueness(tmp_path):
    value = stored()
    repository = InMemoryContinuedOperationAuthorizationRepository((value,))
    path = tmp_path / "consumption.sqlite3"
    first = enforce(request(value), value=value, repository=repository,
                    ledger=SqliteContinuedOperationConsumptionLedger(path))
    retry = enforce(request(value), value=value, repository=repository,
                    ledger=SqliteContinuedOperationConsumptionLedger(path))
    conflict = enforce(
        request(value, enforcement_request_id="another-request"), value=value,
        repository=repository, ledger=SqliteContinuedOperationConsumptionLedger(path),
    )
    assert first.permitted and retry.idempotent
    assert conflict.reason_codes == (Reason.AUTHORIZATION_ALREADY_CONSUMED,)
    assert SqliteContinuedOperationConsumptionLedger(path).get(
        value.artifact.authorization_id
    ) == first.consumption_record


def test_public_projection_is_stable_allowlisted_and_sanitized():
    result = enforce()
    public = serialize_public_contract(public_continued_operation_enforcement(result))
    assert set(public) == {
        "schema_version", "authorization_id", "enforcement_request_id", "deployment_id",
        "purpose", "enforcement_state", "reason_codes", "decided_at", "consumed_at",
        "evidence_reference", "correlation_id",
    }
    encoded = json.dumps(public)
    for protected in (
        "signature_base64", "authorization_key_id", "readiness_binding_fingerprint",
        "request_binding_digest", "internal_enforcement_error",
    ):
        assert protected not in encoded


def test_evidence_is_deterministic_traceable_and_mutation_sensitive():
    first = enforce()
    second = enforce()
    changed = enforce(request(correlation_id="other-correlation"))
    assert first.evidence == second.evidence
    assert first.evidence.evidence_digest != changed.evidence.evidence_digest
    assert first.evidence.correlation_id == "correlation-1"


def test_untrusted_clock_and_inactive_enforcement_policy_fail_closed():
    value = stored()
    bad_clock = enforce_continued_operation(
        request(value),
        authorization_repository=InMemoryContinuedOperationAuthorizationRepository((value,)),
        consumption_ledger=InMemoryContinuedOperationConsumptionLedger(), policy=policy(),
        trusted_clock=lambda: (_ for _ in ()).throw(RuntimeError("clock unavailable")),
    )
    inactive = enforce(request(value), value=value,
                       enforcement_policy=policy(lifecycle=Lifecycle.REVOKED))
    assert bad_clock.enforcement_state is State.INDETERMINATE
    assert bad_clock.reason_codes == (Reason.UNTRUSTED_TIME_SOURCE,)
    assert inactive.reason_codes == (Reason.POLICY_MISMATCH,)
