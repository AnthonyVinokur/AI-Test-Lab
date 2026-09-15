from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from pydantic import Field

from src.public_contract import PublicContractModel
from src.reference_architecture_deployment_execution_contract import digest, identifier, utc


INCIDENT_CLOSURE_CONTRACT_VERSION = "1.0"


class IncidentClosureError(ValueError):
    """Normalized fail-closed error at the incident-closure boundary."""


class ClosureDecision(str, Enum):
    CLOSED = "closed"


@dataclass(frozen=True, slots=True)
class ClosureAuthorization:
    incident_id: str
    closer_id: str
    authority_id: str
    expires_at: datetime
    evidence_digest: str
    signature: str

    def __post_init__(self) -> None:
        for value, name in ((self.incident_id, "authorization_incident_id"),
                            (self.evidence_digest, "authorization_evidence_digest"),
                            (self.signature, "authorization_signature")):
            digest(value, name)
        for value, name in ((self.closer_id, "authorized_closer"), (self.authority_id, "closure_authority")):
            identifier(value, name)
        object.__setattr__(self, "expires_at", utc(self.expires_at, "closure_authorization_expiry"))


class RootCauseCategory(str, Enum):
    CONFIGURATION = "configuration"
    DEPENDENCY = "dependency"
    DEPLOYMENT_PROCESS = "deployment_process"
    AUTHORIZATION = "authorization"
    INTEGRITY = "integrity"
    OPERATOR_ACTION = "operator_action"
    UNKNOWN = "unknown"


class ImpactCategory(str, Enum):
    AVAILABILITY = "availability"
    INTEGRITY = "integrity"
    AUTHORIZATION = "authorization"
    EVIDENCE = "evidence"
    NO_EXTERNAL_IMPACT = "no_external_impact"


class PreventiveActionPriority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class PreventiveActionStatus(str, Enum):
    OPEN = "open"
    ACCEPTED = "accepted"
    DEFERRED = "deferred"
    COMPLETED = "completed"
    NOT_APPLICABLE = "not_applicable"


@dataclass(frozen=True, slots=True)
class RootCauseClassification:
    category: RootCauseCategory
    impact: tuple[ImpactCategory, ...]
    evidence_digest: str
    recorded_by: str
    recorded_at: datetime

    def __post_init__(self) -> None:
        if not self.impact or len(set(self.impact)) != len(self.impact):
            raise IncidentClosureError("impact classification is invalid.")
        digest(self.evidence_digest, "root_cause_evidence_digest")
        identifier(self.recorded_by, "root_cause_recorded_by")
        object.__setattr__(self, "recorded_at", utc(self.recorded_at, "root_cause_recorded_at"))


@dataclass(frozen=True, slots=True)
class PreventiveActionRecord:
    action_id: str
    incident_id: str
    action_type: str
    owner_id: str
    due_condition: str
    priority: PreventiveActionPriority
    status: PreventiveActionStatus
    evidence_digest: str
    created_at: datetime
    record_digest: str
    schema_version: str = INCIDENT_CLOSURE_CONTRACT_VERSION

    def __post_init__(self) -> None:
        for value, name in ((self.action_id, "preventive_action_id"), (self.incident_id, "incident_id"),
                            (self.evidence_digest, "preventive_action_evidence_digest"),
                            (self.record_digest, "preventive_action_record_digest")):
            digest(value, name)
        for value, name in ((self.action_type, "preventive_action_type"), (self.owner_id, "preventive_action_owner"),
                            (self.due_condition, "preventive_action_due_condition")):
            identifier(value, name)
        object.__setattr__(self, "created_at", utc(self.created_at, "preventive_action_created_at"))
        if self.schema_version != INCIDENT_CLOSURE_CONTRACT_VERSION:
            raise IncidentClosureError("preventive action schema version is unsupported.")


@dataclass(frozen=True, slots=True)
class PreventiveActionDisposition:
    action_id: str
    status: PreventiveActionStatus
    decided_by: str
    justification: str
    evidence_digest: str
    decided_at: datetime
    disposition_digest: str

    def __post_init__(self) -> None:
        if self.status not in {PreventiveActionStatus.ACCEPTED, PreventiveActionStatus.DEFERRED,
                               PreventiveActionStatus.COMPLETED, PreventiveActionStatus.NOT_APPLICABLE}:
            raise IncidentClosureError("preventive action disposition is invalid.")
        for value, name in ((self.action_id, "preventive_action_id"), (self.evidence_digest, "disposition_evidence_digest"),
                            (self.disposition_digest, "disposition_digest")):
            digest(value, name)
        for value, name in ((self.decided_by, "disposition_actor"), (self.justification, "disposition_justification")):
            identifier(value, name)
        object.__setattr__(self, "decided_at", utc(self.decided_at, "disposition_decided_at"))


@dataclass(frozen=True, slots=True)
class IncidentClosureRecord:
    closure_id: str
    incident_id: str
    remediation_reference: str
    reconciliation_evidence_digest: str
    verification_evidence_digest: str
    root_cause: RootCauseClassification
    preventive_action_ids: tuple[str, ...]
    decision: ClosureDecision
    closed_by: str
    closed_at: datetime
    reason: str
    closure_digest: str
    schema_version: str = INCIDENT_CLOSURE_CONTRACT_VERSION

    def __post_init__(self) -> None:
        for value, name in ((self.closure_id, "closure_id"), (self.incident_id, "incident_id"),
                            (self.remediation_reference, "remediation_reference"),
                            (self.reconciliation_evidence_digest, "reconciliation_evidence_digest"),
                            (self.verification_evidence_digest, "verification_evidence_digest"),
                            (self.closure_digest, "closure_digest")):
            digest(value, name)
        if not self.preventive_action_ids or len(set(self.preventive_action_ids)) != len(self.preventive_action_ids):
            raise IncidentClosureError("preventive action references are invalid.")
        for action_id in self.preventive_action_ids: digest(action_id, "preventive_action_id")
        for value, name in ((self.closed_by, "closure_actor"), (self.reason, "closure_reason")):
            identifier(value, name)
        object.__setattr__(self, "closed_at", utc(self.closed_at, "closed_at"))
        if self.schema_version != INCIDENT_CLOSURE_CONTRACT_VERSION:
            raise IncidentClosureError("incident closure schema version is unsupported.")


class PublicIncidentClosureAttestationV1(PublicContractModel):
    schema_version: str = INCIDENT_CLOSURE_CONTRACT_VERSION
    incident_id: str = Field(min_length=64, max_length=64)
    closure_id: str = Field(min_length=64, max_length=64)
    closed: bool
    closed_at: datetime
    preventive_action_count: int = Field(ge=1)
    closure_evidence_digest: str = Field(min_length=64, max_length=64)
