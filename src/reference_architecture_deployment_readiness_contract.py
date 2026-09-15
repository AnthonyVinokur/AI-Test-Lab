from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from pydantic import Field

from src.public_contract import PublicContractModel
from src.reference_architecture_deployment_execution_contract import digest, identifier, utc


READINESS_ATTESTATION_CONTRACT_VERSION = "1.0"


class DeploymentReadinessError(ValueError):
    """Normalized fail-closed error at the deployment-readiness boundary."""


class DeploymentReadinessStatus(str, Enum):
    READY = "ready"
    BLOCKED = "blocked"
    REVIEW_REQUIRED = "review_required"


class ReadinessReasonCode(str, Enum):
    INTEGRITY_NOT_VERIFIED = "integrity_not_verified"
    INTEGRITY_EVIDENCE_UNAVAILABLE = "integrity_evidence_unavailable"
    ACTIVE_DEPLOYMENT_INCIDENT = "active_deployment_incident"
    INCIDENT_EVIDENCE_UNAVAILABLE = "incident_evidence_unavailable"
    RECOVERY_AUTHORIZATION_INVALID = "recovery_authorization_invalid"
    RECOVERY_VERIFICATION_INCOMPLETE = "recovery_verification_incomplete"
    POST_INCIDENT_CLOSURE_INCOMPLETE = "post_incident_closure_incomplete"


@dataclass(frozen=True, slots=True)
class DeploymentReadinessAttestation:
    deployment_id: str
    status: DeploymentReadinessStatus
    reason_codes: tuple[ReadinessReasonCode, ...]
    attested_at: datetime
    attestation_digest: str
    schema_version: str = READINESS_ATTESTATION_CONTRACT_VERSION

    def __post_init__(self) -> None:
        identifier(self.deployment_id, "deployment_id")
        digest(self.attestation_digest, "readiness_attestation_digest")
        object.__setattr__(self, "attested_at", utc(self.attested_at, "attested_at"))
        if self.schema_version != READINESS_ATTESTATION_CONTRACT_VERSION:
            raise DeploymentReadinessError("readiness attestation schema version is unsupported.")
        if self.status is DeploymentReadinessStatus.READY and self.reason_codes:
            raise DeploymentReadinessError("ready attestation cannot contain reasons.")
        if self.status is not DeploymentReadinessStatus.READY and not self.reason_codes:
            raise DeploymentReadinessError("non-ready attestation requires reasons.")
        if len(set(self.reason_codes)) != len(self.reason_codes):
            raise DeploymentReadinessError("readiness reasons must be unique.")


class PublicDeploymentReadinessAttestationV1(PublicContractModel):
    schema_version: str = READINESS_ATTESTATION_CONTRACT_VERSION
    deployment_id: str = Field(min_length=1)
    status: DeploymentReadinessStatus
    reason_codes: tuple[ReadinessReasonCode, ...]
    attested_at: datetime
