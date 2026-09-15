from dataclasses import replace
from tests.test_reference_architecture_deployment_integrity import baseline, observe
from tests.test_reference_architecture_deployment_outcome_verification import NOW, execution_attestation
from src.reference_architecture_deployment_integrity import evaluate_integrity
from src.reference_architecture_deployment_integrity_contract import TrustStatus
from src.reference_architecture_deployment_integrity_incident import *
from src.reference_architecture_deployment_integrity_incident_contract import *

def inputs(finding=None):
    b=baseline(); f=finding or evaluate_integrity(b,observe(b,artifact_digest="1"*64),evaluation_time=NOW)
    return adapt_verified_integrity_input(baseline=b,finding=f,execution=execution_attestation(),scope="production",correlation_id="correlation",causation_id="cause"), f

def test_verified_finding_creates_immutable_critical_open_incident():
    source,f=inputs(); incident=create_integrity_incident(source,f,SeverityRules("v1"),created_at=NOW)
    assert incident.state is IncidentState.OPEN and incident.severity is IncidentSeverity.CRITICAL
    assert incident.recommendation is ContainmentRecommendation.REQUEST_CONTAINMENT
    assert verify_integrity_incident_attestation(incident) and not verify_integrity_incident_attestation(replace(incident,finding_type="other"))

def test_healthy_monitoring_is_explicit_no_incident_and_unknown_never_healthy():
    b=baseline(); healthy=evaluate_integrity(b,observe(b),evaluation_time=NOW)
    source=adapt_verified_integrity_input(baseline=b,finding=healthy,execution=execution_attestation(),scope="production",correlation_id="correlation",causation_id="cause")
    assert create_integrity_incident(source,healthy,SeverityRules("v1"),created_at=NOW).state is IncidentState.NO_INCIDENT
    unknown=evaluate_integrity(b,None,evaluation_time=NOW)
    source=adapt_verified_integrity_input(baseline=b,finding=unknown,execution=execution_attestation(),scope="production",correlation_id="correlation",causation_id="cause")
    assert create_integrity_incident(source,unknown,SeverityRules("v1"),created_at=NOW).state is IncidentState.INDETERMINATE

def test_cross_deployment_and_tampered_finding_are_rejected():
    b=baseline(); finding=evaluate_integrity(b,observe(b,artifact_digest="1"*64),evaluation_time=NOW)
    try: adapt_verified_integrity_input(baseline=replace(b,tenant_id="other"),finding=finding,execution=execution_attestation(),scope="production",correlation_id="c",causation_id="x")
    except IntegrityIncidentError: pass
    else: assert False
    source,_=inputs();
    try: create_integrity_incident(source,replace(finding,result_digest="0"*64),SeverityRules("v1"),created_at=NOW)
    except IntegrityIncidentError: pass
    else: assert False

def test_duplicate_is_idempotent_and_verified_transition_preserves_history():
    source,f=inputs(); store=InMemoryIntegrityIncidentStore(); rules=SeverityRules("v1")
    first,replay=record_integrity_incident(source,f,rules,created_at=NOW,store=store); second,replay2=record_integrity_incident(source,f,rules,created_at=NOW,store=store)
    assert not replay and replay2 and first == second
    contained=store.append_transition(first.incident_id,IncidentTransitionEvidence(first.incident_id,IncidentState.CONTAINED,"verifier","2"*64,NOW))
    assert contained.state is IncidentState.CONTAINED and first.state is IncidentState.OPEN
