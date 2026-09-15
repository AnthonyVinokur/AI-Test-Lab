from dataclasses import replace

import pytest

from src.public_contract import serialize_public_contract
from src.reference_architecture_deployment_incident_closure import *
from src.reference_architecture_deployment_incident_closure_contract import *
from src.reference_architecture_deployment_integrity_incident import InMemoryIntegrityIncidentStore
from src.reference_architecture_deployment_integrity_incident_contract import IncidentState, IncidentTransitionEvidence
from src.reference_architecture_deployment_recovery import verify_post_remediation
from src.reference_architecture_deployment_recovery_contract import RecoveryExecutionAttestation, RecoveryExecutionStatus
from tests.test_reference_architecture_deployment_integrity_incident import inputs
from tests.test_reference_architecture_deployment_recovery import NOW, request


def resolved_incident():
    source, finding = inputs(); store = InMemoryIntegrityIncidentStore()
    from src.reference_architecture_deployment_integrity_incident import SeverityRules, record_integrity_incident
    incident, _ = record_integrity_incident(source, finding, SeverityRules("v1"), created_at=NOW, store=store)
    return store.append_transition(incident.incident_id, IncidentTransitionEvidence(incident.incident_id, IncidentState.RESOLVED, "verifier", "b" * 64, NOW))


def closure_inputs():
    incident = resolved_incident()
    execution = RecoveryExecutionAttestation(request().__class__(incident.incident_id, incident.source.deployment_id, incident.source.artifact_digest,
        incident.source.tenant_id, incident.source.environment, "rollback", "3" * 64, NOW), RecoveryExecutionStatus.EXECUTED, "7" * 64, "8" * 64, NOW)
    verification = verify_post_remediation(execution, integrity_verified=True, outcome_verified=True,
        integrity_evidence_digest="9" * 64, outcome_evidence_digest="a" * 64, verified_at=NOW)
    root = RootCauseClassification(RootCauseCategory.CONFIGURATION, (ImpactCategory.AVAILABILITY,), "9" * 64, "investigator", NOW)
    action = create_preventive_action(incident_id=incident.incident_id, action_type="policy_update", owner_id="owner",
        due_condition="before_next_release", priority=PreventiveActionPriority.HIGH, evidence_digest="c" * 64, created_at=NOW)
    authorization = authorize_closure(incident_id=incident.incident_id, closer_id="closer", authority_id="authority",
        expires_at=NOW.replace(year=2027), evidence_digest="f" * 64)
    return incident, execution, verification, root, action, authorization


def test_closure_is_eligible_only_after_resolved_reconciled_verified_recovery():
    incident, execution, verification, root, action, authorization = closure_inputs()
    assert closure_eligible(incident=incident, recovery_execution=execution, verification=verification, reconciliation_evidence_digest="d" * 64)
    closure = create_incident_closure(incident=incident, recovery_execution=execution, verification=verification,
        reconciliation_evidence_digest="d" * 64, root_cause=root, preventive_actions=(action,), closure_authorization=authorization, closed_by="closer", closed_at=NOW, reason="verified")
    assert verify_incident_closure_record(closure)
    assert not closure_eligible(incident=replace(incident, state=IncidentState.OPEN), recovery_execution=execution, verification=verification, reconciliation_evidence_digest="d" * 64)
    with pytest.raises(IncidentClosureError):
        create_incident_closure(incident=incident, recovery_execution=execution, verification=verification,
          reconciliation_evidence_digest="d" * 64, root_cause=root, preventive_actions=(), closure_authorization=authorization, closed_by="closer", closed_at=NOW, reason="verified")


def test_records_are_tamper_resistant_and_actions_have_immutable_dispositions():
    incident, execution, verification, root, action, _ = closure_inputs()
    assert verify_preventive_action_record(action) and not verify_preventive_action_record(replace(action, owner_id="other"))
    disposition = create_preventive_action_disposition(action, status=PreventiveActionStatus.DEFERRED, decided_by="owner",
        justification="scheduled_window", evidence_digest="e" * 64, decided_at=NOW)
    store = InMemoryIncidentClosureStore(); store.preserve_action(action); store.append_disposition(disposition)
    assert store.disposition_history(action.action_id) == (disposition,)
    with pytest.raises(IncidentClosureError): store.append_disposition(replace(disposition, justification="changed"))
    with pytest.raises(IncidentClosureError):
        create_preventive_action_disposition(replace(action, owner_id="other"), status=PreventiveActionStatus.ACCEPTED,
          decided_by="owner", justification="accepted", evidence_digest="e" * 64, decided_at=NOW)


def test_public_attestation_is_allowlisted_and_never_exposes_classification_or_reason():
    incident, execution, verification, root, action, authorization = closure_inputs()
    closure = create_incident_closure(incident=incident, recovery_execution=execution, verification=verification,
        reconciliation_evidence_digest="d" * 64, root_cause=root, preventive_actions=(action,), closure_authorization=authorization, closed_by="closer", closed_at=NOW, reason="verified")
    document = serialize_public_contract(public_incident_closure_attestation(closure))
    assert document["closed"] is True and "reason" not in document and "root_cause" not in document and "preventive_action_ids" not in document


def test_cross_incident_recovery_and_incomplete_evidence_fail_closed():
    incident, execution, verification, root, action, authorization = closure_inputs()
    with pytest.raises(IncidentClosureError):
        create_incident_closure(incident=incident, recovery_execution=replace(execution, request=replace(execution.request, incident_id="f" * 64)), verification=verification,
          reconciliation_evidence_digest="d" * 64, root_cause=root, preventive_actions=(action,), closure_authorization=authorization, closed_by="closer", closed_at=NOW, reason="verified")
    with pytest.raises(IncidentClosureError):
        create_incident_closure(incident=incident, recovery_execution=execution, verification=verification,
          reconciliation_evidence_digest="not-a-digest", root_cause=root, preventive_actions=(action,), closure_authorization=authorization, closed_by="closer", closed_at=NOW, reason="verified")
    with pytest.raises(IncidentClosureError):
        create_incident_closure(incident=incident, recovery_execution=execution, verification=verification,
          reconciliation_evidence_digest="d" * 64, root_cause=root, preventive_actions=(action,), closure_authorization=replace(authorization, closer_id="other"), closed_by="closer", closed_at=NOW, reason="verified")
