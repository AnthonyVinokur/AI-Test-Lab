from __future__ import annotations

import json
from dataclasses import asdict, replace
from datetime import datetime
from hashlib import sha256
from threading import Lock
from typing import Any

from src.reference_architecture_deployment_execution import verify_execution_attestation
from src.reference_architecture_deployment_execution_contract import DeploymentExecutionAttestation
from src.reference_architecture_deployment_integrity import verify_integrity_result
from src.reference_architecture_deployment_integrity_contract import IntegrityResult, TrustStatus, TrustedDeploymentBaseline
from src.reference_architecture_deployment_integrity_incident_contract import *

def _canonical(value: Any) -> bytes: return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
def _time(value: datetime) -> str: return value.strftime("%Y-%m-%dT%H:%M:%SZ")
def _hash(value: Any) -> str: return sha256(_canonical(value)).hexdigest()

def _source_doc(source: VerifiedIncidentInput) -> dict[str, Any]:
    data = asdict(source); data["observed_at"] = _time(source.observed_at); return data

def _incident_doc(incident: IntegrityIncidentAttestation) -> dict[str, Any]:
    return {"incident_key": incident.incident_key, "state": incident.state.value, "severity": incident.severity.value if incident.severity else None,
      "finding_type": incident.finding_type, "recommendation": incident.recommendation.value, "source": _source_doc(incident.source),
      "severity_rules_version": incident.severity_rules_version, "evidence_digest": incident.evidence_digest,
      "created_at": _time(incident.created_at), "schema_version": incident.schema_version}

def verify_integrity_incident_attestation(incident: IntegrityIncidentAttestation) -> bool:
    digest = _hash(_incident_doc(incident))
    return digest == incident.attestation_digest and _hash({**_incident_doc(incident), "attestation_digest": digest}) == incident.incident_id

def adapt_verified_integrity_input(*, baseline: TrustedDeploymentBaseline, finding: IntegrityResult,
                                  execution: DeploymentExecutionAttestation, scope: str,
                                  correlation_id: str, causation_id: str) -> VerifiedIncidentInput:
    """Narrow adapter: rejects cross-deployment evidence before incident creation."""
    try:
        if not (verify_integrity_result(finding) and verify_execution_attestation(execution)):
            raise IntegrityIncidentError("trusted input evidence is invalid.")
        if finding.baseline_id != baseline.baseline_id or execution.attestation_id != baseline.execution_attestation_id:
            raise IntegrityIncidentError("trusted input binding is invalid.")
        if (execution.authorization_id, execution.artifact_digest, execution.tenant_id, execution.environment,
            execution.release_id, execution.configuration_digest) != (baseline.authorization_id, baseline.artifact_digest,
            baseline.tenant_id, baseline.environment, baseline.release_id, baseline.configuration_digest):
            raise IntegrityIncidentError("trusted input binding is invalid.")
        if execution.configuration_digest is None: raise IntegrityIncidentError("trusted input binding is unavailable.")
        return VerifiedIncidentInput(deployment_id=baseline.baseline_id, release_id=baseline.release_id,
          artifact_digest=baseline.artifact_digest, configuration_digest=baseline.configuration_digest, tenant_id=baseline.tenant_id,
          environment=baseline.environment, scope=scope, operation=execution.operation, authorization_id=baseline.authorization_id,
          admission_receipt_id=execution.admission_receipt_id, execution_attestation_id=execution.attestation_id,
          reconciliation_id=baseline.reconciliation_id, baseline_id=baseline.baseline_id, finding_id=finding.result_digest,
          finding_evidence_digest=finding.observation_digest or finding.result_digest, correlation_id=correlation_id,
          causation_id=causation_id, observed_at=finding.evaluated_at)
    except IntegrityIncidentError: raise
    except Exception as error: raise IntegrityIncidentError("trusted input is unverifiable.") from error

def classify_severity(finding: IntegrityResult, rules: SeverityRules) -> IncidentSeverity | None:
    if finding.status is TrustStatus.TRUSTED: return None
    if finding.reason_category in {"binding_drift", "evidence_invalid"}: return IncidentSeverity.CRITICAL
    if finding.reason_category in {"authorization_inactive", "authorization_unavailable"}: return IncidentSeverity.HIGH
    if finding.status in {TrustStatus.INDETERMINATE, TrustStatus.INVALID}: return IncidentSeverity.MEDIUM
    return IncidentSeverity.LOW

def _state(finding: IntegrityResult) -> IncidentState:
    return IncidentState.NO_INCIDENT if finding.status is TrustStatus.TRUSTED else (IncidentState.INDETERMINATE if finding.status in {TrustStatus.INDETERMINATE, TrustStatus.INVALID} else IncidentState.OPEN)

def create_integrity_incident(source: VerifiedIncidentInput, finding: IntegrityResult, rules: SeverityRules, *, created_at: datetime) -> IntegrityIncidentAttestation:
    if not verify_integrity_result(finding) or source.finding_id != finding.result_digest: raise IntegrityIncidentError("integrity finding is invalid.")
    state = _state(finding); severity = classify_severity(finding, rules)
    recommendation = ContainmentRecommendation.REQUEST_CONTAINMENT if severity in {IncidentSeverity.CRITICAL, IncidentSeverity.HIGH} else (ContainmentRecommendation.INVESTIGATE if state is not IncidentState.NO_INCIDENT else ContainmentRecommendation.NONE)
    finding_type = finding.reason_category; key = _hash({"deployment":source.deployment_id,"finding_type":finding_type,"evidence":source.finding_evidence_digest})
    evidence = _hash({"source":_source_doc(source),"finding":finding.result_digest})
    provisional = IntegrityIncidentAttestation("0"*64,key,state,severity,finding_type,recommendation,source,rules.version,evidence,created_at,"0"*64)
    document = _incident_doc(provisional); attestation_digest = _hash(document)
    return replace(provisional, attestation_digest=attestation_digest, incident_id=_hash({**document,"attestation_digest":attestation_digest}))

class InMemoryIntegrityIncidentStore:
    def __init__(self) -> None: self._lock = Lock(); self._by_key: dict[str, IntegrityIncidentAttestation] = {}
    def get(self, incident_key: str) -> IntegrityIncidentAttestation | None:
        with self._lock: return self._by_key.get(incident_key)
    def put_if_absent(self, attestation: IntegrityIncidentAttestation) -> IntegrityIncidentAttestation:
        if not verify_integrity_incident_attestation(attestation): raise IntegrityIncidentError("incident attestation is invalid.")
        with self._lock:
            self._by_key.setdefault(attestation.incident_key, attestation); return self._by_key[attestation.incident_key]
    def append_transition(self, incident_id: str, transition: IncidentTransitionEvidence) -> IntegrityIncidentAttestation:
        with self._lock:
            current = next((item for item in self._by_key.values() if item.incident_id == incident_id), None)
            if current is None or transition.incident_id != incident_id: raise IntegrityIncidentError("incident is unavailable.")
            if current.state not in {IncidentState.OPEN, IncidentState.CONTAINED}: raise IntegrityIncidentError("incident transition is invalid.")
            if transition.target_state is IncidentState.RESOLVED and current.state not in {IncidentState.OPEN, IncidentState.CONTAINED}: raise IntegrityIncidentError("incident transition is invalid.")
            updated = replace(current, state=transition.target_state)
            # State changes are represented as a new attestation, never mutation of historical evidence.
            document = _incident_doc(updated); digest = _hash(document); updated = replace(updated, attestation_digest=digest, incident_id=_hash({**document,"attestation_digest":digest}))
            self._by_key[updated.incident_key] = updated; return updated

def record_integrity_incident(source: VerifiedIncidentInput, finding: IntegrityResult, rules: SeverityRules, *, created_at: datetime,
                              store: IntegrityIncidentStorePort, evidence: IncidentEvidencePort | None = None,
                              notifications: IncidentNotificationPort | None = None, containment: ContainmentActionPort | None = None) -> tuple[IntegrityIncidentAttestation, bool]:
    candidate = create_integrity_incident(source, finding, rules, created_at=created_at); prior = store.get(candidate.incident_key)
    incident = store.put_if_absent(candidate)
    created = prior is None
    if created:
        if evidence: evidence.preserve(incident)
        if notifications and incident.state is not IncidentState.NO_INCIDENT: notifications.notify(incident)
        if containment and incident.recommendation is ContainmentRecommendation.REQUEST_CONTAINMENT: containment.request(incident)
    return incident, not created
