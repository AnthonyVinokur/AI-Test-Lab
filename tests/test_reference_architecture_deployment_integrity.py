from dataclasses import replace
from datetime import timedelta

from src.reference_architecture_deployment_integrity import (establish_baseline, evaluate_integrity, normalized_observation, verify_integrity_observation, verify_integrity_result)
from src.reference_architecture_deployment_integrity_contract import AuthorizationIntegrityState, DriftClassification, TrustStatus
from tests.test_reference_architecture_deployment_outcome_verification import NOW, execution_attestation, run


def baseline():
    execution = execution_attestation(); reconciliation = run(execution)
    return establish_baseline(execution, reconciliation.attestation)


def observe(b, **change):
    values=dict(deployment_reference=b.baseline_id, artifact_digest=b.artifact_digest,
        release_id=b.release_id, tenant_id=b.tenant_id, environment=b.environment,
        configuration_digest=b.configuration_digest, authorization_state=AuthorizationIntegrityState.ACTIVE,
        observed_at=NOW)
    return normalized_observation(**(values | change))


def test_unchanged_active_deployment_is_trusted_and_reproducible():
    b=baseline(); o=observe(b); r=evaluate_integrity(b,o,evaluation_time=NOW)
    assert r.status is TrustStatus.TRUSTED and r.drift is DriftClassification.NONE
    assert verify_integrity_observation(o) and verify_integrity_result(r)
    assert not verify_integrity_result(replace(r,reason_category="changed"))


def test_each_trusted_binding_drift_revokes_trust_without_leaking_values():
    b=baseline()
    for field,value in (("artifact_digest","1"*64),("release_id","other"),("tenant_id","other"),("environment","staging"),("configuration_digest","2"*64)):
        r=evaluate_integrity(b,observe(b,**{field:value}),evaluation_time=NOW,prior_status=TrustStatus.TRUSTED)
        assert r.status is TrustStatus.UNTRUSTED and r.revocation and r.reason_category == "binding_drift"
        assert r.remediation[-1].value == "block_future_change"


def test_lifecycle_missing_invalid_and_tampered_evidence_fail_closed():
    b=baseline()
    for state in (AuthorizationIntegrityState.EXPIRED,AuthorizationIntegrityState.REVOKED,AuthorizationIntegrityState.SUPERSEDED):
        assert evaluate_integrity(b,observe(b,authorization_state=state),evaluation_time=NOW).status is TrustStatus.UNTRUSTED
    assert evaluate_integrity(b,observe(b,authorization_state=AuthorizationIntegrityState.UNAVAILABLE),evaluation_time=NOW).status is TrustStatus.INDETERMINATE
    assert evaluate_integrity(b,None,evaluation_time=NOW).status is TrustStatus.INDETERMINATE
    assert evaluate_integrity(b,replace(observe(b),observation_digest="0"*64),evaluation_time=NOW).status is TrustStatus.INVALID
    assert evaluate_integrity(b,observe(b,observed_at=NOW+timedelta(seconds=1)),evaluation_time=NOW).status is TrustStatus.INVALID
