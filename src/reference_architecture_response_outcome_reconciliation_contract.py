"""ATL-A.31 authorized-response outcome reconciliation contracts."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Protocol

from pydantic import Field

from src.public_contract import PublicContractModel
from src.reference_architecture_continued_operation_response_contract import ResponseAuthorizationEvidence
from src.reference_architecture_deployment_execution_contract import digest, identifier, utc
from src.reference_architecture_deployment_recovery_contract import (
    PostRemediationVerification,
    RecoveryDecision,
    RecoveryExecutionAttestation,
)


RESPONSE_RECONCILIATION_CONTRACT_VERSION = "1.0"
RESPONSE_RECONCILIATION_EVIDENCE_VERSION = "1.0"


class ResponseOutcomeReconciliationError(ValueError):
    """Normalized fail-closed ATL-A.31 boundary error."""


class ReconciliationOutcome(str, Enum):
    VERIFIED_RECOVERY = "verified_recovery"
    RESPONSE_FAILED = "response_failed"
    RESPONSE_INDETERMINATE = "response_indeterminate"
    EXPIRED_UNEXECUTED = "expired_unexecuted"
    REJECTED = "rejected"


class ReconciliationReasonCode(str, Enum):
    RECOVERY_INDEPENDENTLY_VERIFIED = "RECOVERY_INDEPENDENTLY_VERIFIED"
    RECOVERY_VERIFICATION_FAILED = "RECOVERY_VERIFICATION_FAILED"
    RECOVERY_VERIFICATION_INCONCLUSIVE = "RECOVERY_VERIFICATION_INCONCLUSIVE"
    AUTHORIZATION_EXPIRED_UNEXECUTED = "AUTHORIZATION_EXPIRED_UNEXECUTED"
    AUTHORIZATION_NOT_FOUND = "AUTHORIZATION_NOT_FOUND"
    AUTHORIZATION_INVALID = "AUTHORIZATION_INVALID"
    REMEDIATION_DECISION_INVALID = "REMEDIATION_DECISION_INVALID"
    EXECUTION_EVIDENCE_INVALID = "EXECUTION_EVIDENCE_INVALID"
    VERIFICATION_EVIDENCE_INVALID = "VERIFICATION_EVIDENCE_INVALID"
    LINEAGE_MISMATCH = "LINEAGE_MISMATCH"
    CAPABILITY_MISMATCH = "CAPABILITY_MISMATCH"
    SCOPE_EXPANSION = "SCOPE_EXPANSION"
    CONSTRAINTS_WEAKENED = "CONSTRAINTS_WEAKENED"
    MANIFEST_MISMATCH = "MANIFEST_MISMATCH"
    ATTEMPT_LIMIT_EXCEEDED = "ATTEMPT_LIMIT_EXCEEDED"
    EXECUTION_AFTER_EXPIRY = "EXECUTION_AFTER_EXPIRY"
    POLICY_NOT_FOUND = "POLICY_NOT_FOUND"
    POLICY_INVALID = "POLICY_INVALID"
    IDEMPOTENCY_CONFLICT = "IDEMPOTENCY_CONFLICT"
    RECONCILIATION_IN_PROGRESS = "RECONCILIATION_IN_PROGRESS"
    REPOSITORY_UNAVAILABLE = "REPOSITORY_UNAVAILABLE"
    COMMIT_INDETERMINATE = "COMMIT_INDETERMINATE"
    UNTRUSTED_TIME_SOURCE = "UNTRUSTED_TIME_SOURCE"


class ReconciliationClaimState(str, Enum):
    NEW = "new"
    REPLAY = "replay"
    CONFLICT = "conflict"
    IN_PROGRESS = "in_progress"
    UNAVAILABLE = "unavailable"


def _id(value: object, name: str) -> str:
    try:
        return identifier(value, name)
    except ValueError:
        raise ResponseOutcomeReconciliationError(f"{name} is invalid.") from None


def _digest(value: object, name: str) -> str:
    try:
        return digest(value, name)
    except ValueError:
        raise ResponseOutcomeReconciliationError(f"{name} is invalid.") from None


def _time(value: object, name: str) -> datetime:
    try:
        return utc(value, name)
    except (ValueError, OverflowError):
        raise ResponseOutcomeReconciliationError(f"{name} is invalid.") from None


def _ids(values: object, name: str, *, empty: bool = False) -> tuple[str, ...]:
    if type(values) is not tuple or (not values and not empty) or len(values) != len(set(values)):
        raise ResponseOutcomeReconciliationError(f"{name} is invalid.")
    for value in values:
        _id(value, name)
    return values


@dataclass(frozen=True, slots=True)
class ResponseOutcomeReconciliationRequest:
    request_id: str
    idempotency_key: str
    response_authorization_id: str
    remediation_decision_id: str
    execution_attestation_id: str
    post_remediation_verification_id: str
    reconciliation_policy_version: str
    requested_at: datetime
    schema_version: str = RESPONSE_RECONCILIATION_CONTRACT_VERSION

    def __post_init__(self) -> None:
        _id(self.request_id, "request_id")
        _id(self.idempotency_key, "idempotency_key")
        _digest(self.response_authorization_id, "response_authorization_id")
        _id(self.remediation_decision_id, "remediation_decision_id")
        _id(self.execution_attestation_id, "execution_attestation_id")
        _id(self.post_remediation_verification_id, "post_remediation_verification_id")
        _id(self.reconciliation_policy_version, "reconciliation_policy_version")
        object.__setattr__(self, "requested_at", _time(self.requested_at, "requested_at"))
        if self.schema_version != RESPONSE_RECONCILIATION_CONTRACT_VERSION:
            raise ResponseOutcomeReconciliationError("reconciliation request version is unsupported.")


@dataclass(frozen=True, slots=True)
class ReconciliationPolicy:
    policy_id: str
    version: str
    required_atl_a21_policy_version: str
    closure_capability: str
    closure_handoff_lifetime_seconds: int

    def __post_init__(self) -> None:
        _id(self.policy_id, "policy_id")
        _id(self.version, "policy_version")
        _id(self.required_atl_a21_policy_version, "required_atl_a21_policy_version")
        _id(self.closure_capability, "closure_capability")
        if type(self.closure_handoff_lifetime_seconds) is not int or self.closure_handoff_lifetime_seconds <= 0:
            raise ResponseOutcomeReconciliationError("closure_handoff_lifetime_seconds is invalid.")


@dataclass(frozen=True, slots=True)
class AuthoritativeResponseAuthorizationRecord:
    evidence: ResponseAuthorizationEvidence
    committed: bool

    def __post_init__(self) -> None:
        if type(self.evidence) is not ResponseAuthorizationEvidence or type(self.committed) is not bool:
            raise ResponseOutcomeReconciliationError("response authorization record is invalid.")


@dataclass(frozen=True, slots=True)
class AuthoritativeRemediationDecisionRecord:
    remediation_decision_id: str
    decision_digest: str
    decision: RecoveryDecision
    response_authorization_id: str
    committed: bool

    def __post_init__(self) -> None:
        _id(self.remediation_decision_id, "remediation_decision_id")
        _digest(self.decision_digest, "decision_digest")
        _digest(self.response_authorization_id, "response_authorization_id")
        if type(self.decision) is not RecoveryDecision or type(self.committed) is not bool:
            raise ResponseOutcomeReconciliationError("remediation decision record is invalid.")


@dataclass(frozen=True, slots=True)
class AuthoritativeRemediationExecutionRecord:
    execution_attestation_id: str
    execution_digest: str
    execution: RecoveryExecutionAttestation
    response_authorization_id: str
    remediation_decision_id: str
    capability: str
    scope: tuple[str, ...]
    constraints: tuple[str, ...]
    manifest_digest: str
    attempt_number: int
    committed: bool

    def __post_init__(self) -> None:
        _id(self.execution_attestation_id, "execution_attestation_id")
        _digest(self.execution_digest, "execution_digest")
        _digest(self.response_authorization_id, "response_authorization_id")
        _id(self.remediation_decision_id, "remediation_decision_id")
        _id(self.capability, "capability")
        _ids(self.scope, "scope")
        _ids(self.constraints, "constraints", empty=True)
        _digest(self.manifest_digest, "manifest_digest")
        if type(self.execution) is not RecoveryExecutionAttestation or type(self.committed) is not bool:
            raise ResponseOutcomeReconciliationError("execution record is invalid.")
        if type(self.attempt_number) is not int or self.attempt_number <= 0:
            raise ResponseOutcomeReconciliationError("attempt_number is invalid.")


@dataclass(frozen=True, slots=True)
class AuthoritativePostRemediationVerificationRecord:
    post_remediation_verification_id: str
    verification_digest: str
    verification: PostRemediationVerification
    execution_attestation_id: str
    target_scope: tuple[str, ...]
    committed: bool

    def __post_init__(self) -> None:
        _id(self.post_remediation_verification_id, "post_remediation_verification_id")
        _digest(self.verification_digest, "verification_digest")
        _id(self.execution_attestation_id, "execution_attestation_id")
        _ids(self.target_scope, "target_scope")
        if type(self.verification) is not PostRemediationVerification or type(self.committed) is not bool:
            raise ResponseOutcomeReconciliationError("verification record is invalid.")


@dataclass(frozen=True, slots=True)
class ResponseOutcomeReconciliationEvidence:
    reconciliation_id: str
    request_id: str
    idempotency_key: str
    incident_id: str
    protected_operation_id: str
    settlement_id: str
    settlement_digest: str
    response_authorization_id: str
    response_authorization_digest: str
    remediation_decision_id: str
    remediation_decision_digest: str
    execution_attestation_id: str
    execution_attestation_digest: str
    post_remediation_verification_id: str
    post_remediation_verification_digest: str
    authorized_capability: str
    authorized_scope: tuple[str, ...]
    actual_capability: str
    actual_scope: tuple[str, ...]
    authorization_issued_at: datetime
    authorization_expires_at: datetime
    consumed_attempt: int
    maximum_attempts: int
    policy_id: str
    policy_version: str
    outcome: ReconciliationOutcome
    reason_codes: tuple[ReconciliationReasonCode, ...]
    closure_eligible: bool
    created_at: datetime
    evidence_digest: str
    signer_id: str
    signature: str
    schema_version: str = RESPONSE_RECONCILIATION_EVIDENCE_VERSION

    def __post_init__(self) -> None:
        for value, name in (
            (self.reconciliation_id, "reconciliation_id"), (self.incident_id, "incident_id"),
            (self.settlement_id, "settlement_id"), (self.settlement_digest, "settlement_digest"),
            (self.response_authorization_id, "response_authorization_id"),
            (self.response_authorization_digest, "response_authorization_digest"),
            (self.remediation_decision_digest, "remediation_decision_digest"),
            (self.execution_attestation_digest, "execution_attestation_digest"),
            (self.post_remediation_verification_digest, "post_remediation_verification_digest"),
            (self.evidence_digest, "evidence_digest"), (self.signature, "signature"),
        ):
            _digest(value, name)
        for value, name in (
            (self.request_id, "request_id"), (self.idempotency_key, "idempotency_key"),
            (self.protected_operation_id, "protected_operation_id"),
            (self.remediation_decision_id, "remediation_decision_id"),
            (self.execution_attestation_id, "execution_attestation_id"),
            (self.post_remediation_verification_id, "post_remediation_verification_id"),
            (self.authorized_capability, "authorized_capability"),
            (self.actual_capability, "actual_capability"), (self.policy_id, "policy_id"),
            (self.policy_version, "policy_version"), (self.signer_id, "signer_id"),
        ):
            _id(value, name)
        _ids(self.authorized_scope, "authorized_scope")
        _ids(self.actual_scope, "actual_scope")
        if not isinstance(self.outcome, ReconciliationOutcome):
            raise ResponseOutcomeReconciliationError("outcome is invalid.")
        if (type(self.reason_codes) is not tuple or not self.reason_codes or
                len(self.reason_codes) != len(set(self.reason_codes)) or
                any(not isinstance(item, ReconciliationReasonCode) for item in self.reason_codes)):
            raise ResponseOutcomeReconciliationError("reason_codes are invalid.")
        if type(self.closure_eligible) is not bool or self.closure_eligible != (
                self.outcome is ReconciliationOutcome.VERIFIED_RECOVERY):
            raise ResponseOutcomeReconciliationError("closure eligibility is inconsistent.")
        if (type(self.consumed_attempt) is not int or self.consumed_attempt < 0 or
                type(self.maximum_attempts) is not int or self.maximum_attempts <= 0):
            raise ResponseOutcomeReconciliationError("attempt information is invalid.")
        object.__setattr__(self, "authorization_issued_at", _time(self.authorization_issued_at, "authorization_issued_at"))
        object.__setattr__(self, "authorization_expires_at", _time(self.authorization_expires_at, "authorization_expires_at"))
        object.__setattr__(self, "created_at", _time(self.created_at, "created_at"))
        if self.authorization_expires_at <= self.authorization_issued_at or self.created_at < self.authorization_issued_at:
            raise ResponseOutcomeReconciliationError("reconciliation timestamps are invalid.")
        if self.schema_version != RESPONSE_RECONCILIATION_EVIDENCE_VERSION:
            raise ResponseOutcomeReconciliationError("reconciliation evidence version is unsupported.")


@dataclass(frozen=True, slots=True)
class IncidentClosureHandoff:
    handoff_id: str
    reconciliation_id: str
    reconciliation_digest: str
    incident_id: str
    settlement_id: str
    response_authorization_id: str
    remediation_decision_id: str
    execution_attestation_id: str
    post_remediation_verification_id: str
    closure_capability: str
    closure_scope: tuple[str, ...]
    required_atl_a21_policy_version: str
    expires_at: datetime
    handoff_digest: str
    signature: str

    def __post_init__(self) -> None:
        for value, name in (
            (self.handoff_id, "handoff_id"), (self.reconciliation_id, "reconciliation_id"),
            (self.reconciliation_digest, "reconciliation_digest"), (self.incident_id, "incident_id"),
            (self.settlement_id, "settlement_id"),
            (self.response_authorization_id, "response_authorization_id"),
            (self.handoff_digest, "handoff_digest"), (self.signature, "signature"),
        ):
            _digest(value, name)
        for value, name in (
            (self.remediation_decision_id, "remediation_decision_id"),
            (self.execution_attestation_id, "execution_attestation_id"),
            (self.post_remediation_verification_id, "post_remediation_verification_id"),
            (self.closure_capability, "closure_capability"),
            (self.required_atl_a21_policy_version, "required_atl_a21_policy_version"),
        ):
            _id(value, name)
        _ids(self.closure_scope, "closure_scope")
        object.__setattr__(self, "expires_at", _time(self.expires_at, "expires_at"))


@dataclass(frozen=True, slots=True)
class ReconciliationCommit:
    evidence: ResponseOutcomeReconciliationEvidence
    closure_handoff: IncidentClosureHandoff | None

    def __post_init__(self) -> None:
        if type(self.evidence) is not ResponseOutcomeReconciliationEvidence:
            raise ResponseOutcomeReconciliationError("reconciliation commit is invalid.")
        if self.closure_handoff is not None and type(self.closure_handoff) is not IncidentClosureHandoff:
            raise ResponseOutcomeReconciliationError("closure handoff is invalid.")
        if (self.closure_handoff is not None) != self.evidence.closure_eligible:
            raise ResponseOutcomeReconciliationError("reconciliation commit is inconsistent.")


@dataclass(frozen=True, slots=True)
class AtomicReconciliationClaim:
    state: ReconciliationClaimState
    commit: ReconciliationCommit | None = None


class PublicResponseOutcomeReconciliationV1(PublicContractModel):
    schema_version: str = RESPONSE_RECONCILIATION_CONTRACT_VERSION
    reconciliation_id: str = Field(min_length=64, max_length=64)
    incident_id: str = Field(min_length=64, max_length=64)
    outcome: ReconciliationOutcome
    reason_codes: tuple[ReconciliationReasonCode, ...]
    closure_eligible: bool
    policy_version: str = Field(min_length=1)
    created_at: datetime
    protected_operation_id: str = Field(min_length=1)
    settlement_id: str = Field(min_length=64, max_length=64)
    response_authorization_id: str = Field(min_length=64, max_length=64)
    remediation_decision_id: str = Field(min_length=1)
    execution_attestation_id: str = Field(min_length=1)
    post_remediation_verification_id: str = Field(min_length=1)


class ResponseAuthorizationRecordRepository(Protocol):
    def get(self, record_id: str) -> AuthoritativeResponseAuthorizationRecord | None: ...


class RemediationDecisionRecordRepository(Protocol):
    def get(self, record_id: str) -> AuthoritativeRemediationDecisionRecord | None: ...


class RemediationExecutionRecordRepository(Protocol):
    def get(self, record_id: str) -> AuthoritativeRemediationExecutionRecord | None: ...


class PostRemediationVerificationRecordRepository(Protocol):
    def get(self, record_id: str) -> AuthoritativePostRemediationVerificationRecord | None: ...


class ReconciliationPolicyRepository(Protocol):
    def get(self, version: str) -> ReconciliationPolicy | None: ...


class ResponseReconciliationRepository(Protocol):
    def claim(self, *, lifecycle_key: str, request_id: str, idempotency_key: str,
              request_digest: str) -> AtomicReconciliationClaim: ...
    def commit(self, *, lifecycle_key: str, request_id: str, idempotency_key: str,
               request_digest: str, value: ReconciliationCommit) -> None: ...
    def get_by_reconciliation_id(self, reconciliation_id: str) -> ReconciliationCommit | None: ...
    def get_handoff(self, handoff_id: str) -> IncidentClosureHandoff | None: ...


class ReconciliationSigner(Protocol):
    signer_id: str
    def sign(self, payload: bytes) -> str: ...
    def verify(self, payload: bytes, signature: str) -> bool: ...


__all__ = [name for name in globals() if not name.startswith("_")]
