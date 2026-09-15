from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Callable, Protocol

from src.reference_architecture_deployment_authorization_contract import (
    AuthorizationLifecycleRecord,
    DeploymentAuthorizationAttestation,
)


ADMISSION_CONTRACT_VERSION = "1.0"


def _identifier(value: object, name: str) -> str:
    if type(value) is not str or not value or len(value) > 256 or value.strip() != value:
        raise ValueError(f"{name} is invalid.")
    return value


def _digest(value: object, name: str) -> str:
    if type(value) is not str or len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise ValueError(f"{name} must be a lowercase SHA-256 digest.")
    return value


def _utc(value: object, name: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware.")
    normalized = value.astimezone(timezone.utc)
    if normalized.microsecond:
        raise ValueError(f"{name} must use whole-second precision.")
    return normalized


class AdmissionDecision(str, Enum):
    PERMITTED = "permitted"
    BLOCKED = "blocked"
    INDETERMINATE = "indeterminate"
    INVALID = "invalid"


class AuthorizationUsage(str, Enum):
    SINGLE_USE = "single_use"
    REUSABLE = "reusable"


@dataclass(frozen=True, slots=True)
class EnforcementPolicyReference:
    policy_id: str
    version: str
    digest: str

    def __post_init__(self) -> None:
        _identifier(self.policy_id, "policy_id")
        _identifier(self.version, "policy_version")
        _digest(self.digest, "policy_digest")


@dataclass(frozen=True, slots=True)
class AdmissionEnforcementPolicy:
    policy_id: str
    version: str
    allowed_operations: frozenset[str]
    allowed_environment_classifications: frozenset[str]
    usage: AuthorizationUsage = AuthorizationUsage.SINGLE_USE
    minimum_remaining_validity_seconds: int = 0
    maximum_clock_skew_seconds: int = 0

    def __post_init__(self) -> None:
        _identifier(self.policy_id, "policy_id")
        _identifier(self.version, "policy_version")
        for values, name in (
            (self.allowed_operations, "allowed_operations"),
            (self.allowed_environment_classifications, "allowed_environment_classifications"),
        ):
            if not isinstance(values, frozenset) or not values:
                raise ValueError(f"{name} must be a non-empty frozenset.")
            for value in values:
                _identifier(value, name)
        if not isinstance(self.usage, AuthorizationUsage):
            raise ValueError("usage is invalid.")
        for value, name in (
            (self.minimum_remaining_validity_seconds, "minimum_remaining_validity_seconds"),
            (self.maximum_clock_skew_seconds, "maximum_clock_skew_seconds"),
        ):
            if type(value) is not int or value < 0:
                raise ValueError(f"{name} must be a non-negative integer.")


@dataclass(frozen=True, slots=True)
class DeploymentAdmissionRequest:
    admission_request_id: str
    deployment_attempt_id: str
    authorization_id: str
    artifact_id: str
    artifact_digest: str
    release_id: str
    tenant_id: str
    target_environment: str
    environment_classification: str
    deployment_scope: str
    operation: str
    configuration_digest: str
    requested_conditions: tuple[str, ...]
    requested_at: datetime
    evaluation_time: datetime
    correlation_id: str
    enforcement_policy: EnforcementPolicyReference
    idempotency_key: str
    contract_version: str = ADMISSION_CONTRACT_VERSION

    def __post_init__(self) -> None:
        for value, name in (
            (self.admission_request_id, "admission_request_id"),
            (self.deployment_attempt_id, "deployment_attempt_id"),
            (self.artifact_id, "artifact_id"), (self.release_id, "release_id"),
            (self.tenant_id, "tenant_id"), (self.target_environment, "target_environment"),
            (self.environment_classification, "environment_classification"),
            (self.deployment_scope, "deployment_scope"), (self.operation, "operation"),
            (self.correlation_id, "correlation_id"), (self.idempotency_key, "idempotency_key"),
        ):
            _identifier(value, name)
        for value, name in (
            (self.authorization_id, "authorization_id"),
            (self.artifact_digest, "artifact_digest"),
            (self.configuration_digest, "configuration_digest"),
        ):
            _digest(value, name)
        if not isinstance(self.requested_conditions, tuple) or len(self.requested_conditions) != len(set(self.requested_conditions)):
            raise ValueError("requested_conditions must be a duplicate-free tuple.")
        for value in self.requested_conditions:
            _identifier(value, "requested_condition")
        object.__setattr__(self, "requested_at", _utc(self.requested_at, "requested_at"))
        object.__setattr__(self, "evaluation_time", _utc(self.evaluation_time, "evaluation_time"))
        if not isinstance(self.enforcement_policy, EnforcementPolicyReference):
            raise ValueError("enforcement_policy is invalid.")
        if self.contract_version != ADMISSION_CONTRACT_VERSION:
            raise ValueError("contract_version is unsupported.")


@dataclass(frozen=True, slots=True)
class CanonicalDeploymentRequest:
    digest: str
    canonical_bytes: bytes


@dataclass(frozen=True, slots=True)
class VerifiedAuthorizationReference:
    authorization_id: str
    artifact_id: str
    artifact_digest: str
    release_id: str
    tenant_id: str
    environment: str
    scope: str
    conditions: tuple[str, ...]
    authorization_policy_id: str
    valid_from: datetime
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class DeploymentAdmissionReceipt:
    receipt_id: str
    deployment_attempt_id: str
    authorization_id: str
    request_binding_digest: str
    outcome: AdmissionDecision
    enforcement_policy_id: str
    enforcement_policy_version: str
    enforcement_policy_digest: str
    evaluated_at: datetime
    consumption_reference: str
    correlation_id: str
    integrity_digest: str


@dataclass(frozen=True, slots=True)
class AdmissionResult:
    decision: AdmissionDecision
    reason_codes: tuple[str, ...]
    authorization_id: str | None
    deployment_attempt_id: str
    request_binding_digest: str | None
    enforcement_policy: EnforcementPolicyReference
    evaluated_at: datetime
    receipt: DeploymentAdmissionReceipt | None = None
    idempotent_replay: bool = False

    @property
    def permitted(self) -> bool:
        return self.decision is AdmissionDecision.PERMITTED and self.receipt is not None


@dataclass(frozen=True, slots=True)
class PublicAdmissionResult:
    admission_request_id: str
    deployment_attempt_id: str
    authorization_reference: str | None
    outcome: AdmissionDecision
    permitted: bool
    reason_codes: tuple[str, ...]
    evaluated_at: datetime
    receipt_reference: str | None
    request_binding_digest: str | None
    contract_version: str = ADMISSION_CONTRACT_VERSION


class AuthorizationVerifierPort(Protocol):
    def verify(self, authorization: DeploymentAuthorizationAttestation | None, *,
               history: tuple[AuthorizationLifecycleRecord, ...],
               evaluation_time: datetime, request: DeploymentAdmissionRequest,
               ) -> tuple[VerifiedAuthorizationReference | None, str]: ...


class EnforcementStateStore(Protocol):
    def consume(self, *, authorization_id: str, attempt_id: str, idempotency_key: str,
                request_digest: str, single_use: bool,
                receipt_factory: Callable[[str], DeploymentAdmissionReceipt],
                ) -> tuple[DeploymentAdmissionReceipt | None, bool, str | None]: ...


class DeploymentExecutorPort(Protocol):
    def execute(self, request: DeploymentAdmissionRequest,
                receipt: DeploymentAdmissionReceipt) -> None: ...
