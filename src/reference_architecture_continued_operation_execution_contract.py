"""ATL-A.27 trusted continued-operation execution contracts."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Mapping, Protocol

from pydantic import Field

from src.public_contract import PublicContractModel
from src.reference_architecture_continued_operation_enforcement_contract import (
    ContinuedOperationConsumptionRecord,
)
from src.reference_architecture_deployment_execution_contract import digest, identifier, utc


CONTINUED_OPERATION_EXECUTION_CONTRACT_VERSION = "1.0"
CONTINUED_OPERATION_EXECUTION_ATTESTATION_VERSION = "1.0"
CONTINUED_OPERATION_EXECUTION_DIGEST_ALGORITHM = "sha256"


class ContinuedOperationExecutionError(ValueError):
    """Normalized error for invalid ATL-A.27 contract values."""


class ContinuedOperationExecutionOutcome(str, Enum):
    BLOCKED = "blocked"
    INVALID = "invalid"
    INDETERMINATE = "indeterminate"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REJECTED = "rejected"
    TIMED_OUT = "timed_out"
    OUTCOME_UNKNOWN = "outcome_unknown"


class ContinuedOperationExecutionReasonCode(str, Enum):
    EXECUTION_SUCCEEDED = "execution_succeeded"
    EXECUTION_FAILED = "execution_failed"
    PROVIDER_REJECTED = "provider_rejected"
    PROVIDER_TIMED_OUT = "provider_timed_out"
    PROVIDER_OUTCOME_UNKNOWN = "provider_outcome_unknown"
    IDEMPOTENT_RESULT_RETURNED = "idempotent_result_returned"
    INVALID_EXECUTION_REQUEST = "invalid_execution_request"
    UNSUPPORTED_SCHEMA_VERSION = "unsupported_schema_version"
    ENFORCEMENT_RECORD_NOT_FOUND = "enforcement_record_not_found"
    ENFORCEMENT_STATE_UNAVAILABLE = "enforcement_state_unavailable"
    ENFORCEMENT_EVIDENCE_MISMATCH = "enforcement_evidence_mismatch"
    AUTHORIZATION_MISMATCH = "authorization_mismatch"
    ENFORCEMENT_REQUEST_MISMATCH = "enforcement_request_mismatch"
    REQUEST_BINDING_MISMATCH = "request_binding_mismatch"
    DEPLOYMENT_MISMATCH = "deployment_mismatch"
    CONSUMER_MISMATCH = "consumer_mismatch"
    ENFORCEMENT_POINT_MISMATCH = "enforcement_point_mismatch"
    PURPOSE_MISMATCH = "purpose_mismatch"
    OPERATION_MISMATCH = "operation_mismatch"
    CORRELATION_MISMATCH = "correlation_mismatch"
    MANIFEST_NOT_FOUND = "manifest_not_found"
    MANIFEST_DIGEST_MISMATCH = "manifest_digest_mismatch"
    OPERATION_NOT_PERMITTED = "operation_not_permitted"
    DEPLOYMENT_NOT_PERMITTED = "deployment_not_permitted"
    ADAPTER_NOT_PERMITTED = "adapter_not_permitted"
    ADAPTER_NOT_FOUND = "adapter_not_found"
    ADAPTER_VERSION_UNSUPPORTED = "adapter_version_unsupported"
    ADAPTER_CAPABILITY_MISMATCH = "adapter_capability_mismatch"
    EXECUTION_POLICY_MISMATCH = "execution_policy_mismatch"
    EXECUTION_WINDOW_EXPIRED = "execution_window_expired"
    UNTRUSTED_TIME_SOURCE = "untrusted_time_source"
    EXECUTION_ALREADY_CLAIMED = "execution_already_claimed"
    EXECUTION_REQUEST_CONFLICT = "execution_request_conflict"
    EXECUTION_IN_PROGRESS = "execution_in_progress"
    EXECUTION_STATE_UNAVAILABLE = "execution_state_unavailable"
    ADAPTER_RESPONSE_INVALID = "adapter_response_invalid"
    INTERNAL_EXECUTION_ERROR = "internal_execution_error"


class ContinuedOperationExecutionClaimState(str, Enum):
    CLAIMED = "claimed"
    INVOCATION_STARTED = "invocation_started"
    COMPLETED = "completed"
    OUTCOME_UNKNOWN = "outcome_unknown"


class AtomicExecutionClaimState(str, Enum):
    CLAIMED = "claimed"
    EXACT_RETRY = "exact_retry"
    ALREADY_CLAIMED = "already_claimed"
    REQUEST_CONFLICT = "request_conflict"
    STATE_UNAVAILABLE = "state_unavailable"


def _id(value: object, name: str) -> str:
    try:
        return identifier(value, name)
    except ValueError:
        raise ContinuedOperationExecutionError(f"{name} is invalid.") from None


def _digest(value: object, name: str) -> str:
    try:
        return digest(value, name)
    except ValueError:
        raise ContinuedOperationExecutionError(f"{name} is invalid.") from None


def _time(value: object, name: str) -> datetime:
    try:
        return utc(value, name)
    except (ValueError, OverflowError):
        raise ContinuedOperationExecutionError(f"{name} is invalid.") from None


def _ids(values: object, name: str, *, empty: bool = False) -> tuple[str, ...]:
    if type(values) is not tuple or (not values and not empty):
        raise ContinuedOperationExecutionError(f"{name} is invalid.")
    for value in values:
        _id(value, name)
    if len(values) != len(set(values)):
        raise ContinuedOperationExecutionError(f"{name} is invalid.")
    return values


@dataclass(frozen=True, slots=True)
class ContinuedOperationExecutionRequest:
    execution_attempt_id: str
    enforcement_request_id: str
    authorization_id: str
    authorization_digest: str
    enforcement_evidence_reference: str
    enforcement_evidence_digest: str
    request_binding_digest: str
    deployment_id: str
    consumer_id: str
    enforcement_point_id: str
    purpose: str
    operation_reference: str
    operation_manifest_reference: str
    operation_manifest_digest: str
    requested_adapter: str
    adapter_contract_version: str
    execution_policy_reference: str
    idempotency_key: str
    requested_at: datetime
    correlation_id: str
    schema_version: str = CONTINUED_OPERATION_EXECUTION_CONTRACT_VERSION

    def __post_init__(self) -> None:
        for value, name in (
            (self.execution_attempt_id, "execution_attempt_id"),
            (self.enforcement_request_id, "enforcement_request_id"),
            (self.deployment_id, "deployment_id"), (self.consumer_id, "consumer_id"),
            (self.enforcement_point_id, "enforcement_point_id"),
            (self.purpose, "purpose"), (self.operation_reference, "operation_reference"),
            (self.operation_manifest_reference, "operation_manifest_reference"),
            (self.requested_adapter, "requested_adapter"),
            (self.adapter_contract_version, "adapter_contract_version"),
            (self.execution_policy_reference, "execution_policy_reference"),
            (self.idempotency_key, "idempotency_key"),
            (self.correlation_id, "correlation_id"),
        ):
            _id(value, name)
        for value, name in (
            (self.authorization_id, "authorization_id"),
            (self.authorization_digest, "authorization_digest"),
            (self.enforcement_evidence_reference, "enforcement_evidence_reference"),
            (self.enforcement_evidence_digest, "enforcement_evidence_digest"),
            (self.request_binding_digest, "request_binding_digest"),
            (self.operation_manifest_digest, "operation_manifest_digest"),
        ):
            _digest(value, name)
        object.__setattr__(self, "requested_at", _time(self.requested_at, "requested_at"))
        if self.schema_version != CONTINUED_OPERATION_EXECUTION_CONTRACT_VERSION:
            raise ContinuedOperationExecutionError("execution schema version is unsupported.")


@dataclass(frozen=True, slots=True)
class TrustedContinuedOperationPermit:
    authorization_id: str
    authorization_digest: str
    enforcement_request_id: str
    enforcement_evidence_digest: str
    request_binding_digest: str
    deployment_id: str
    consumer_id: str
    enforcement_point_id: str
    purpose: str
    operation_reference: str
    consumed_at: datetime
    enforcement_policy_reference: str
    correlation_id: str

    def __post_init__(self) -> None:
        for value, name in (
            (self.authorization_id, "authorization_id"),
            (self.authorization_digest, "authorization_digest"),
            (self.enforcement_evidence_digest, "enforcement_evidence_digest"),
            (self.request_binding_digest, "request_binding_digest"),
        ):
            _digest(value, name)
        for value, name in (
            (self.enforcement_request_id, "enforcement_request_id"),
            (self.deployment_id, "deployment_id"), (self.consumer_id, "consumer_id"),
            (self.enforcement_point_id, "enforcement_point_id"),
            (self.purpose, "purpose"), (self.operation_reference, "operation_reference"),
            (self.enforcement_policy_reference, "enforcement_policy_reference"),
            (self.correlation_id, "correlation_id"),
        ):
            _id(value, name)
        object.__setattr__(self, "consumed_at", _time(self.consumed_at, "consumed_at"))


@dataclass(frozen=True, slots=True)
class ProtectedOperationManifest:
    reference: str
    operation_reference: str
    version: str
    canonical_operation_input_digest: str
    permitted_adapters: tuple[str, ...]
    permitted_adapter_contract_versions: tuple[str, ...]
    required_capabilities: tuple[str, ...]
    timeout_seconds: int
    permitted_deployments: tuple[str, ...]
    environment_restrictions: tuple[str, ...]
    safe_retry_classification: str
    result_retention_classification: str

    def __post_init__(self) -> None:
        for value, name in (
            (self.reference, "manifest_reference"),
            (self.operation_reference, "operation_reference"), (self.version, "manifest_version"),
            (self.safe_retry_classification, "safe_retry_classification"),
            (self.result_retention_classification, "result_retention_classification"),
        ):
            _id(value, name)
        _digest(self.canonical_operation_input_digest, "canonical_operation_input_digest")
        _ids(self.permitted_adapters, "permitted_adapters")
        _ids(self.permitted_adapter_contract_versions, "permitted_adapter_contract_versions")
        _ids(self.required_capabilities, "required_capabilities", empty=True)
        _ids(self.permitted_deployments, "permitted_deployments")
        _ids(self.environment_restrictions, "environment_restrictions", empty=True)
        if type(self.timeout_seconds) is not int or self.timeout_seconds <= 0:
            raise ContinuedOperationExecutionError("timeout_seconds is invalid.")
        if self.safe_retry_classification != "at-most-once":
            raise ContinuedOperationExecutionError("safe retry classification is invalid.")


@dataclass(frozen=True, slots=True)
class ContinuedOperationExecutionPolicy:
    reference: str
    maximum_permit_to_execution_delay_seconds: int
    permitted_adapters: tuple[str, ...]
    permitted_adapter_contract_versions: tuple[str, ...]

    def __post_init__(self) -> None:
        _id(self.reference, "execution_policy_reference")
        _ids(self.permitted_adapters, "permitted_adapters")
        _ids(self.permitted_adapter_contract_versions, "permitted_adapter_contract_versions")
        if (type(self.maximum_permit_to_execution_delay_seconds) is not int or
                self.maximum_permit_to_execution_delay_seconds < 0):
            raise ContinuedOperationExecutionError("maximum execution delay is invalid.")


@dataclass(frozen=True, slots=True)
class ContinuedOperationExecutionCommand:
    request: ContinuedOperationExecutionRequest
    permit: TrustedContinuedOperationPermit
    manifest: ProtectedOperationManifest
    command_digest: str

    def __post_init__(self) -> None:
        if (type(self.request) is not ContinuedOperationExecutionRequest or
                type(self.permit) is not TrustedContinuedOperationPermit or
                type(self.manifest) is not ProtectedOperationManifest):
            raise ContinuedOperationExecutionError("execution command is invalid.")
        _digest(self.command_digest, "command_digest")


@dataclass(frozen=True, slots=True)
class ContinuedOperationExecutionClaim:
    authorization_id: str
    enforcement_request_id: str
    execution_attempt_id: str
    idempotency_key: str
    command_digest: str
    operation_manifest_digest: str
    claim_timestamp: datetime
    claim_state: ContinuedOperationExecutionClaimState
    final_result_reference: str | None = None

    def __post_init__(self) -> None:
        _digest(self.authorization_id, "authorization_id")
        _digest(self.command_digest, "command_digest")
        _digest(self.operation_manifest_digest, "operation_manifest_digest")
        for value, name in (
            (self.enforcement_request_id, "enforcement_request_id"),
            (self.execution_attempt_id, "execution_attempt_id"),
            (self.idempotency_key, "idempotency_key"),
        ):
            _id(value, name)
        if not isinstance(self.claim_state, ContinuedOperationExecutionClaimState):
            raise ContinuedOperationExecutionError("claim state is invalid.")
        if self.final_result_reference is not None:
            _digest(self.final_result_reference, "final_result_reference")
        object.__setattr__(self, "claim_timestamp", _time(self.claim_timestamp, "claim_timestamp"))


@dataclass(frozen=True, slots=True)
class ContinuedOperationAdapterResult:
    adapter_execution_reference: str
    outcome: ContinuedOperationExecutionOutcome
    reason_code: ContinuedOperationExecutionReasonCode
    started_at: datetime
    completed_at: datetime | None
    provider_operation_reference: str | None
    sanitized_provider_response_digest: str

    def __post_init__(self) -> None:
        _id(self.adapter_execution_reference, "adapter_execution_reference")
        if self.provider_operation_reference is not None:
            _id(self.provider_operation_reference, "provider_operation_reference")
        _digest(self.sanitized_provider_response_digest, "sanitized_provider_response_digest")
        if self.outcome not in {
            ContinuedOperationExecutionOutcome.SUCCEEDED,
            ContinuedOperationExecutionOutcome.FAILED,
            ContinuedOperationExecutionOutcome.REJECTED,
            ContinuedOperationExecutionOutcome.TIMED_OUT,
            ContinuedOperationExecutionOutcome.OUTCOME_UNKNOWN,
        } or not isinstance(self.reason_code, ContinuedOperationExecutionReasonCode):
            raise ContinuedOperationExecutionError("adapter result is invalid.")
        object.__setattr__(self, "started_at", _time(self.started_at, "started_at"))
        if self.completed_at is not None:
            object.__setattr__(self, "completed_at", _time(self.completed_at, "completed_at"))
            if self.completed_at < self.started_at:
                raise ContinuedOperationExecutionError("adapter result timestamps are invalid.")


@dataclass(frozen=True, slots=True)
class ContinuedOperationExecutionAttestation:
    attestation_id: str
    attestation_digest: str
    execution_attempt_id: str
    authorization_id: str
    authorization_digest: str
    enforcement_request_id: str
    enforcement_evidence_digest: str
    request_binding_digest: str
    execution_command_digest: str
    operation_reference: str
    operation_manifest_digest: str
    deployment_id: str
    consumer_id: str
    enforcement_point_id: str
    purpose: str
    adapter_identity: str
    adapter_contract_version: str
    execution_policy_reference: str
    outcome: ContinuedOperationExecutionOutcome
    reason_code: ContinuedOperationExecutionReasonCode
    started_at: datetime
    completed_at: datetime | None
    provider_operation_reference: str | None
    sanitized_provider_response_digest: str
    previous_execution_state_reference: str
    correlation_id: str
    contract_version: str = CONTINUED_OPERATION_EXECUTION_ATTESTATION_VERSION

    def __post_init__(self) -> None:
        for value, name in (
            (self.attestation_id, "attestation_id"), (self.attestation_digest, "attestation_digest"),
            (self.authorization_id, "authorization_id"),
            (self.authorization_digest, "authorization_digest"),
            (self.enforcement_evidence_digest, "enforcement_evidence_digest"),
            (self.request_binding_digest, "request_binding_digest"),
            (self.execution_command_digest, "execution_command_digest"),
            (self.operation_manifest_digest, "operation_manifest_digest"),
            (self.sanitized_provider_response_digest, "sanitized_provider_response_digest"),
            (self.previous_execution_state_reference, "previous_execution_state_reference"),
        ):
            _digest(value, name)
        for value, name in (
            (self.execution_attempt_id, "execution_attempt_id"),
            (self.enforcement_request_id, "enforcement_request_id"),
            (self.operation_reference, "operation_reference"),
            (self.deployment_id, "deployment_id"), (self.consumer_id, "consumer_id"),
            (self.enforcement_point_id, "enforcement_point_id"), (self.purpose, "purpose"),
            (self.adapter_identity, "adapter_identity"),
            (self.adapter_contract_version, "adapter_contract_version"),
            (self.execution_policy_reference, "execution_policy_reference"),
            (self.correlation_id, "correlation_id"),
        ):
            _id(value, name)
        if self.provider_operation_reference is not None:
            _id(self.provider_operation_reference, "provider_operation_reference")
        if (not isinstance(self.outcome, ContinuedOperationExecutionOutcome) or
                not isinstance(self.reason_code, ContinuedOperationExecutionReasonCode)):
            raise ContinuedOperationExecutionError("execution attestation is invalid.")
        object.__setattr__(self, "started_at", _time(self.started_at, "started_at"))
        if self.completed_at is not None:
            object.__setattr__(self, "completed_at", _time(self.completed_at, "completed_at"))
        if self.contract_version != CONTINUED_OPERATION_EXECUTION_ATTESTATION_VERSION:
            raise ContinuedOperationExecutionError("attestation version is unsupported.")


@dataclass(frozen=True, slots=True)
class ContinuedOperationExecutionResult:
    execution_attempt_id: str
    enforcement_request_id: str
    authorization_id: str
    deployment_id: str
    purpose: str
    operation_reference: str
    outcome: ContinuedOperationExecutionOutcome
    reason_codes: tuple[ContinuedOperationExecutionReasonCode, ...]
    evaluated_at: datetime
    correlation_id: str
    attestation: ContinuedOperationExecutionAttestation | None = None
    idempotent: bool = False

    def __post_init__(self) -> None:
        for value, name in (
            (self.execution_attempt_id, "execution_attempt_id"),
            (self.enforcement_request_id, "enforcement_request_id"),
            (self.deployment_id, "deployment_id"), (self.purpose, "purpose"),
            (self.operation_reference, "operation_reference"),
            (self.correlation_id, "correlation_id"),
        ):
            _id(value, name)
        _digest(self.authorization_id, "authorization_id")
        if (not isinstance(self.outcome, ContinuedOperationExecutionOutcome) or
                type(self.reason_codes) is not tuple or not self.reason_codes or
                any(not isinstance(value, ContinuedOperationExecutionReasonCode)
                    for value in self.reason_codes) or
                len(set(self.reason_codes)) != len(self.reason_codes) or
                type(self.idempotent) is not bool):
            raise ContinuedOperationExecutionError("execution result is invalid.")
        if self.attestation is not None and type(self.attestation) is not ContinuedOperationExecutionAttestation:
            raise ContinuedOperationExecutionError("execution result is invalid.")
        object.__setattr__(self, "evaluated_at", _time(self.evaluated_at, "evaluated_at"))


@dataclass(frozen=True, slots=True)
class AtomicExecutionClaimResult:
    state: AtomicExecutionClaimState
    claim: ContinuedOperationExecutionClaim | None
    result: ContinuedOperationExecutionResult | None = None

    def __post_init__(self) -> None:
        if (not isinstance(self.state, AtomicExecutionClaimState) or
                (self.claim is not None and
                 type(self.claim) is not ContinuedOperationExecutionClaim) or
                (self.result is not None and
                 type(self.result) is not ContinuedOperationExecutionResult)):
            raise ContinuedOperationExecutionError("atomic execution claim result is invalid.")
        if self.state is AtomicExecutionClaimState.CLAIMED and self.claim is None:
            raise ContinuedOperationExecutionError("atomic execution claim result is inconsistent.")


class PublicContinuedOperationExecutionV1(PublicContractModel):
    schema_version: str = CONTINUED_OPERATION_EXECUTION_CONTRACT_VERSION
    execution_attempt_id: str = Field(min_length=1)
    enforcement_request_id: str = Field(min_length=1)
    authorization_id: str = Field(min_length=1)
    deployment_id: str = Field(min_length=1)
    purpose: str = Field(min_length=1)
    operation_reference: str = Field(min_length=1)
    outcome: ContinuedOperationExecutionOutcome
    reason_codes: tuple[ContinuedOperationExecutionReasonCode, ...]
    started_at: datetime | None = None
    completed_at: datetime | None = None
    attestation_reference: str | None = None
    correlation_id: str = Field(min_length=1)
    idempotent: bool = False


class ContinuedOperationConsumptionRecordRepository(Protocol):
    def get_by_evidence_reference(
        self, reference: str,
    ) -> ContinuedOperationConsumptionRecord | None: ...


class ProtectedOperationManifestRepository(Protocol):
    def get(self, reference: str) -> ProtectedOperationManifest | None: ...


class ContinuedOperationExecutionAdapter(Protocol):
    identity: str
    contract_version: str
    capabilities: frozenset[str]

    def execute(
        self, command: ContinuedOperationExecutionCommand,
    ) -> ContinuedOperationAdapterResult: ...


class ContinuedOperationExecutionStateStore(Protocol):
    def claim(
        self, *, request: ContinuedOperationExecutionRequest,
        command_digest: str, claimed_at: datetime,
    ) -> AtomicExecutionClaimResult: ...

    def mark_invocation_started(self, *, command_digest: str) -> str: ...

    def finalize(
        self, *, command_digest: str, result: ContinuedOperationExecutionResult,
    ) -> None: ...


__all__ = [name for name in globals() if name.startswith("ContinuedOperation") or
           name.startswith("ProtectedOperation") or name.startswith("TrustedContinued") or
           name.startswith("AtomicExecution") or name.startswith("PublicContinued")]
__all__ += ["CONTINUED_OPERATION_EXECUTION_CONTRACT_VERSION",
            "CONTINUED_OPERATION_EXECUTION_ATTESTATION_VERSION",
            "CONTINUED_OPERATION_EXECUTION_DIGEST_ALGORITHM"]
