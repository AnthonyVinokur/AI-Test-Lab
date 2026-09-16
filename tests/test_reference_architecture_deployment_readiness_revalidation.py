from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone

import pytest

from src.public_contract import serialize_public_contract
from src.reference_architecture_deployment_incident_closure import create_incident_closure
from src.reference_architecture_deployment_integrity_contract import TrustStatus
from src.reference_architecture_deployment_integrity_incident_contract import IncidentState
from src.reference_architecture_deployment_readiness_contract import (
    DeploymentReadinessError, DeploymentReadinessStatus as Status, ReadinessReasonCode as Reason,
)
from src.reference_architecture_deployment_readiness_revalidation import (
    ApplicabilityReason as Applicability, ReadinessEvidence,
    attest_bound_deployment_readiness, public_deployment_readiness_revalidation,
    revalidate_deployment_readiness,
)
from src.reference_architecture_deployment_recovery import sign_decision
from src.reference_architecture_deployment_recovery_contract import RecoveryDecisionStatus
from tests.test_reference_architecture_deployment_incident_closure import closure_inputs
from tests.test_reference_architecture_deployment_readiness import trusted_integrity
from tests.test_reference_architecture_deployment_recovery import NOW

VALIDITY = timedelta(hours=1)


def evidence():
    return ReadinessEvidence("deployment", "revision-1", trusted_integrity(), None)


def bound(current=None):
    return attest_bound_deployment_readiness(
        evidence=current or evidence(), evaluation_time=NOW, validity=VALIDITY,
    )


def revalidate(old, current=None, now=NOW, **overrides):
    arguments = dict(previous=old.attestation, binding=old, evidence=current or old.evidence,
                     evaluation_time=now, validity=VALIDITY)
    arguments.update(overrides)
    return revalidate_deployment_readiness(**arguments)


@pytest.mark.parametrize("offset,applicable", [(0, True), (3599, True), (3600, False), (3601, False)])
def test_freshness_is_half_open_and_expired_evidence_can_be_re_evaluated(offset, applicable):
    old = bound()
    result = revalidate(old, now=NOW + timedelta(seconds=offset))
    assert result.previous_applicable is applicable
    assert result.attestation.status is Status.READY
    assert result.attestation.attested_at == NOW + timedelta(seconds=offset)
    assert result.binding.expires_at == result.attestation.attested_at + VALIDITY
    assert old.attestation.attested_at == NOW and old.expires_at == NOW + VALIDITY
    if not applicable:
        assert Applicability.EXPIRED in result.previous_applicability_reasons


@pytest.mark.parametrize("changes", [
    {"revision": "revision-2"},
    {"integrity": replace(trusted_integrity(), result_digest="d" * 64)},
    {"integrity": replace(trusted_integrity(), observation_digest="e" * 64)},
    {"integrity": replace(trusted_integrity(), baseline_id="f" * 64)},
])
def test_changed_evidence_is_detected_and_fresh_ready_is_bound_to_current(changes):
    old = bound()
    current = replace(old.evidence, **changes)
    result = revalidate(old, current)
    assert result.previous_applicability_reasons == (Applicability.EVIDENCE_CHANGED,)
    assert result.attestation.status is Status.READY
    assert result.binding.evidence == current
    assert old.evidence == evidence()


@pytest.mark.parametrize("trust", [TrustStatus.UNTRUSTED, TrustStatus.INVALID])
def test_old_ready_cannot_hide_failed_integrity_even_if_revision_is_reused(trust):
    old = bound()
    result = revalidate(old, replace(old.evidence, integrity=replace(trusted_integrity(), status=trust)))
    assert result.attestation.status is Status.BLOCKED
    assert Reason.INTEGRITY_NOT_VERIFIED in result.attestation.reason_codes


@pytest.mark.parametrize("state", [IncidentState.OPEN, IncidentState.CONTAINED])
def test_new_active_incident_blocks_even_with_missing_integrity(state):
    incident, *_ = closure_inputs()
    old = bound(replace(evidence(), deployment_id=incident.source.deployment_id))
    result = revalidate(old, replace(old.evidence, integrity=None, incident=replace(incident, state=state)))
    assert result.attestation.status is Status.BLOCKED
    assert Reason.ACTIVE_DEPLOYMENT_INCIDENT in result.attestation.reason_codes
    assert Reason.INTEGRITY_EVIDENCE_UNAVAILABLE in result.attestation.reason_codes


@pytest.mark.parametrize("changes,reason", [
    ({"integrity": None}, Reason.INTEGRITY_EVIDENCE_UNAVAILABLE),
    ({"integrity": replace(trusted_integrity(), status=TrustStatus.INDETERMINATE)}, Reason.INTEGRITY_EVIDENCE_UNAVAILABLE),
    ({"integrity": replace(trusted_integrity(), status=TrustStatus.DEGRADED)}, Reason.INTEGRITY_EVIDENCE_UNAVAILABLE),
    ({"incident_evidence_available": False}, Reason.INCIDENT_EVIDENCE_UNAVAILABLE),
    ({"integrity": replace(trusted_integrity(), evaluated_at=NOW + timedelta(seconds=1))}, Reason.INTEGRITY_EVIDENCE_UNAVAILABLE),
])
def test_missing_indeterminate_or_future_current_evidence_never_retains_ready(changes, reason):
    old = bound()
    result = revalidate(old, replace(old.evidence, **changes))
    assert result.attestation.status is Status.REVIEW_REQUIRED
    assert reason in result.attestation.reason_codes


def test_unknown_incident_evidence_preserves_known_integrity_block():
    old = bound()
    current = replace(old.evidence, incident_evidence_available=False,
                      integrity=replace(trusted_integrity(), status=TrustStatus.UNTRUSTED))
    assert revalidate(old, current).attestation.status is Status.BLOCKED


def test_expired_recovery_authorization_cannot_be_overridden_by_previous_ready():
    incident, execution, verification, root, action, authorization = closure_inputs()
    evaluated_at = incident.source.observed_at
    decision = sign_decision(execution.request, RecoveryDecisionStatus.APPROVED,
                             evaluated_at + VALIDITY, "operator")
    closure = create_incident_closure(
        incident=incident, recovery_execution=execution, verification=verification,
        reconciliation_evidence_digest="d" * 64, root_cause=root, preventive_actions=(action,),
        closure_authorization=authorization, closed_by="closer", closed_at=NOW, reason="verified",
    )
    current = ReadinessEvidence(incident.source.deployment_id, "revision-1", trusted_integrity(),
                               incident, recovery_decision=decision, recovery_execution=execution,
                               recovery_verification=verification, incident_closure=closure)
    old = attest_bound_deployment_readiness(evidence=current, evaluation_time=evaluated_at, validity=VALIDITY)
    assert old.attestation.status is Status.READY
    result = revalidate(old, now=evaluated_at + VALIDITY)
    assert result.attestation.status is Status.BLOCKED
    assert Reason.RECOVERY_AUTHORIZATION_INVALID in result.attestation.reason_codes


def test_deployment_mismatch_rejects_use_of_previous_or_binding():
    old = bound()
    with pytest.raises(DeploymentReadinessError, match="deployment does not match"):
        revalidate(old, replace(old.evidence, deployment_id="other"))
    with pytest.raises(DeploymentReadinessError, match="deployment does not match"):
        revalidate(old, binding=replace(old, evidence=replace(old.evidence, deployment_id="other")))


def test_missing_binding_requires_fresh_evaluation_without_backfilling_old_record():
    old = bound()
    result = revalidate(old, binding=None)
    assert result.previous_applicability_reasons == (Applicability.MISSING_BINDING,)
    assert result.attestation.status is Status.READY
    assert revalidate(old, replace(old.evidence, integrity=None), binding=None).attestation.status is Status.REVIEW_REQUIRED


def test_binding_mismatch_and_invalid_attestation_are_not_reused():
    old = bound()
    damaged = replace(old.attestation, attestation_digest="0" * 64)
    result = revalidate(old, previous=damaged)
    assert Applicability.INVALID_ATTESTATION in result.previous_applicability_reasons
    assert Applicability.BINDING_MISMATCH in result.previous_applicability_reasons
    assert result.attestation.status is Status.READY


def test_future_issuance_is_not_fresh():
    future = attest_bound_deployment_readiness(evidence=evidence(), evaluation_time=NOW + VALIDITY,
                                              validity=VALIDITY)
    result = revalidate(future)
    assert result.previous_applicability_reasons == (Applicability.FUTURE_ISSUANCE,)
    assert result.attestation.attested_at == NOW


@pytest.mark.parametrize("expiry", [NOW, NOW - VALIDITY, NOW.replace(tzinfo=None)])
def test_invalid_bound_timestamps_require_fresh_evaluation(expiry):
    old = bound()
    result = revalidate(old, binding=replace(old, expires_at=expiry))
    assert Applicability.INVALID_TIMESTAMP in result.previous_applicability_reasons
    assert result.attestation.status is Status.READY


@pytest.mark.parametrize("validity", [timedelta(0), -VALIDITY, 3600, None, timedelta(microseconds=1), timedelta.max])
def test_invalid_duration_is_normalized(validity):
    with pytest.raises(DeploymentReadinessError):
        revalidate(bound(), validity=validity)


@pytest.mark.parametrize("now", [NOW.replace(tzinfo=None), NOW.replace(microsecond=1), None])
def test_invalid_evaluation_time_is_normalized(now):
    with pytest.raises(DeploymentReadinessError):
        revalidate(bound(), now=now)


def test_offset_normalization_determinism_public_allowlist_and_immutability():
    old = bound()
    first = revalidate(old)
    second = revalidate(old, now=NOW.astimezone(timezone(timedelta(hours=5))))
    assert first == second
    assert first.attestation is not old.attestation
    public = serialize_public_contract(public_deployment_readiness_revalidation(first))
    assert set(public) == {"schema_version", "deployment_id", "status", "reason_codes", "attested_at"}
    assert public["status"] == "ready" and public["schema_version"] == "1.0"
    with pytest.raises(FrozenInstanceError):
        old.expires_at = NOW


@pytest.mark.parametrize("status", [TrustStatus.UNTRUSTED, TrustStatus.INDETERMINATE])
def test_previous_nonready_never_substitutes_for_current_evaluation(status):
    old = bound(replace(evidence(), integrity=replace(trusted_integrity(), status=status)))
    assert revalidate(old, evidence()).attestation.status is Status.READY


@pytest.mark.parametrize("decision_status", [RecoveryDecisionStatus.REJECTED, RecoveryDecisionStatus.EXPIRED])
def test_recovery_rejection_is_normalized_by_existing_readiness_engine(decision_status):
    from src.reference_architecture_deployment_readiness import attest_deployment_readiness
    incident, execution, *_ = closure_inputs()
    decision = sign_decision(execution.request, decision_status, NOW + VALIDITY, "operator")
    result = attest_deployment_readiness(
        deployment_id=incident.source.deployment_id, integrity=trusted_integrity(),
        incident=incident, recovery_execution=execution, recovery_decision=decision, attested_at=NOW,
    )
    assert result.status is Status.BLOCKED
    assert Reason.RECOVERY_AUTHORIZATION_INVALID in result.reason_codes


def test_naive_historical_timestamp_cannot_establish_applicability():
    old = bound()
    # Simulate a damaged persisted object bypassing constructor validation.
    object.__setattr__(old.attestation, "attested_at", NOW.replace(tzinfo=None))
    result = revalidate(old)
    assert Applicability.INVALID_TIMESTAMP in result.previous_applicability_reasons
    assert result.attestation.status is Status.READY
