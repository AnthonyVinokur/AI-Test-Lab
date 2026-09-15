from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from src.reference_architecture_deployment_execution_contract import digest, identifier, utc

RECOVERY_CONTRACT_VERSION = "1.0"
class RecoveryError(ValueError): """Normalized fail-closed recovery boundary error."""
class RemediationRequestStatus(str, Enum): REQUESTED="requested"; WITHDRAWN="withdrawn"; SUPERSEDED="superseded"
class RecoveryDecisionStatus(str, Enum): APPROVED="approved"; REJECTED="rejected"; EXPIRED="expired"
class RecoveryExecutionStatus(str, Enum): EXECUTED="executed"; BLOCKED="blocked"; FAILED="failed"
class RecoveryVerificationStatus(str, Enum): PASSED="passed"; FAILED="failed"; UNAVAILABLE="unavailable"

@dataclass(frozen=True, slots=True)
class RemediationRequest:
    incident_id:str; deployment_id:str; artifact_digest:str; tenant_id:str; environment:str; action:str; action_fingerprint:str; requested_at:datetime; status:RemediationRequestStatus=RemediationRequestStatus.REQUESTED
    def __post_init__(self):
        for x,n in ((self.incident_id,"incident_id"),(self.artifact_digest,"artifact_digest"),(self.action_fingerprint,"action_fingerprint")): digest(x,n)
        for x,n in ((self.deployment_id,"deployment_id"),(self.tenant_id,"tenant_id"),(self.environment,"environment"),(self.action,"action")): identifier(x,n)
        object.__setattr__(self,"requested_at",utc(self.requested_at,"requested_at"))

@dataclass(frozen=True, slots=True)
class RecoveryDecision:
    request:RemediationRequest; status:RecoveryDecisionStatus; expires_at:datetime; authority_id:str; signature:str
    def __post_init__(self):
        identifier(self.authority_id,"authority_id"); digest(self.signature,"signature"); object.__setattr__(self,"expires_at",utc(self.expires_at,"expires_at"))
        if self.expires_at <= self.request.requested_at: raise RecoveryError("recovery decision expiry is invalid.")

@dataclass(frozen=True, slots=True)
class RecoveryExecutionAttestation:
    request:RemediationRequest; status:RecoveryExecutionStatus; before_digest:str; after_digest:str; executed_at:datetime
    def __post_init__(self):
        digest(self.before_digest,"before_digest"); digest(self.after_digest,"after_digest"); object.__setattr__(self,"executed_at",utc(self.executed_at,"executed_at"))

@dataclass(frozen=True, slots=True)
class PostRemediationVerification:
    execution:RecoveryExecutionAttestation; integrity_evidence_digest:str; outcome_evidence_digest:str; status:RecoveryVerificationStatus; verified_at:datetime
    def __post_init__(self):
        digest(self.integrity_evidence_digest,"integrity_evidence_digest"); digest(self.outcome_evidence_digest,"outcome_evidence_digest"); object.__setattr__(self,"verified_at",utc(self.verified_at,"verified_at"))

@dataclass(frozen=True, slots=True)
class PublicRecoveryEvidence:
    incident_id:str; action_fingerprint:str; execution_status:str; verification_status:str; eligible_for_resolution:bool
