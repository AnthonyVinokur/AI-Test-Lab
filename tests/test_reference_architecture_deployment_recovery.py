from dataclasses import replace
from datetime import datetime, timezone, timedelta
from src.reference_architecture_deployment_recovery_contract import *
from src.reference_architecture_deployment_recovery import *
NOW=datetime(2026,1,1,tzinfo=timezone.utc)

def request(): return RemediationRequest("1"*64,"deployment","2"*64,"tenant","production","rollback","3"*64,NOW)

def test_approved_decision_authorizes_only_exact_request():
    item=request(); decision=sign_decision(item,RecoveryDecisionStatus.APPROVED,NOW+timedelta(hours=1),"operator")
    assert authorize_recovery(item,decision,NOW)
    for changed in (replace(item,incident_id="4"*64),replace(item,tenant_id="other"),replace(item,environment="stage"),replace(item,artifact_digest="5"*64),replace(item,action_fingerprint="6"*64)):
        try: authorize_recovery(changed,decision,NOW); assert False
        except RecoveryError: pass

def test_expired_or_tampered_decision_blocks_recovery():
    item=request(); expired=sign_decision(item,RecoveryDecisionStatus.APPROVED,NOW+timedelta(seconds=1),"operator")
    try: authorize_recovery(item,expired,NOW+timedelta(seconds=1)); assert False
    except RecoveryError: pass
    decision=sign_decision(item,RecoveryDecisionStatus.APPROVED,NOW+timedelta(hours=1),"operator")
    try: authorize_recovery(item,replace(decision,signature="0"*64),NOW); assert False
    except RecoveryError: pass

def test_execution_does_not_resolve_and_verification_is_fail_closed():
    execution=RecoveryExecutionAttestation(request(),RecoveryExecutionStatus.EXECUTED,"7"*64,"8"*64,NOW)
    passed=verify_post_remediation(execution,integrity_verified=True,outcome_verified=True,integrity_evidence_digest="9"*64,outcome_evidence_digest="a"*64,verified_at=NOW)
    unavailable=verify_post_remediation(execution,integrity_verified=None,outcome_verified=True,integrity_evidence_digest="9"*64,outcome_evidence_digest="a"*64,verified_at=NOW)
    assert passed.status is RecoveryVerificationStatus.PASSED
    assert unavailable.status is RecoveryVerificationStatus.UNAVAILABLE
    assert resolution_eligible(execution,passed.status)
    assert not resolution_eligible(execution,unavailable.status)
    assert public_evidence(execution,unavailable.status).eligible_for_resolution is False
