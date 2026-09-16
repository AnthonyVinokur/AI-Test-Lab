from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Callable, Protocol

from pydantic import Field

from src.public_contract import PublicContractModel
from src.reference_architecture_deployment_continued_operation_authorization_contract import (
    ContinuedOperationAuthorization,
    ContinuedOperationLifecycleState,
    ResolvedAuthorizationVerificationKey,
)
from src.reference_architecture_deployment_execution_contract import digest, identifier, utc


CONTINUED_OPERATION_ENFORCEMENT_CONTRACT_VERSION = "1.0"
CONTINUED_OPERATION_ENFORCEMENT_DIGEST_ALGORITHM = "sha256"


class ContinuedOperationEnforcementError(ValueError):
    """Normalized error for invalid ATL-A.26 contract values."""


class ContinuedOperationEnforcementState(str, Enum):
    PERMITTED = "permitted"
    BLOCKED = "blocked"
    INDETERMINATE = "indeterminate"


class ContinuedOperationEnforcementReasonCode(str, Enum):
    AUTHORIZATION_CONSUMED = "authorization_consumed"
    IDEMPOTENT_RESULT_RETURNED = "idempotent_result_returned"
    DEPLOYMENT_MISMATCH = "deployment_mismatch"
    CONSUMER_MISMATCH = "consumer_mismatch"
    ENFORCEMENT_POINT_MISMATCH = "enforcement_point_mismatch"
    PURPOSE_MISMATCH = "purpose_mismatch"
    OPERATION_MISMATCH = "operation_mismatch"
    POLICY_MISMATCH = "policy_mismatch"
    AUTHORIZATION_DIGEST_MISMATCH = "authorization_digest_mismatch"
    REQUEST_ID_CONFLICT = "request_id_conflict"
    AUTHORIZATION_NOT_FOUND = "authorization_not_found"
    AUTHORIZATION_NOT_AUTHORIZED = "authorization_not_authorized"
    AUTHORIZATION_NOT_YET_VALID = "authorization_not_yet_valid"
    AUTHORIZATION_EXPIRED = "authorization_expired"
    AUTHORIZATION_REVOKED = "authorization_revoked"
    AUTHORIZATION_SUPERSEDED = "authorization_superseded"
    UPSTREAM_STATE_INACTIVE = "upstream_state_inactive"
    AUTHORIZATION_ALREADY_CONSUMED = "authorization_already_consumed"
    REPLAY_DETECTED = "replay_detected"
    ATOMIC_CONSUMPTION_CONFLICT = "atomic_consumption_conflict"
    CONSUMPTION_PERSISTENCE_FAILED = "consumption_persistence_failed"
    CONSUMPTION_STATE_UNAVAILABLE = "consumption_state_unavailable"
    INVALID_ENFORCEMENT_REQUEST = "invalid_enforcement_request"
    UNSUPPORTED_SCHEMA_VERSION = "unsupported_schema_version"
    MISSING_REQUIRED_BINDING = "missing_required_binding"
    UNTRUSTED_TIME_SOURCE = "untrusted_time_source"
    INTERNAL_ENFORCEMENT_ERROR = "internal_enforcement_error"


class AtomicConsumptionState(str, Enum):
    CONSUMED = "consumed"
    IDEMPOTENT = "idempotent"
    ALREADY_CONSUMED = "already_consumed"
    REQUEST_CONFLICT = "request_conflict"
    LIFECYCLE_BLOCKED = "lifecycle_blocked"


def _id(value: object, name: str) -> str:
    try:
        return identifier(value, name)
    except ValueError:
        raise ContinuedOperationEnforcementError(f"{name} is invalid.") from None


def _digest(value: object, name: str) -> str:
    try:
        return digest(value, name)
    except ValueError:
        raise ContinuedOperationEnforcementError(f"{name} is invalid.") from None


def _time(value: object, name: str) -> datetime:
    try:
        return utc(value, name)
    except (ValueError, OverflowError):
        raise ContinuedOperationEnforcementError(f"{name} is invalid.") from None


@dataclass(frozen=True, slots=True)
class ContinuedOperationEnforcementRequest:
    authorization_reference: str
    authorization_digest: str
    enforcement_request_id: str
    deployment_id: str
    consumer_id: str
    enforcement_point_id: str
    purpose: str
    requested_at: datetime
    operation_reference: str
    policy_reference: str
    correlation_id: str
    schema_version: str = CONTINUED_OPERATION_ENFORCEMENT_CONTRACT_VERSION

    def __post_init__(self) -> None:
        for value, name in (
            (self.authorization_reference, "authorization_reference"),
            (self.enforcement_request_id, "enforcement_request_id"),
            (self.deployment_id, "deployment_id"), (self.consumer_id, "consumer_id"),
            (self.enforcement_point_id, "enforcement_point_id"),
            (self.purpose, "purpose"), (self.operation_reference, "operation_reference"),
            (self.policy_reference, "policy_reference"),
            (self.correlation_id, "correlation_id"),
        ):
            _id(value, name)
        _digest(self.authorization_digest, "authorization_digest")
        object.__setattr__(self, "requested_at", _time(self.requested_at, "requested_at"))
        if self.schema_version != CONTINUED_OPERATION_ENFORCEMENT_CONTRACT_VERSION:
            raise ContinuedOperationEnforcementError("enforcement schema version is unsupported.")


@dataclass(frozen=True, slots=True)
class ContinuedOperationEnforcementBinding:
    deployment_id: str
    consumer_id: str
    enforcement_point_id: str
    purpose: str
    operation_reference: str

    def __post_init__(self) -> None:
        for value, name in (
            (self.deployment_id, "deployment_id"), (self.consumer_id, "consumer_id"),
            (self.enforcement_point_id, "enforcement_point_id"),
            (self.purpose, "purpose"), (self.operation_reference, "operation_reference"),
        ):
            _id(value, name)


@dataclass(frozen=True, slots=True)
class ContinuedOperationEnforcementPolicy:
    policy_reference: str
    accepted_authorization_policy_id: str
    accepted_authorization_policy_version: str
    active_from: datetime
    expires_at: datetime
    lifecycle_state: ContinuedOperationLifecycleState
    bindings: tuple[ContinuedOperationEnforcementBinding, ...]

    def __post_init__(self) -> None:
        for value, name in (
            (self.policy_reference, "policy_reference"),
            (self.accepted_authorization_policy_id, "accepted_authorization_policy_id"),
            (self.accepted_authorization_policy_version, "accepted_authorization_policy_version"),
        ):
            _id(value, name)
        active_from = _time(self.active_from, "active_from")
        expires_at = _time(self.expires_at, "expires_at")
        if expires_at <= active_from or not isinstance(
            self.lifecycle_state, ContinuedOperationLifecycleState
        ):
            raise ContinuedOperationEnforcementError("enforcement policy is invalid.")
        if (type(self.bindings) is not tuple or not self.bindings or
                any(type(item) is not ContinuedOperationEnforcementBinding for item in self.bindings) or
                len(set(self.bindings)) != len(self.bindings)):
            raise ContinuedOperationEnforcementError("enforcement policy bindings are invalid.")
        object.__setattr__(self, "active_from", active_from)
        object.__setattr__(self, "expires_at", expires_at)


@dataclass(frozen=True, slots=True)
class StoredContinuedOperationAuthorization:
    reference: str
    artifact: ContinuedOperationAuthorization
    artifact_digest: str
    resolved_key: ResolvedAuthorizationVerificationKey
    lifecycle_state: ContinuedOperationLifecycleState
    upstream_active: bool

    def __post_init__(self) -> None:
        _id(self.reference, "authorization_reference")
        _digest(self.artifact_digest, "authorization_digest")
        if (type(self.artifact) is not ContinuedOperationAuthorization or
                type(self.resolved_key) is not ResolvedAuthorizationVerificationKey or
                not isinstance(self.lifecycle_state, ContinuedOperationLifecycleState) or
                type(self.upstream_active) is not bool):
            raise ContinuedOperationEnforcementError("stored authorization is invalid.")


@dataclass(frozen=True, slots=True)
class ContinuedOperationConsumptionRecord:
    authorization_id: str
    authorization_digest: str
    enforcement_request_id: str
    request_binding_digest: str
    deployment_id: str
    consumer_id: str
    enforcement_point_id: str
    purpose: str
    operation_reference: str
    consumed_at: datetime
    policy_reference: str
    evidence_digest: str
    correlation_id: str

    def __post_init__(self) -> None:
        _digest(self.authorization_id, "authorization_id")
        _digest(self.authorization_digest, "authorization_digest")
        _digest(self.request_binding_digest, "request_binding_digest")
        _digest(self.evidence_digest, "evidence_digest")
        for value, name in (
            (self.enforcement_request_id, "enforcement_request_id"),
            (self.deployment_id, "deployment_id"), (self.consumer_id, "consumer_id"),
            (self.enforcement_point_id, "enforcement_point_id"),
            (self.purpose, "purpose"), (self.operation_reference, "operation_reference"),
            (self.policy_reference, "policy_reference"), (self.correlation_id, "correlation_id"),
        ):
            _id(value, name)
        object.__setattr__(self, "consumed_at", _time(self.consumed_at, "consumed_at"))


@dataclass(frozen=True, slots=True)
class ContinuedOperationEnforcementEvidence:
    evidence_digest: str
    authorization_reference: str
    authorization_digest: str
    authorization_id: str | None
    enforcement_request_id: str
    request_binding_digest: str
    lifecycle_state: str
    consumption_result: str
    enforcement_state: ContinuedOperationEnforcementState
    reason_codes: tuple[ContinuedOperationEnforcementReasonCode, ...]
    decided_at: datetime
    policy_reference: str
    enforcement_point_id: str
    previous_consumption_reference: str | None
    correlation_id: str
    schema_version: str = CONTINUED_OPERATION_ENFORCEMENT_CONTRACT_VERSION

    def __post_init__(self) -> None:
        _digest(self.evidence_digest, "evidence_digest")
        _digest(self.authorization_digest, "authorization_digest")
        _digest(self.request_binding_digest, "request_binding_digest")
        if self.authorization_id is not None:
            _digest(self.authorization_id, "authorization_id")
        for value, name in (
            (self.authorization_reference, "authorization_reference"),
            (self.enforcement_request_id, "enforcement_request_id"),
            (self.lifecycle_state, "lifecycle_state"),
            (self.consumption_result, "consumption_result"),
            (self.policy_reference, "policy_reference"),
            (self.enforcement_point_id, "enforcement_point_id"),
            (self.correlation_id, "correlation_id"),
        ):
            _id(value, name)
        if (not isinstance(self.enforcement_state, ContinuedOperationEnforcementState) or
                type(self.reason_codes) is not tuple or not self.reason_codes or
                any(not isinstance(item, ContinuedOperationEnforcementReasonCode)
                    for item in self.reason_codes) or
                len(set(self.reason_codes)) != len(self.reason_codes)):
            raise ContinuedOperationEnforcementError("enforcement evidence is invalid.")
        if self.previous_consumption_reference is not None:
            _digest(self.previous_consumption_reference, "previous_consumption_reference")
        if self.schema_version != CONTINUED_OPERATION_ENFORCEMENT_CONTRACT_VERSION:
            raise ContinuedOperationEnforcementError("enforcement evidence version is unsupported.")
        object.__setattr__(self, "decided_at", _time(self.decided_at, "decided_at"))


@dataclass(frozen=True, slots=True)
class AtomicConsumptionResult:
    state: AtomicConsumptionState
    record: ContinuedOperationConsumptionRecord | None
    previous_record: ContinuedOperationConsumptionRecord | None = None
    lifecycle_reason: ContinuedOperationEnforcementReasonCode | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.state, AtomicConsumptionState):
            raise ContinuedOperationEnforcementError("atomic consumption result is invalid.")
        has_record = type(self.record) is ContinuedOperationConsumptionRecord
        if (self.state in {AtomicConsumptionState.CONSUMED, AtomicConsumptionState.IDEMPOTENT}) != has_record:
            raise ContinuedOperationEnforcementError("atomic consumption result is inconsistent.")
        if (self.previous_record is not None and
                type(self.previous_record) is not ContinuedOperationConsumptionRecord):
            raise ContinuedOperationEnforcementError("atomic consumption result is invalid.")
        if (self.lifecycle_reason is not None and
                not isinstance(self.lifecycle_reason, ContinuedOperationEnforcementReasonCode)):
            raise ContinuedOperationEnforcementError("atomic consumption result is invalid.")


@dataclass(frozen=True, slots=True)
class ContinuedOperationEnforcementResult:
    authorization_id: str | None
    enforcement_request_id: str
    deployment_id: str
    purpose: str
    enforcement_state: ContinuedOperationEnforcementState
    reason_codes: tuple[ContinuedOperationEnforcementReasonCode, ...]
    decided_at: datetime
    request_binding_digest: str
    evidence: ContinuedOperationEnforcementEvidence
    consumption_record: ContinuedOperationConsumptionRecord | None = None
    idempotent: bool = False

    def __post_init__(self) -> None:
        if self.authorization_id is not None:
            _digest(self.authorization_id, "authorization_id")
        _id(self.enforcement_request_id, "enforcement_request_id")
        _id(self.deployment_id, "deployment_id")
        _id(self.purpose, "purpose")
        _digest(self.request_binding_digest, "request_binding_digest")
        if (not isinstance(self.enforcement_state, ContinuedOperationEnforcementState) or
                type(self.reason_codes) is not tuple or not self.reason_codes or
                any(not isinstance(item, ContinuedOperationEnforcementReasonCode)
                    for item in self.reason_codes) or
                len(set(self.reason_codes)) != len(self.reason_codes) or
                type(self.evidence) is not ContinuedOperationEnforcementEvidence or
                type(self.idempotent) is not bool):
            raise ContinuedOperationEnforcementError("enforcement result is invalid.")
        permitted = self.enforcement_state is ContinuedOperationEnforcementState.PERMITTED
        if permitted != (type(self.consumption_record) is ContinuedOperationConsumptionRecord):
            raise ContinuedOperationEnforcementError("enforcement result is inconsistent.")
        if (self.idempotent and not permitted) or self.evidence.enforcement_state is not self.enforcement_state:
            raise ContinuedOperationEnforcementError("enforcement result is inconsistent.")
        if self.evidence.reason_codes != self.reason_codes:
            raise ContinuedOperationEnforcementError("enforcement result is inconsistent.")
        object.__setattr__(self, "decided_at", _time(self.decided_at, "decided_at"))

    @property
    def permitted(self) -> bool:
        return (self.enforcement_state is ContinuedOperationEnforcementState.PERMITTED and
                self.consumption_record is not None)


class PublicContinuedOperationEnforcementV1(PublicContractModel):
    schema_version: str = CONTINUED_OPERATION_ENFORCEMENT_CONTRACT_VERSION
    authorization_id: str | None = None
    enforcement_request_id: str = Field(min_length=1)
    deployment_id: str = Field(min_length=1)
    purpose: str = Field(min_length=1)
    enforcement_state: ContinuedOperationEnforcementState
    reason_codes: tuple[ContinuedOperationEnforcementReasonCode, ...]
    decided_at: datetime
    consumed_at: datetime | None = None
    evidence_reference: str | None = None
    correlation_id: str | None = None


class ContinuedOperationAuthorizationRepository(Protocol):
    def get(self, reference: str) -> StoredContinuedOperationAuthorization | None: ...


class ContinuedOperationConsumptionLedger(Protocol):
    def consume(
        self, *, authorization: StoredContinuedOperationAuthorization,
        request: ContinuedOperationEnforcementRequest, request_binding_digest: str,
        consumed_at: datetime,
        lifecycle_recheck: Callable[[], ContinuedOperationEnforcementReasonCode | None],
        record_factory: Callable[[str], ContinuedOperationConsumptionRecord],
    ) -> AtomicConsumptionResult: ...


__all__ = [name for name in globals() if name.startswith("ContinuedOperation") or
           name.startswith("StoredContinued") or name.startswith("AtomicConsumption") or
           name.startswith("PublicContinued")]
__all__ += ["CONTINUED_OPERATION_ENFORCEMENT_CONTRACT_VERSION",
            "CONTINUED_OPERATION_ENFORCEMENT_DIGEST_ALGORITHM"]
