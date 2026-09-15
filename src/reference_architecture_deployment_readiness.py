from __future__ import annotations

import hashlib
import json
from datetime import datetime

from src.reference_architecture_deployment_incident_closure import verify_incident_closure_record
from src.reference_architecture_deployment_incident_closure_contract import IncidentClosureRecord
from src.reference_architecture_deployment_integrity_contract import IntegrityResult, TrustStatus
from src.reference_architecture_deployment_integrity_incident_contract import IncidentState, IntegrityIncidentAttestation
from src.reference_architecture_deployment_recovery import authorize_recovery
from src.reference_architecture_deployment_recovery_contract import (
    PostRemediationVerification, RecoveryDecision, RecoveryExecutionAttestation,
    RecoveryExecutionStatus, RecoveryVerificationStatus,
)
from src.reference_architecture_deployment_readiness_contract import *


def _time(value: datetime) -> str: return value.strftime("%Y-%m-%dT%H:%M:%SZ")


def _digest(*, deployment_id: str, status: DeploymentReadinessStatus,
            reasons: tuple[ReadinessReasonCode, ...], attested_at: datetime) -> str:
    document = {"deployment_id": deployment_id, "status": status.value,
                "reason_codes": [reason.value for reason in reasons], "attested_at": _time(attested_at),
                "schema_version": READINESS_ATTESTATION_CONTRACT_VERSION}
    return hashlib.sha256(json.dumps(document, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def verify_deployment_readiness_attestation(value: DeploymentReadinessAttestation) -> bool:
    return value.attestation_digest == _digest(deployment_id=value.deployment_id, status=value.status,
        reasons=value.reason_codes, attested_at=value.attested_at)


def _status_for(reasons: tuple[ReadinessReasonCode, ...]) -> DeploymentReadinessStatus:
    if not reasons:
        return DeploymentReadinessStatus.READY
    review = {ReadinessReasonCode.INTEGRITY_EVIDENCE_UNAVAILABLE, ReadinessReasonCode.INCIDENT_EVIDENCE_UNAVAILABLE,
              ReadinessReasonCode.RECOVERY_VERIFICATION_INCOMPLETE, ReadinessReasonCode.POST_INCIDENT_CLOSURE_INCOMPLETE}
    return DeploymentReadinessStatus.REVIEW_REQUIRED if all(reason in review for reason in reasons) else DeploymentReadinessStatus.BLOCKED


def attest_deployment_readiness(*, deployment_id: str, integrity: IntegrityResult | None,
                                incident: IntegrityIncidentAttestation | None = None,
                                recovery_decision: RecoveryDecision | None = None,
                                recovery_execution: RecoveryExecutionAttestation | None = None,
                                recovery_verification: PostRemediationVerification | None = None,
                                incident_closure: IncidentClosureRecord | None = None,
                                attested_at: datetime) -> DeploymentReadinessAttestation:
    """Return a deterministic, fail-closed release readiness decision from existing trusted evidence."""
    reasons: list[ReadinessReasonCode] = []
    if integrity is None or integrity.status in {TrustStatus.INDETERMINATE, TrustStatus.DEGRADED}:
        reasons.append(ReadinessReasonCode.INTEGRITY_EVIDENCE_UNAVAILABLE)
    elif integrity.status is not TrustStatus.TRUSTED:
        reasons.append(ReadinessReasonCode.INTEGRITY_NOT_VERIFIED)
    if incident is not None and incident.source.deployment_id != deployment_id:
        reasons.append(ReadinessReasonCode.INCIDENT_EVIDENCE_UNAVAILABLE)
    elif incident is not None and incident.state in {IncidentState.OPEN, IncidentState.CONTAINED}:
        reasons.append(ReadinessReasonCode.ACTIVE_DEPLOYMENT_INCIDENT)
    elif incident is not None and incident.state is IncidentState.INDETERMINATE:
        reasons.append(ReadinessReasonCode.INCIDENT_EVIDENCE_UNAVAILABLE)
    elif incident is not None and incident.state is IncidentState.RESOLVED:
        execution_is_bound = recovery_execution is not None and recovery_execution.request.incident_id == incident.incident_id and recovery_execution.request.deployment_id == deployment_id
        authorization_is_valid = execution_is_bound and recovery_decision is not None and authorize_recovery(recovery_execution.request, recovery_decision, attested_at)
        if not authorization_is_valid:
            reasons.append(ReadinessReasonCode.RECOVERY_AUTHORIZATION_INVALID)
        verification_is_valid = execution_is_bound and recovery_verification is not None and recovery_execution.status is RecoveryExecutionStatus.EXECUTED and recovery_verification.execution == recovery_execution and recovery_verification.status is RecoveryVerificationStatus.PASSED
        if not verification_is_valid:
            reasons.append(ReadinessReasonCode.RECOVERY_VERIFICATION_INCOMPLETE)
        closure_is_valid = verification_is_valid and incident_closure is not None and incident_closure.incident_id == incident.incident_id and verify_incident_closure_record(incident_closure)
        if not closure_is_valid:
            reasons.append(ReadinessReasonCode.POST_INCIDENT_CLOSURE_INCOMPLETE)
    unique_reasons = tuple(dict.fromkeys(reasons))
    status = _status_for(unique_reasons)
    return DeploymentReadinessAttestation(deployment_id, status, unique_reasons, attested_at,
        _digest(deployment_id=deployment_id, status=status, reasons=unique_reasons, attested_at=attested_at))


def public_deployment_readiness_attestation(value: DeploymentReadinessAttestation) -> PublicDeploymentReadinessAttestationV1:
    if not verify_deployment_readiness_attestation(value):
        raise DeploymentReadinessError("readiness attestation is invalid.")
    return PublicDeploymentReadinessAttestationV1(deployment_id=value.deployment_id, status=value.status,
        reason_codes=value.reason_codes, attested_at=value.attested_at)
