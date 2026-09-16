"""ATL-A.29 protected-operation outcome settlement contracts."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Protocol

from pydantic import Field

from src.public_contract import PublicContractModel
from src.reference_architecture_continued_operation_reconciliation_contract import (
    AuthoritativeExecutionEvidence,
    ContinuedOperationReconciliationAttestation,
)
from src.reference_architecture_deployment_execution_contract import digest, identifier, utc


CONTINUED_OPERATION_SETTLEMENT_CONTRACT_VERSION = "1.0"
CONTINUED_OPERATION_SETTLEMENT_EVIDENCE_VERSION = "1.0"


class ContinuedOperationSettlementError(ValueError):
    """Normalized ATL-A.29 contract error."""


class ProtectedOperationSettlementStatus(str, Enum):
    SETTLED_SUCCESS = "settled_success"
    SETTLED_FAILURE = "settled_failure"
    SUSPENDED = "suspended"
    REJECTED = "rejected"


class SettlementReasonCode(str, Enum):
    EXPECTED_POSTCONDITION_VERIFIED = "EXPECTED_POSTCONDITION_VERIFIED"
    EXPECTED_POSTCONDITION_MISMATCH = "EXPECTED_POSTCONDITION_MISMATCH"
    VERIFICATION_INDETERMINATE = "VERIFICATION_INDETERMINATE"
    VERIFICATION_EVIDENCE_INVALID = "VERIFICATION_EVIDENCE_INVALID"
    VERIFICATION_EVIDENCE_EXPIRED = "VERIFICATION_EVIDENCE_EXPIRED"
    LIFECYCLE_BINDING_MISMATCH = "LIFECYCLE_BINDING_MISMATCH"
    SETTLEMENT_POLICY_NOT_FOUND = "SETTLEMENT_POLICY_NOT_FOUND"
    SETTLEMENT_POLICY_NOT_ALLOWED = "SETTLEMENT_POLICY_NOT_ALLOWED"
    SETTLEMENT_ALREADY_COMMITTED = "SETTLEMENT_ALREADY_COMMITTED"
    CONFLICTING_SETTLEMENT = "CONFLICTING_SETTLEMENT"
    UPSTREAM_EVIDENCE_MISSING = "UPSTREAM_EVIDENCE_MISSING"
    UPSTREAM_EVIDENCE_INVALID = "UPSTREAM_EVIDENCE_INVALID"
    SETTLEMENT_COMMIT_INDETERMINATE = "SETTLEMENT_COMMIT_INDETERMINATE"
    SETTLEMENT_REPOSITORY_UNAVAILABLE = "SETTLEMENT_REPOSITORY_UNAVAILABLE"
    UNTRUSTED_TIME_SOURCE = "UNTRUSTED_TIME_SOURCE"


class SettlementClaimState(str, Enum):
    NEW = "new"
    REPLAY = "replay"
    CONFLICT = "conflict"
    IN_PROGRESS = "in_progress"
    UNAVAILABLE = "unavailable"


def _id(value: object, name: str) -> str:
    try:
        return identifier(value, name)
    except ValueError:
        raise ContinuedOperationSettlementError(f"{name} is invalid.") from None


def _digest(value: object, name: str) -> str:
    try:
        return digest(value, name)
    except ValueError:
        raise ContinuedOperationSettlementError(f"{name} is invalid.") from None


def _time(value: object, name: str) -> datetime:
    try:
        return utc(value, name)
    except (ValueError, OverflowError):
        raise ContinuedOperationSettlementError(f"{name} is invalid.") from None


def _ids(values: object, name: str, *, empty: bool = False) -> tuple[str, ...]:
    if type(values) is not tuple or (not values and not empty):
        raise ContinuedOperationSettlementError(f"{name} is invalid.")
    if len(values) != len(set(values)):
        raise ContinuedOperationSettlementError(f"{name} is invalid.")
    for value in values:
        _id(value, name)
    return values


@dataclass(frozen=True, slots=True)
class ProtectedOperationSettlementRequest:
    settlement_request_id: str
    deployment_id: str
    operation_id: str
    execution_id: str
    verification_id: str
    verification_evidence_digest: str
    settlement_policy_id: str
    settlement_policy_version: str
    requested_at: datetime
    requester_id: str
    correlation_id: str
    schema_version: str = CONTINUED_OPERATION_SETTLEMENT_CONTRACT_VERSION

    def __post_init__(self) -> None:
        for value, name in (
            (self.settlement_request_id, "settlement_request_id"),
            (self.deployment_id, "deployment_id"), (self.operation_id, "operation_id"),
            (self.execution_id, "execution_id"), (self.requester_id, "requester_id"),
            (self.correlation_id, "correlation_id"),
            (self.settlement_policy_id, "settlement_policy_id"),
            (self.settlement_policy_version, "settlement_policy_version"),
        ):
            _id(value, name)
        _digest(self.verification_id, "verification_id")
        _digest(self.verification_evidence_digest, "verification_evidence_digest")
        object.__setattr__(self, "requested_at", _time(self.requested_at, "requested_at"))
        if self.schema_version != CONTINUED_OPERATION_SETTLEMENT_CONTRACT_VERSION:
            raise ContinuedOperationSettlementError("settlement schema version is unsupported.")


@dataclass(frozen=True, slots=True)
class ProtectedOperationSettlementPolicy:
    policy_id: str
    version: str
    allowed_verification_policy_ids: tuple[str, ...]
    maximum_verification_age_seconds: int
    mismatch_is_terminal: bool
    indeterminate_requires_review: bool
    require_execution_attestation: bool
    require_complete_evidence_chain: bool

    def __post_init__(self) -> None:
        _id(self.policy_id, "settlement_policy_id")
        _id(self.version, "settlement_policy_version")
        _ids(self.allowed_verification_policy_ids, "allowed_verification_policy_ids")
        if (type(self.maximum_verification_age_seconds) is not int or
                self.maximum_verification_age_seconds < 0):
            raise ContinuedOperationSettlementError(
                "maximum_verification_age_seconds is invalid."
            )
        for value in (
            self.mismatch_is_terminal, self.indeterminate_requires_review,
            self.require_execution_attestation, self.require_complete_evidence_chain,
        ):
            if type(value) is not bool:
                raise ContinuedOperationSettlementError("settlement policy is invalid.")


@dataclass(frozen=True, slots=True)
class AuthoritativeVerificationEvidence:
    attestation: ContinuedOperationReconciliationAttestation
    execution_evidence: AuthoritativeExecutionEvidence | None
    committed: bool

    def __post_init__(self) -> None:
        if (type(self.attestation) is not ContinuedOperationReconciliationAttestation or
                (self.execution_evidence is not None and
                 type(self.execution_evidence) is not AuthoritativeExecutionEvidence) or
                type(self.committed) is not bool):
            raise ContinuedOperationSettlementError("verification evidence is invalid.")


@dataclass(frozen=True, slots=True)
class ProtectedOperationSettlementEvidence:
    settlement_id: str
    settlement_status: ProtectedOperationSettlementStatus
    deployment_id: str
    operation_id: str
    execution_id: str
    verification_id: str
    enforcement_evidence_digest: str
    execution_evidence_digest: str
    verification_evidence_digest: str
    settlement_policy_id: str
    settlement_policy_version: str
    reason_code: SettlementReasonCode
    settled_at: datetime
    evidence_digest: str
    signature: str
    contract_version: str = CONTINUED_OPERATION_SETTLEMENT_EVIDENCE_VERSION

    def __post_init__(self) -> None:
        for value, name in (
            (self.settlement_id, "settlement_id"), (self.verification_id, "verification_id"),
            (self.enforcement_evidence_digest, "enforcement_evidence_digest"),
            (self.execution_evidence_digest, "execution_evidence_digest"),
            (self.verification_evidence_digest, "verification_evidence_digest"),
            (self.evidence_digest, "evidence_digest"), (self.signature, "signature"),
        ):
            _digest(value, name)
        for value, name in (
            (self.deployment_id, "deployment_id"), (self.operation_id, "operation_id"),
            (self.execution_id, "execution_id"),
            (self.settlement_policy_id, "settlement_policy_id"),
            (self.settlement_policy_version, "settlement_policy_version"),
        ):
            _id(value, name)
        if (not isinstance(self.settlement_status, ProtectedOperationSettlementStatus) or
                not isinstance(self.reason_code, SettlementReasonCode)):
            raise ContinuedOperationSettlementError("settlement evidence is invalid.")
        object.__setattr__(self, "settled_at", _time(self.settled_at, "settled_at"))
        if self.contract_version != CONTINUED_OPERATION_SETTLEMENT_EVIDENCE_VERSION:
            raise ContinuedOperationSettlementError("settlement evidence version is unsupported.")


@dataclass(frozen=True, slots=True)
class ProtectedOperationSettlementResult:
    settlement_request_id: str
    status: ProtectedOperationSettlementStatus
    reason_code: SettlementReasonCode
    evaluated_at: datetime
    evidence: ProtectedOperationSettlementEvidence | None = None
    committed: bool = False
    idempotent: bool = False

    def __post_init__(self) -> None:
        _id(self.settlement_request_id, "settlement_request_id")
        if (not isinstance(self.status, ProtectedOperationSettlementStatus) or
                not isinstance(self.reason_code, SettlementReasonCode) or
                type(self.committed) is not bool or type(self.idempotent) is not bool):
            raise ContinuedOperationSettlementError("settlement result is invalid.")
        if self.evidence is not None and type(self.evidence) is not ProtectedOperationSettlementEvidence:
            raise ContinuedOperationSettlementError("settlement result is invalid.")
        if self.committed != (self.evidence is not None):
            raise ContinuedOperationSettlementError("settlement commit state is invalid.")
        object.__setattr__(self, "evaluated_at", _time(self.evaluated_at, "evaluated_at"))


@dataclass(frozen=True, slots=True)
class AtomicSettlementClaim:
    state: SettlementClaimState
    result: ProtectedOperationSettlementResult | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.state, SettlementClaimState):
            raise ContinuedOperationSettlementError("settlement claim state is invalid.")
        if self.result is not None and type(self.result) is not ProtectedOperationSettlementResult:
            raise ContinuedOperationSettlementError("settlement claim result is invalid.")


class PublicProtectedOperationSettlementV1(PublicContractModel):
    schema_version: str = CONTINUED_OPERATION_SETTLEMENT_CONTRACT_VERSION
    settlement_id: str | None = None
    settlement_request_id: str = Field(min_length=1)
    deployment_id: str = Field(min_length=1)
    operation_id: str = Field(min_length=1)
    execution_id: str = Field(min_length=1)
    verification_id: str = Field(min_length=1)
    status: ProtectedOperationSettlementStatus
    reason_code: SettlementReasonCode
    settled_at: datetime | None = None
    committed: bool
    idempotent: bool


class VerificationEvidenceRepository(Protocol):
    def get_committed(self, verification_id: str) -> AuthoritativeVerificationEvidence | None: ...


class SettlementPolicyRepository(Protocol):
    def get(self, policy_id: str, version: str) -> ProtectedOperationSettlementPolicy | None: ...


class SettlementEvidenceRepository(Protocol):
    def claim(
        self, *, lifecycle_key: str, settlement_request_id: str, request_digest: str,
    ) -> AtomicSettlementClaim: ...

    def commit(
        self, *, lifecycle_key: str, settlement_request_id: str, request_digest: str,
        result: ProtectedOperationSettlementResult,
    ) -> None: ...


class SettlementSigner(Protocol):
    def sign(self, payload: bytes) -> str: ...
    def verify(self, payload: bytes, signature: str) -> bool: ...


__all__ = [name for name in globals() if name.startswith("ProtectedOperation") or
           name.startswith("Settlement") or name.startswith("AuthoritativeVerification") or
           name.startswith("AtomicSettlement") or name.startswith("PublicProtected") or
           name.startswith("VerificationEvidence") or name.startswith("ContinuedOperation")]
__all__ += ["CONTINUED_OPERATION_SETTLEMENT_CONTRACT_VERSION",
            "CONTINUED_OPERATION_SETTLEMENT_EVIDENCE_VERSION"]
