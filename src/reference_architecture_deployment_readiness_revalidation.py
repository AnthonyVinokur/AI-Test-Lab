"""INTERNAL readiness revalidation; bindings are associations, not authentication."""
from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from datetime import datetime, timedelta
from enum import Enum

from src import reference_architecture_deployment_readiness as readiness
from src.reference_architecture_deployment_execution_contract import identifier, utc
from src.reference_architecture_deployment_incident_closure_contract import IncidentClosureRecord
from src.reference_architecture_deployment_integrity_contract import IntegrityResult
from src.reference_architecture_deployment_integrity_incident_contract import IntegrityIncidentAttestation
from src.reference_architecture_deployment_readiness_contract import (
    DeploymentReadinessAttestation, DeploymentReadinessError,
    PublicDeploymentReadinessAttestationV1, ReadinessReasonCode,
)
from src.reference_architecture_deployment_recovery_contract import (
    PostRemediationVerification, RecoveryDecision, RecoveryExecutionAttestation,
)


@dataclass(frozen=True, slots=True)
class ReadinessEvidence:
    """Immutable current snapshot. Explicit incident=None means confirmed no incident.

    Revision identifies the deployment/evidence revision in the caller's store.
    Existing immutable identities and all supplied evidence are retained exactly.
    """
    deployment_id: str
    revision: str
    integrity: IntegrityResult | None
    incident: IntegrityIncidentAttestation | None
    incident_evidence_available: bool = True
    recovery_decision: RecoveryDecision | None = None
    recovery_execution: RecoveryExecutionAttestation | None = None
    recovery_verification: PostRemediationVerification | None = None
    incident_closure: IncidentClosureRecord | None = None

    def __post_init__(self) -> None:
        try:
            identifier(self.deployment_id, "deployment_id")
            identifier(self.revision, "evidence_revision")
            expected = ((self.integrity, IntegrityResult),
                        (self.incident, IntegrityIncidentAttestation),
                        (self.recovery_decision, RecoveryDecision),
                        (self.recovery_execution, RecoveryExecutionAttestation),
                        (self.recovery_verification, PostRemediationVerification),
                        (self.incident_closure, IncidentClosureRecord))
            if any(value is not None and not isinstance(value, kind) for value, kind in expected):
                raise ValueError("invalid evidence type")
            if type(self.incident_evidence_available) is not bool:
                raise ValueError("invalid availability")
        except ValueError:
            raise DeploymentReadinessError("readiness evidence is invalid.") from None


@dataclass(frozen=True, slots=True)
class ReadinessEvidenceBinding:
    attestation: DeploymentReadinessAttestation
    evidence: ReadinessEvidence
    expires_at: datetime


class ApplicabilityReason(str, Enum):
    MISSING_BINDING = "missing_binding"
    BINDING_MISMATCH = "binding_mismatch"
    EVIDENCE_CHANGED = "evidence_changed"
    INVALID_ATTESTATION = "invalid_attestation"
    INVALID_TIMESTAMP = "invalid_timestamp"
    FUTURE_ISSUANCE = "future_issuance"
    EXPIRED = "expired"


@dataclass(frozen=True, slots=True)
class ReadinessRevalidationResult:
    attestation: DeploymentReadinessAttestation
    binding: ReadinessEvidenceBinding
    previous_applicability_reasons: tuple[ApplicabilityReason, ...]

    @property
    def previous_applicable(self) -> bool:
        return not self.previous_applicability_reasons


def _time(value: datetime) -> datetime:
    try:
        return utc(value, "evaluation_time")
    except (ValueError, OverflowError):
        raise DeploymentReadinessError("readiness timestamp is invalid.") from None


def _expiry(issued_at: datetime, validity: timedelta) -> datetime:
    if not isinstance(validity, timedelta) or validity <= timedelta(0):
        raise DeploymentReadinessError("readiness validity must be positive.")
    try:
        return _time(issued_at + validity)
    except OverflowError:
        raise DeploymentReadinessError("readiness expiry is invalid.") from None


def _timestamps_valid(value: object, now: datetime) -> bool:
    """Evidence events cannot be future-dated; authorization expiry may be future."""
    if is_dataclass(value):
        for field in fields(value):
            item = getattr(value, field.name)
            if isinstance(item, datetime):
                try:
                    normalized = _time(item)
                except DeploymentReadinessError:
                    return False
                if field.name != "expires_at" and normalized > now:
                    return False
            elif not _timestamps_valid(item, now):
                return False
    elif isinstance(value, tuple):
        return all(_timestamps_valid(item, now) for item in value)
    return True


def _evaluate(evidence: ReadinessEvidence, now: datetime) -> DeploymentReadinessAttestation:
    result = readiness.attest_deployment_readiness(
        deployment_id=evidence.deployment_id, integrity=evidence.integrity,
        incident=evidence.incident, recovery_decision=evidence.recovery_decision,
        recovery_execution=evidence.recovery_execution,
        recovery_verification=evidence.recovery_verification,
        incident_closure=evidence.incident_closure, attested_at=now,
    )
    reasons = list(result.reason_codes)
    if not evidence.incident_evidence_available:
        reasons.append(ReadinessReasonCode.INCIDENT_EVIDENCE_UNAVAILABLE)
    if not _timestamps_valid(evidence, now):
        reasons.append(ReadinessReasonCode.INTEGRITY_EVIDENCE_UNAVAILABLE)
    return readiness._attestation_from_reasons(
        evidence.deployment_id, tuple(dict.fromkeys(reasons)), now,
    )


def attest_bound_deployment_readiness(*, evidence: ReadinessEvidence,
                                      evaluation_time: datetime,
                                      validity: timedelta) -> ReadinessEvidenceBinding:
    """Evaluate and bind atomically; never attach new evidence to an old decision."""
    now = _time(evaluation_time)
    expires_at = _expiry(now, validity)
    return ReadinessEvidenceBinding(_evaluate(evidence, now), evidence, expires_at)


def revalidate_deployment_readiness(*, previous: DeploymentReadinessAttestation,
                                    binding: ReadinessEvidenceBinding | None,
                                    evidence: ReadinessEvidence,
                                    evaluation_time: datetime,
                                    validity: timedelta) -> ReadinessRevalidationResult:
    now = _time(evaluation_time)
    _expiry(now, validity)
    if previous.deployment_id != evidence.deployment_id:
        raise DeploymentReadinessError("previous readiness deployment does not match.")
    if binding is not None and binding.evidence.deployment_id != evidence.deployment_id:
        raise DeploymentReadinessError("readiness binding deployment does not match.")
    reasons: list[ApplicabilityReason] = []
    if not readiness.verify_deployment_readiness_attestation(previous):
        reasons.append(ApplicabilityReason.INVALID_ATTESTATION)
    try:
        issued_at = _time(previous.attested_at)
        if issued_at > now:
            reasons.append(ApplicabilityReason.FUTURE_ISSUANCE)
    except DeploymentReadinessError:
        reasons.append(ApplicabilityReason.INVALID_TIMESTAMP)
    if binding is None:
        reasons.append(ApplicabilityReason.MISSING_BINDING)
    else:
        if binding.attestation != previous:
            reasons.append(ApplicabilityReason.BINDING_MISMATCH)
        if binding.evidence != evidence:
            reasons.append(ApplicabilityReason.EVIDENCE_CHANGED)
        try:
            expires_at = _time(binding.expires_at)
            if expires_at <= _time(previous.attested_at):
                reasons.append(ApplicabilityReason.INVALID_TIMESTAMP)
            elif now >= expires_at:
                reasons.append(ApplicabilityReason.EXPIRED)
        except DeploymentReadinessError:
            reasons.append(ApplicabilityReason.INVALID_TIMESTAMP)
    fresh = attest_bound_deployment_readiness(
        evidence=evidence, evaluation_time=now, validity=validity,
    )
    return ReadinessRevalidationResult(fresh.attestation, fresh, tuple(dict.fromkeys(reasons)))


def public_deployment_readiness_revalidation(
    value: ReadinessRevalidationResult,
) -> PublicDeploymentReadinessAttestationV1:
    """Only the existing allowlisted ATL-A.22 DTO may cross the public boundary."""
    return readiness.public_deployment_readiness_attestation(value.attestation)
