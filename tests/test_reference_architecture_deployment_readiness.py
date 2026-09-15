from dataclasses import replace
from datetime import timedelta

from src.public_contract import serialize_public_contract
from src.reference_architecture_deployment_integrity_contract import TrustStatus
from src.reference_architecture_deployment_readiness import *
from src.reference_architecture_deployment_readiness_contract import *
from src.reference_architecture_deployment_recovery import sign_decision
from src.reference_architecture_deployment_recovery_contract import RecoveryDecisionStatus
from tests.test_reference_architecture_deployment_incident_closure import closure_inputs
from tests.test_reference_architecture_deployment_integrity_incident import inputs
from tests.test_reference_architecture_deployment_recovery import NOW


def trusted_integrity():
    source, finding = inputs()
    from src.reference_architecture_deployment_integrity_contract import DriftClassification, IntegrityResult
    return IntegrityResult("a" * 64, TrustStatus.TRUSTED, DriftClassification.NONE, "bindings_match", (), NOW, "b" * 64, "c" * 64)


def test_ready_when_integrity_is_trusted_and_no_incident_exists():
    result = attest_deployment_readiness(deployment_id="deployment", integrity=trusted_integrity(), attested_at=NOW)
    assert result.status is DeploymentReadinessStatus.READY and result.reason_codes == ()
    assert verify_deployment_readiness_attestation(result)


def test_integrity_failure_and_active_incident_block_promotion():
    incident, *_ = closure_inputs()
    blocked = attest_deployment_readiness(deployment_id=incident.source.deployment_id,
        integrity=replace(trusted_integrity(), status=TrustStatus.UNTRUSTED), incident=replace(incident, state=IncidentState.OPEN), attested_at=NOW)
    assert blocked.status is DeploymentReadinessStatus.BLOCKED
    assert ReadinessReasonCode.INTEGRITY_NOT_VERIFIED in blocked.reason_codes
    assert ReadinessReasonCode.ACTIVE_DEPLOYMENT_INCIDENT in blocked.reason_codes


def test_resolved_incident_requires_exact_authorized_verified_and_closed_recovery():
    incident, execution, verification, root, action, closure_authorization = closure_inputs()
    incomplete = attest_deployment_readiness(deployment_id=incident.source.deployment_id, integrity=trusted_integrity(), incident=incident, attested_at=NOW)
    assert incomplete.status is DeploymentReadinessStatus.BLOCKED
    assert ReadinessReasonCode.RECOVERY_AUTHORIZATION_INVALID in incomplete.reason_codes
    decision = sign_decision(execution.request, RecoveryDecisionStatus.APPROVED, NOW + timedelta(hours=1), "operator")
    from src.reference_architecture_deployment_incident_closure import create_incident_closure
    closure = create_incident_closure(incident=incident, recovery_execution=execution, verification=verification,
      reconciliation_evidence_digest="d" * 64, root_cause=root, preventive_actions=(action,), closure_authorization=closure_authorization,
      closed_by="closer", closed_at=NOW, reason="verified")
    ready = attest_deployment_readiness(deployment_id=incident.source.deployment_id, integrity=trusted_integrity(), incident=incident,
      recovery_decision=decision, recovery_execution=execution, recovery_verification=verification, incident_closure=closure, attested_at=NOW)
    assert ready.status is DeploymentReadinessStatus.READY


def test_unavailable_evidence_requires_review_and_public_projection_is_allowlisted():
    result = attest_deployment_readiness(deployment_id="deployment", integrity=None, attested_at=NOW)
    assert result.status is DeploymentReadinessStatus.REVIEW_REQUIRED
    document = serialize_public_contract(public_deployment_readiness_attestation(result))
    assert document["reason_codes"] == ["integrity_evidence_unavailable"]
    assert "attestation_digest" not in document and "recovery_execution" not in document
