from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Protocol

from src.reference_architecture_deployment_execution_contract import DeploymentExecutionAttestation, digest, identifier, utc


OUTCOME_VERIFICATION_CONTRACT_VERSION = "1.0"


class DeploymentOutcomeVerificationState(str, Enum):
    VERIFIED = "verified"
    MISMATCH = "mismatch"
    INDETERMINATE = "indeterminate"
    INVALID = "invalid"


class ObservedDeploymentState(str, Enum):
    DEPLOYED = "deployed"
    NOT_DEPLOYED = "not_deployed"
    UNKNOWN = "unknown"


class ObservedHealthState(str, Enum):
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class OutcomeVerificationPolicy:
    policy_id: str
    version: str
    maximum_evidence_age_seconds: int
    required_health: ObservedHealthState = ObservedHealthState.HEALTHY

    def __post_init__(self) -> None:
        identifier(self.policy_id, "policy_id")
        identifier(self.version, "policy_version")
        if type(self.maximum_evidence_age_seconds) is not int or self.maximum_evidence_age_seconds < 0:
            raise ValueError("maximum_evidence_age_seconds is invalid.")
        if self.required_health is not ObservedHealthState.HEALTHY:
            raise ValueError("required_health is unsupported.")


@dataclass(frozen=True, slots=True)
class ExpectedDeploymentState:
    execution_attestation_id: str
    execution_attestation_fingerprint: str
    provider_identity: str
    artifact_digest: str
    environment: str
    release_id: str
    required_health: ObservedHealthState
    expected_state_fingerprint: str
    tenant_id: str | None = None
    configuration_digest: str | None = None

    def __post_init__(self) -> None:
        for value, name in ((self.execution_attestation_id, "execution_attestation_id"),
                            (self.execution_attestation_fingerprint, "execution_attestation_fingerprint"),
                            (self.artifact_digest, "artifact_digest"),
                            (self.expected_state_fingerprint, "expected_state_fingerprint")):
            digest(value, name)
        for value, name in ((self.provider_identity, "provider_identity"), (self.environment, "environment"),
                            (self.release_id, "release_id")):
            identifier(value, name)
        if self.tenant_id is not None: identifier(self.tenant_id, "tenant_id")
        if self.configuration_digest is not None: digest(self.configuration_digest, "configuration_digest")
        if self.required_health is not ObservedHealthState.HEALTHY:
            raise ValueError("required_health is unsupported.")


@dataclass(frozen=True, slots=True)
class DeploymentOutcomeObservation:
    observer_identity: str
    provider_identity: str
    environment: str
    observed_artifact_digest: str | None
    observed_release_id: str | None
    deployment_state: ObservedDeploymentState
    health_state: ObservedHealthState
    observed_at: datetime
    correlation_reference: str | None
    diagnostics_reference: str | None
    observation_fingerprint: str

    def __post_init__(self) -> None:
        for value, name in ((self.observer_identity, "observer_identity"),
                            (self.provider_identity, "provider_identity"), (self.environment, "environment")):
            identifier(value, name)
        if self.observed_artifact_digest is not None:
            digest(self.observed_artifact_digest, "observed_artifact_digest")
        if self.observed_release_id is not None:
            identifier(self.observed_release_id, "observed_release_id")
        for value, name in ((self.correlation_reference, "correlation_reference"),
                            (self.diagnostics_reference, "diagnostics_reference")):
            if value is not None:
                identifier(value, name)
        object.__setattr__(self, "observed_at", utc(self.observed_at, "observed_at"))
        digest(self.observation_fingerprint, "observation_fingerprint")


@dataclass(frozen=True, slots=True)
class DeploymentOutcomeVerificationAttestation:
    verification_id: str
    execution_attestation_id: str
    execution_attestation_fingerprint: str
    expected_state_fingerprint: str
    observer_identity: str | None
    evidence_timestamp: datetime | None
    observation_fingerprint: str | None
    state: DeploymentOutcomeVerificationState
    reason_code: str
    diagnostic_references: tuple[str, ...]
    verification_time: datetime
    policy_id: str
    policy_version: str
    attestation_digest: str
    contract_version: str = OUTCOME_VERIFICATION_CONTRACT_VERSION

    def __post_init__(self) -> None:
        for value, name in ((self.verification_id, "verification_id"),
                            (self.execution_attestation_id, "execution_attestation_id"),
                            (self.execution_attestation_fingerprint, "execution_attestation_fingerprint"),
                            (self.expected_state_fingerprint, "expected_state_fingerprint"),
                            (self.attestation_digest, "attestation_digest")):
            digest(value, name)
        if self.observation_fingerprint is not None:
            digest(self.observation_fingerprint, "observation_fingerprint")
        for value, name in ((self.observer_identity, "observer_identity"), (self.reason_code, "reason_code"),
                            (self.policy_id, "policy_id"), (self.policy_version, "policy_version")):
            if value is not None:
                identifier(value, name)
        if not isinstance(self.diagnostic_references, tuple) or len(self.diagnostic_references) != len(set(self.diagnostic_references)):
            raise ValueError("diagnostic_references must be a duplicate-free tuple.")
        for reference in self.diagnostic_references:
            identifier(reference, "diagnostic_reference")
        object.__setattr__(self, "verification_time", utc(self.verification_time, "verification_time"))
        if self.evidence_timestamp is not None:
            object.__setattr__(self, "evidence_timestamp", utc(self.evidence_timestamp, "evidence_timestamp"))
        if self.contract_version != OUTCOME_VERIFICATION_CONTRACT_VERSION:
            raise ValueError("contract_version is unsupported.")


@dataclass(frozen=True, slots=True)
class DeploymentOutcomeVerificationResult:
    state: DeploymentOutcomeVerificationState
    reason_code: str
    verification_time: datetime
    attestation: DeploymentOutcomeVerificationAttestation | None
    idempotent_replay: bool = False


@dataclass(frozen=True, slots=True)
class PublicDeploymentOutcomeVerificationResult:
    contract_version: str
    verification_id: str | None
    execution_attestation_id: str | None
    state: DeploymentOutcomeVerificationState
    reason_code: str
    verification_time: datetime
    evidence_timestamp: datetime | None


class DeploymentOutcomeObserverPort(Protocol):
    identity: str
    provider_identity: str
    target_environment: str
    def observe(self, expected: ExpectedDeploymentState, *, verification_time: datetime) -> DeploymentOutcomeObservation: ...


class OutcomeVerificationStateStore(Protocol):
    def claim(self, *, execution_attestation_id: str, verification_window: str) -> tuple[str, DeploymentOutcomeVerificationAttestation | None]: ...
    def finalize(self, *, execution_attestation_id: str, verification_window: str,
                 attestation: DeploymentOutcomeVerificationAttestation) -> None: ...


class ExecutionAttestationVerifierPort(Protocol):
    def verify(self, attestation: DeploymentExecutionAttestation | None) -> bool: ...
