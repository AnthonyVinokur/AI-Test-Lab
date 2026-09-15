from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Callable, Mapping, Protocol

from src.reference_architecture_deployment_admission_contract import DeploymentAdmissionReceipt


EXECUTION_CONTRACT_VERSION = "1.0"
ATTESTATION_CONTRACT_VERSION = "1.0"


def identifier(value: object, name: str) -> str:
    if type(value) is not str or not value or len(value) > 256 or value.strip() != value:
        raise ValueError(f"{name} is invalid.")
    return value


def digest(value: object, name: str) -> str:
    if type(value) is not str or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise ValueError(f"{name} must be a lowercase SHA-256 digest.")
    return value


def utc(value: object, name: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware.")
    normalized = value.astimezone(timezone.utc)
    if normalized.microsecond:
        raise ValueError(f"{name} must use whole-second precision.")
    return normalized


class ExecutionOutcome(str, Enum):
    BLOCKED = "blocked"
    INVALID = "invalid"
    INDETERMINATE = "indeterminate"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REJECTED = "rejected"
    TIMED_OUT = "timed_out"
    OUTCOME_UNKNOWN = "outcome_unknown"


class ExecutionClaimState(str, Enum):
    UNCLAIMED = "unclaimed"
    CLAIMED = "claimed"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    OUTCOME_UNKNOWN = "outcome_unknown"


@dataclass(frozen=True, slots=True)
class ExecutionPolicyReference:
    policy_id: str
    version: str
    digest: str

    def __post_init__(self) -> None:
        identifier(self.policy_id, "policy_id"); identifier(self.version, "policy_version")
        digest(self.digest, "policy_digest")


@dataclass(frozen=True, slots=True)
class ExecutionPolicy:
    policy_id: str
    version: str
    permitted_adapters: frozenset[str]
    adapter_contract_versions: frozenset[str]
    permitted_operations: frozenset[str]
    environment_classifications: frozenset[str]
    required_capabilities: frozenset[str] = field(default_factory=frozenset)
    timeout_seconds: int = 300
    retry_eligible: bool = True
    maximum_attempts: int = 1
    minimum_receipt_lifetime_seconds: int = 0
    dry_run_required: bool = False
    reconcile_uncertain_outcomes: bool = False
    retained_provider_fields: frozenset[str] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        identifier(self.policy_id, "policy_id"); identifier(self.version, "policy_version")
        for values, name, empty_ok in (
            (self.permitted_adapters, "permitted_adapters", False),
            (self.adapter_contract_versions, "adapter_contract_versions", False),
            (self.permitted_operations, "permitted_operations", False),
            (self.environment_classifications, "environment_classifications", False),
            (self.required_capabilities, "required_capabilities", True),
            (self.retained_provider_fields, "retained_provider_fields", True),
        ):
            if not isinstance(values, frozenset) or (not values and not empty_ok):
                raise ValueError(f"{name} is invalid.")
            for value in values: identifier(value, name)
        if type(self.timeout_seconds) is not int or self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds is invalid.")
        if type(self.maximum_attempts) is not int or self.maximum_attempts <= 0:
            raise ValueError("maximum_attempts is invalid.")
        if type(self.minimum_receipt_lifetime_seconds) is not int or self.minimum_receipt_lifetime_seconds < 0:
            raise ValueError("minimum_receipt_lifetime_seconds is invalid.")


@dataclass(frozen=True, slots=True)
class DeploymentExecutionRequest:
    execution_attempt_id: str
    admission_receipt_id: str
    deployment_request_digest: str
    authorization_id: str
    artifact_id: str
    artifact_digest: str
    tenant_id: str
    target_environment: str
    environment_classification: str
    release_id: str
    operation: str
    deployment_scope: str
    configuration_digest: str
    idempotency_key: str
    requested_adapter: str
    adapter_contract_version: str
    evaluation_time: datetime
    trace_reference: str
    execution_policy: ExecutionPolicyReference
    required_conditions: tuple[str, ...] = ()
    dry_run: bool = False
    contract_version: str = EXECUTION_CONTRACT_VERSION

    def __post_init__(self) -> None:
        for value, name in ((self.execution_attempt_id, "execution_attempt_id"),
            (self.artifact_id, "artifact_id"), (self.tenant_id, "tenant_id"),
            (self.target_environment, "target_environment"),
            (self.environment_classification, "environment_classification"),
            (self.release_id, "release_id"), (self.operation, "operation"),
            (self.deployment_scope, "deployment_scope"), (self.idempotency_key, "idempotency_key"),
            (self.requested_adapter, "requested_adapter"),
            (self.adapter_contract_version, "adapter_contract_version"),
            (self.trace_reference, "trace_reference")):
            identifier(value, name)
        for value, name in ((self.admission_receipt_id, "admission_receipt_id"),
            (self.deployment_request_digest, "deployment_request_digest"),
            (self.authorization_id, "authorization_id"), (self.artifact_digest, "artifact_digest"),
            (self.configuration_digest, "configuration_digest")):
            digest(value, name)
        if not isinstance(self.required_conditions, tuple) or len(self.required_conditions) != len(set(self.required_conditions)):
            raise ValueError("required_conditions must be a duplicate-free tuple.")
        for condition in self.required_conditions: identifier(condition, "required_condition")
        if type(self.dry_run) is not bool: raise ValueError("dry_run is invalid.")
        object.__setattr__(self, "evaluation_time", utc(self.evaluation_time, "evaluation_time"))
        if not isinstance(self.execution_policy, ExecutionPolicyReference): raise ValueError("execution_policy is invalid.")
        if self.contract_version != EXECUTION_CONTRACT_VERSION: raise ValueError("contract_version is unsupported.")


@dataclass(frozen=True, slots=True)
class VerifiedAdmissionReference:
    receipt_id: str
    deployment_request_digest: str
    authorization_id: str
    artifact_id: str
    artifact_digest: str
    tenant_id: str
    environment: str
    environment_classification: str
    release_id: str
    operation: str
    scope: str
    configuration_digest: str
    conditions: tuple[str, ...]
    admission_policy_id: str
    admitted_at: datetime
    valid_until: datetime
    admission_contract_version: str
    consumption_reference: str
    outcome: str = "permitted"

    def __post_init__(self) -> None:
        for value, name in ((self.artifact_id, "artifact_id"), (self.tenant_id, "tenant_id"),
            (self.environment, "environment"), (self.environment_classification, "environment_classification"),
            (self.release_id, "release_id"), (self.operation, "operation"), (self.scope, "scope"),
            (self.admission_policy_id, "admission_policy_id"),
            (self.admission_contract_version, "admission_contract_version"),
            (self.consumption_reference, "consumption_reference")):
            identifier(value, name)
        for value, name in ((self.receipt_id, "receipt_id"),
            (self.deployment_request_digest, "deployment_request_digest"),
            (self.authorization_id, "authorization_id"), (self.artifact_digest, "artifact_digest"),
            (self.configuration_digest, "configuration_digest")):
            digest(value, name)
        if not isinstance(self.conditions, tuple) or len(self.conditions) != len(set(self.conditions)):
            raise ValueError("conditions must be a duplicate-free tuple.")
        object.__setattr__(self, "admitted_at", utc(self.admitted_at, "admitted_at"))
        object.__setattr__(self, "valid_until", utc(self.valid_until, "valid_until"))
        if self.valid_until <= self.admitted_at: raise ValueError("admission validity window is invalid.")
        if self.outcome != "permitted": raise ValueError("admission outcome is invalid.")


@dataclass(frozen=True, slots=True)
class ExecutionCommand:
    request: DeploymentExecutionRequest
    verified_admission: VerifiedAdmissionReference
    execution_policy: ExecutionPolicyReference
    execution_command_digest: str


@dataclass(frozen=True, slots=True)
class ProviderExecutionResult:
    adapter_execution_reference: str
    provider_operation_reference: str | None
    outcome: ExecutionOutcome
    started_at: datetime
    completed_at: datetime | None
    provider_response_digest: str
    reason_code: str
    observed_artifact_digest: str | None = None
    observed_environment: str | None = None

    def __post_init__(self) -> None:
        identifier(self.adapter_execution_reference, "adapter_execution_reference")
        if self.provider_operation_reference is not None: identifier(self.provider_operation_reference, "provider_operation_reference")
        if self.outcome not in {ExecutionOutcome.SUCCEEDED, ExecutionOutcome.FAILED, ExecutionOutcome.REJECTED,
                                ExecutionOutcome.TIMED_OUT, ExecutionOutcome.OUTCOME_UNKNOWN}:
            raise ValueError("provider outcome is invalid.")
        object.__setattr__(self, "started_at", utc(self.started_at, "started_at"))
        if self.completed_at is not None: object.__setattr__(self, "completed_at", utc(self.completed_at, "completed_at"))
        digest(self.provider_response_digest, "provider_response_digest"); identifier(self.reason_code, "reason_code")
        if self.observed_artifact_digest is not None: digest(self.observed_artifact_digest, "observed_artifact_digest")
        if self.observed_environment is not None: identifier(self.observed_environment, "observed_environment")


@dataclass(frozen=True, slots=True)
class DeploymentExecutionAttestation:
    attestation_id: str
    execution_attempt_id: str
    execution_command_digest: str
    admission_receipt_id: str
    authorization_id: str
    artifact_digest: str
    tenant_id: str
    environment: str
    release_id: str
    operation: str
    adapter_identity: str
    adapter_version: str
    execution_policy: ExecutionPolicyReference
    outcome: ExecutionOutcome
    provider_response_digest: str
    provider_operation_reference: str | None
    reason_code: str
    started_at: datetime
    completed_at: datetime | None
    previous_state_reference: str
    trace_reference: str
    attestation_digest: str
    contract_version: str = ATTESTATION_CONTRACT_VERSION
    # Optional for attestations minted before ATL-A.18.  New attestations retain
    # the approved configuration binding for continuous integrity monitoring.
    configuration_digest: str | None = None

    def __post_init__(self) -> None:
        for value, name in ((self.attestation_id, "attestation_id"),
            (self.execution_command_digest, "execution_command_digest"),
            (self.admission_receipt_id, "admission_receipt_id"),
            (self.authorization_id, "authorization_id"), (self.artifact_digest, "artifact_digest"),
            (self.provider_response_digest, "provider_response_digest"),
            (self.previous_state_reference, "previous_state_reference"),
            (self.attestation_digest, "attestation_digest")):
            digest(value, name)
        if self.configuration_digest is not None:
            digest(self.configuration_digest, "configuration_digest")
        for value, name in ((self.execution_attempt_id, "execution_attempt_id"),
            (self.tenant_id, "tenant_id"), (self.environment, "environment"),
            (self.release_id, "release_id"), (self.operation, "operation"),
            (self.adapter_identity, "adapter_identity"), (self.adapter_version, "adapter_version"),
            (self.reason_code, "reason_code"), (self.trace_reference, "trace_reference")):
            identifier(value, name)
        object.__setattr__(self, "started_at", utc(self.started_at, "started_at"))
        if self.completed_at is not None: object.__setattr__(self, "completed_at", utc(self.completed_at, "completed_at"))
        if self.contract_version != ATTESTATION_CONTRACT_VERSION: raise ValueError("attestation version is unsupported.")


@dataclass(frozen=True, slots=True)
class DeploymentExecutionResult:
    outcome: ExecutionOutcome
    reason_code: str
    execution_attempt_id: str
    execution_command_digest: str | None
    evaluated_at: datetime
    attestation: DeploymentExecutionAttestation | None = None
    idempotent_replay: bool = False


@dataclass(frozen=True, slots=True)
class PublicDeploymentExecutionResult:
    contract_version: str
    execution_attempt_id: str
    admission_receipt_id: str
    attestation_id: str | None
    outcome: ExecutionOutcome
    reason_code: str
    artifact_reference: str
    environment_reference: str
    release_reference: str
    started_at: datetime | None
    completed_at: datetime | None
    trace_reference: str


class DeploymentAdapterPort(Protocol):
    identity: str
    contract_version: str
    capabilities: frozenset[str]
    def execute(self, command: ExecutionCommand) -> ProviderExecutionResult: ...


class AdmissionReceiptVerifierPort(Protocol):
    def verify(self, receipt: DeploymentAdmissionReceipt | None,
               request: DeploymentExecutionRequest) -> VerifiedAdmissionReference | None: ...


class ExecutionStateStore(Protocol):
    def claim(self, *, receipt_id: str, command_digest: str, idempotency_key: str,
              attempt_id: str) -> tuple[str, DeploymentExecutionResult | None]: ...
    def mark_executing(self, *, command_digest: str) -> str: ...
    def finalize(self, *, command_digest: str, result: DeploymentExecutionResult) -> None: ...


ReceiptVerification = Callable[[DeploymentAdmissionReceipt, DeploymentExecutionRequest], VerifiedAdmissionReference | None]
