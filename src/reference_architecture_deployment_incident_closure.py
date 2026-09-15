from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, replace
from datetime import datetime
from threading import Lock
from typing import Any

from src.reference_architecture_deployment_incident_closure_contract import *
from src.reference_architecture_deployment_integrity_incident_contract import IncidentState, IntegrityIncidentAttestation
from src.reference_architecture_deployment_recovery_contract import (
    PostRemediationVerification, RecoveryExecutionAttestation, RecoveryExecutionStatus,
    RecoveryVerificationStatus,
)


def _hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def _time(value: datetime) -> str: return value.strftime("%Y-%m-%dT%H:%M:%SZ")
def _root_doc(value: RootCauseClassification) -> dict[str, Any]:
    return {"category": value.category.value, "impact": [item.value for item in value.impact], "evidence_digest": value.evidence_digest,
            "recorded_by": value.recorded_by, "recorded_at": _time(value.recorded_at)}
def _action_doc(value: PreventiveActionRecord) -> dict[str, Any]:
    return {"incident_id": value.incident_id, "action_type": value.action_type, "owner_id": value.owner_id,
            "due_condition": value.due_condition, "priority": value.priority.value, "status": value.status.value,
            "evidence_digest": value.evidence_digest, "created_at": _time(value.created_at), "schema_version": value.schema_version}
def _disposition_doc(value: PreventiveActionDisposition) -> dict[str, Any]:
    return {"action_id": value.action_id, "status": value.status.value, "decided_by": value.decided_by,
            "justification": value.justification, "evidence_digest": value.evidence_digest, "decided_at": _time(value.decided_at)}
def _closure_doc(value: IncidentClosureRecord) -> dict[str, Any]:
    return {"incident_id": value.incident_id, "remediation_reference": value.remediation_reference,
            "reconciliation_evidence_digest": value.reconciliation_evidence_digest,
            "verification_evidence_digest": value.verification_evidence_digest, "root_cause": _root_doc(value.root_cause),
            "preventive_action_ids": list(value.preventive_action_ids), "decision": value.decision.value,
            "closed_by": value.closed_by, "closed_at": _time(value.closed_at), "reason": value.reason,
            "schema_version": value.schema_version}


def authorize_closure(*, incident_id: str, closer_id: str, authority_id: str, expires_at: datetime,
                      evidence_digest: str) -> ClosureAuthorization:
    provisional = ClosureAuthorization(incident_id, closer_id, authority_id, expires_at, evidence_digest, "0" * 64)
    signature = _hash({"incident_id": incident_id, "closer_id": closer_id, "authority_id": authority_id,
                       "expires_at": _time(provisional.expires_at), "evidence_digest": evidence_digest})
    return replace(provisional, signature=signature)


def verify_closure_authorization(value: ClosureAuthorization | None, *, incident_id: str, closer_id: str,
                                 closed_at: datetime) -> bool:
    try:
        if value is None or value.incident_id != incident_id or value.closer_id != closer_id or closed_at >= value.expires_at:
            return False
        return value == authorize_closure(incident_id=value.incident_id, closer_id=value.closer_id,
          authority_id=value.authority_id, expires_at=value.expires_at, evidence_digest=value.evidence_digest)
    except Exception:
        return False


def verify_preventive_action_record(value: PreventiveActionRecord) -> bool:
    return value.record_digest == _hash(_action_doc(value)) and value.action_id == _hash({**_action_doc(value), "record_digest": value.record_digest})


def verify_preventive_action_disposition(value: PreventiveActionDisposition) -> bool:
    return value.disposition_digest == _hash(_disposition_doc(value))


def verify_incident_closure_record(value: IncidentClosureRecord) -> bool:
    return value.closure_digest == _hash(_closure_doc(value)) and value.closure_id == _hash({**_closure_doc(value), "closure_digest": value.closure_digest})


def create_preventive_action(*, incident_id: str, action_type: str, owner_id: str, due_condition: str,
                             priority: PreventiveActionPriority, evidence_digest: str, created_at: datetime) -> PreventiveActionRecord:
    provisional = PreventiveActionRecord("0" * 64, incident_id, action_type, owner_id, due_condition, priority,
        PreventiveActionStatus.OPEN, evidence_digest, created_at, "0" * 64)
    record_digest = _hash(_action_doc(provisional))
    return replace(provisional, record_digest=record_digest, action_id=_hash({**_action_doc(provisional), "record_digest": record_digest}))


def create_preventive_action_disposition(action: PreventiveActionRecord, *, status: PreventiveActionStatus,
                                         decided_by: str, justification: str, evidence_digest: str,
                                         decided_at: datetime) -> PreventiveActionDisposition:
    if not verify_preventive_action_record(action): raise IncidentClosureError("preventive action record is invalid.")
    provisional = PreventiveActionDisposition(action.action_id, status, decided_by, justification, evidence_digest, decided_at, "0" * 64)
    return replace(provisional, disposition_digest=_hash(_disposition_doc(provisional)))


def closure_eligible(*, incident: IntegrityIncidentAttestation | None, recovery_execution: RecoveryExecutionAttestation | None,
                     verification: PostRemediationVerification | None, reconciliation_evidence_digest: str) -> bool:
    try:
        digest(reconciliation_evidence_digest, "reconciliation_evidence_digest")
        return bool(incident and recovery_execution and verification and incident.state is IncidentState.RESOLVED
          and recovery_execution.status is RecoveryExecutionStatus.EXECUTED
          and recovery_execution.request.incident_id == incident.incident_id
          and recovery_execution.request.deployment_id == incident.source.deployment_id
          and recovery_execution.request.artifact_digest == incident.source.artifact_digest
          and verification.execution == recovery_execution
          and verification.status is RecoveryVerificationStatus.PASSED)
    except Exception:
        return False


def create_incident_closure(*, incident: IntegrityIncidentAttestation, recovery_execution: RecoveryExecutionAttestation,
                            verification: PostRemediationVerification, reconciliation_evidence_digest: str,
                            root_cause: RootCauseClassification, preventive_actions: tuple[PreventiveActionRecord, ...],
                            closure_authorization: ClosureAuthorization | None, closed_by: str, closed_at: datetime,
                            reason: str) -> IncidentClosureRecord:
    if not closure_eligible(incident=incident, recovery_execution=recovery_execution, verification=verification,
                            reconciliation_evidence_digest=reconciliation_evidence_digest):
        raise IncidentClosureError("incident closure evidence is incomplete or contradictory.")
    if not verify_closure_authorization(closure_authorization, incident_id=incident.incident_id, closer_id=closed_by, closed_at=closed_at):
        raise IncidentClosureError("incident closure authorization is invalid.")
    if not preventive_actions or any(not verify_preventive_action_record(action) or action.incident_id != incident.incident_id for action in preventive_actions):
        raise IncidentClosureError("preventive action evidence is invalid.")
    if root_cause.evidence_digest != verification.integrity_evidence_digest:
        raise IncidentClosureError("root cause evidence is not bound to remediation verification.")
    provisional = IncidentClosureRecord("0" * 64, incident.incident_id, recovery_execution.request.action_fingerprint,
      reconciliation_evidence_digest, verification.outcome_evidence_digest, root_cause,
      tuple(action.action_id for action in preventive_actions), ClosureDecision.CLOSED, closed_by, closed_at, reason, "0" * 64)
    closure_digest = _hash(_closure_doc(provisional))
    return replace(provisional, closure_digest=closure_digest, closure_id=_hash({**_closure_doc(provisional), "closure_digest": closure_digest}))


class InMemoryIncidentClosureStore:
    """Append-only closure/action store; records are verified before retention."""
    def __init__(self) -> None:
        self._lock = Lock(); self._closures: dict[str, IncidentClosureRecord] = {}; self._actions: dict[str, PreventiveActionRecord] = {}; self._dispositions: dict[str, list[PreventiveActionDisposition]] = {}
    def close(self, value: IncidentClosureRecord) -> IncidentClosureRecord:
        if not verify_incident_closure_record(value): raise IncidentClosureError("incident closure record is invalid.")
        with self._lock:
            prior = self._closures.get(value.incident_id)
            if prior and prior != value: raise IncidentClosureError("incident is already closed.")
            self._closures[value.incident_id] = value; return value
    def preserve_action(self, value: PreventiveActionRecord) -> PreventiveActionRecord:
        if not verify_preventive_action_record(value): raise IncidentClosureError("preventive action record is invalid.")
        with self._lock:
            existing = self._actions.get(value.action_id)
            if existing and existing != value: raise IncidentClosureError("preventive action is immutable.")
            self._actions[value.action_id] = value; return value
    def append_disposition(self, value: PreventiveActionDisposition) -> PreventiveActionDisposition:
        if not verify_preventive_action_disposition(value): raise IncidentClosureError("preventive action disposition is invalid.")
        with self._lock:
            if value.action_id not in self._actions: raise IncidentClosureError("preventive action is unavailable.")
            history = self._dispositions.setdefault(value.action_id, [])
            if history and history[-1] != value: raise IncidentClosureError("preventive action disposition is immutable.")
            if not history: history.append(value)
            return history[-1]
    def disposition_history(self, action_id: str) -> tuple[PreventiveActionDisposition, ...]:
        with self._lock: return tuple(self._dispositions.get(action_id, ()))


def public_incident_closure_attestation(value: IncidentClosureRecord) -> PublicIncidentClosureAttestationV1:
    if not verify_incident_closure_record(value): raise IncidentClosureError("incident closure record is invalid.")
    return PublicIncidentClosureAttestationV1(incident_id=value.incident_id, closure_id=value.closure_id, closed=True,
      closed_at=value.closed_at, preventive_action_count=len(value.preventive_action_ids), closure_evidence_digest=value.closure_digest)
