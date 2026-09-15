from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Protocol

from src.reference_architecture_deployment_execution_contract import digest, identifier, utc

INTEGRITY_INCIDENT_CONTRACT_VERSION = "1.0"


class IncidentState(str, Enum):
    NO_INCIDENT = "no_incident"; OPEN = "open"; CONTAINED = "contained"; RESOLVED = "resolved"; INDETERMINATE = "indeterminate"


class IncidentSeverity(str, Enum):
    CRITICAL = "critical"; HIGH = "high"; MEDIUM = "medium"; LOW = "low"


class ContainmentRecommendation(str, Enum):
    NONE = "none"; REQUEST_CONTAINMENT = "request_containment"; INVESTIGATE = "investigate"


class IntegrityIncidentError(ValueError):
    """A normalized public failure at the integrity-incident boundary."""


@dataclass(frozen=True, slots=True)
class SeverityRules:
    version: str
    policy_id: str = "trusted_deployment_integrity"
    def __post_init__(self) -> None:
        identifier(self.version, "severity_rules_version"); identifier(self.policy_id, "severity_policy_id")


@dataclass(frozen=True, slots=True)
class VerifiedIncidentInput:
    """Allowlisted, already-verified bindings from A.15-A.18; not a decision input."""
    deployment_id: str; release_id: str; artifact_digest: str; configuration_digest: str
    tenant_id: str; environment: str; scope: str; operation: str
    authorization_id: str; admission_receipt_id: str; execution_attestation_id: str
    reconciliation_id: str; baseline_id: str; finding_id: str; finding_evidence_digest: str
    correlation_id: str; causation_id: str; observed_at: datetime
    def __post_init__(self) -> None:
        for value, name in ((self.deployment_id,"deployment_id"),(self.release_id,"release_id"),(self.tenant_id,"tenant_id"),
                            (self.environment,"environment"),(self.scope,"scope"),(self.operation,"operation"),
                            (self.correlation_id,"correlation_id"),(self.causation_id,"causation_id")):
            identifier(value, name)
        for value, name in ((self.artifact_digest,"artifact_digest"),(self.configuration_digest,"configuration_digest"),
                            (self.authorization_id,"authorization_id"),(self.admission_receipt_id,"admission_receipt_id"),
                            (self.execution_attestation_id,"execution_attestation_id"),(self.reconciliation_id,"reconciliation_id"),
                            (self.baseline_id,"baseline_id"),(self.finding_id,"finding_id"),(self.finding_evidence_digest,"finding_evidence_digest")):
            digest(value, name)
        object.__setattr__(self, "observed_at", utc(self.observed_at, "observed_at"))


@dataclass(frozen=True, slots=True)
class IntegrityIncidentAttestation:
    incident_id: str; incident_key: str; state: IncidentState; severity: IncidentSeverity | None
    finding_type: str; recommendation: ContainmentRecommendation; source: VerifiedIncidentInput
    severity_rules_version: str; evidence_digest: str; created_at: datetime; attestation_digest: str
    schema_version: str = INTEGRITY_INCIDENT_CONTRACT_VERSION
    def __post_init__(self) -> None:
        for value, name in ((self.incident_id,"incident_id"),(self.incident_key,"incident_key"),(self.evidence_digest,"evidence_digest"),(self.attestation_digest,"attestation_digest")):
            digest(value, name)
        identifier(self.finding_type, "finding_type"); identifier(self.severity_rules_version, "severity_rules_version")
        object.__setattr__(self, "created_at", utc(self.created_at, "created_at"))
        if self.schema_version != INTEGRITY_INCIDENT_CONTRACT_VERSION: raise IntegrityIncidentError("incident schema version is unsupported.")


@dataclass(frozen=True, slots=True)
class IncidentTransitionEvidence:
    incident_id: str; target_state: IncidentState; verifier_identity: str; evidence_digest: str; verified_at: datetime
    def __post_init__(self) -> None:
        digest(self.incident_id,"incident_id"); digest(self.evidence_digest,"evidence_digest"); identifier(self.verifier_identity,"verifier_identity")
        if self.target_state not in {IncidentState.CONTAINED, IncidentState.RESOLVED}: raise IntegrityIncidentError("incident transition is unsupported.")
        object.__setattr__(self,"verified_at",utc(self.verified_at,"verified_at"))


class IntegrityIncidentStorePort(Protocol):
    def get(self, incident_key: str) -> IntegrityIncidentAttestation | None: ...
    def put_if_absent(self, attestation: IntegrityIncidentAttestation) -> IntegrityIncidentAttestation: ...
    def append_transition(self, incident_id: str, transition: IncidentTransitionEvidence) -> IntegrityIncidentAttestation: ...


class IncidentNotificationPort(Protocol):
    def notify(self, incident: IntegrityIncidentAttestation) -> None: ...


class ContainmentActionPort(Protocol):
    def request(self, incident: IntegrityIncidentAttestation) -> None: ...


class IncidentEvidencePort(Protocol):
    def preserve(self, incident: IntegrityIncidentAttestation) -> None: ...
