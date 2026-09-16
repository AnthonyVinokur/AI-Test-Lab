"""ATL-A.30 settled-outcome response authorization contracts."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Protocol

from pydantic import Field

from src.public_contract import PublicContractModel
from src.reference_architecture_continued_operation_settlement_contract import (
    ProtectedOperationSettlementEvidence,
    ProtectedOperationSettlementStatus,
)
from src.reference_architecture_deployment_execution_contract import digest, identifier, utc


CONTINUED_OPERATION_RESPONSE_CONTRACT_VERSION = "1.0"
CONTINUED_OPERATION_RESPONSE_EVIDENCE_VERSION = "1.0"


class ContinuedOperationResponseError(ValueError):
    """Normalized fail-closed ATL-A.30 boundary error."""


class ResponseOutcome(str, Enum):
    AUTHORIZED = "authorized"
    MANUAL_REVIEW_REQUIRED = "manual_review_required"
    DEFERRED = "deferred"
    INELIGIBLE = "ineligible"
    REJECTED = "rejected"
    CONFLICT = "conflict"


class ResponseType(str, Enum):
    REMEDIATION = "remediation"
    CONTAINMENT = "containment"
    COMPENSATION = "compensation"
    ROLLBACK = "rollback"
    INVESTIGATION = "investigation"
    REVERIFICATION = "reverification"
    MANUAL_REVIEW = "manual_review"
    GOVERNANCE_ESCALATION = "governance_escalation"


class ResponseReasonCode(str, Enum):
    RESPONSE_AUTHORIZED = "RESPONSE_AUTHORIZED"
    MANUAL_REVIEW_REQUIRED = "MANUAL_REVIEW_REQUIRED"
    SETTLEMENT_SUCCESS_INELIGIBLE = "SETTLEMENT_SUCCESS_INELIGIBLE"
    SETTLEMENT_REJECTED = "SETTLEMENT_REJECTED"
    SETTLEMENT_NOT_FOUND = "SETTLEMENT_NOT_FOUND"
    SETTLEMENT_EVIDENCE_INVALID = "SETTLEMENT_EVIDENCE_INVALID"
    SETTLEMENT_BINDING_MISMATCH = "SETTLEMENT_BINDING_MISMATCH"
    RESPONSE_POLICY_NOT_FOUND = "RESPONSE_POLICY_NOT_FOUND"
    RESPONSE_POLICY_INVALID = "RESPONSE_POLICY_INVALID"
    RESPONSE_MANIFEST_NOT_FOUND = "RESPONSE_MANIFEST_NOT_FOUND"
    RESPONSE_MANIFEST_INVALID = "RESPONSE_MANIFEST_INVALID"
    RESPONSE_NOT_PERMITTED = "RESPONSE_NOT_PERMITTED"
    SCOPE_NOT_PERMITTED = "SCOPE_NOT_PERMITTED"
    REQUESTER_NOT_AUTHORIZED = "REQUESTER_NOT_AUTHORIZED"
    RESPONSE_CONFLICT = "RESPONSE_CONFLICT"
    RESPONSE_AUTHORIZATION_EXPIRED = "RESPONSE_AUTHORIZATION_EXPIRED"
    RESPONSE_IN_PROGRESS = "RESPONSE_IN_PROGRESS"
    RESPONSE_REPOSITORY_UNAVAILABLE = "RESPONSE_REPOSITORY_UNAVAILABLE"
    RESPONSE_COMMIT_INDETERMINATE = "RESPONSE_COMMIT_INDETERMINATE"
    UNTRUSTED_TIME_SOURCE = "UNTRUSTED_TIME_SOURCE"


class ResponseClaimState(str, Enum):
    NEW = "new"
    REPLAY = "replay"
    CONFLICT = "conflict"
    IN_PROGRESS = "in_progress"
    UNAVAILABLE = "unavailable"


def _id(value: object, name: str) -> str:
    try:
        return identifier(value, name)
    except ValueError:
        raise ContinuedOperationResponseError(f"{name} is invalid.") from None


def _digest(value: object, name: str) -> str:
    try:
        return digest(value, name)
    except ValueError:
        raise ContinuedOperationResponseError(f"{name} is invalid.") from None


def _time(value: object, name: str) -> datetime:
    try:
        return utc(value, name)
    except (ValueError, OverflowError):
        raise ContinuedOperationResponseError(f"{name} is invalid.") from None


def _ids(values: object, name: str, *, empty: bool = False) -> tuple[str, ...]:
    if type(values) is not tuple or (not values and not empty) or len(values) != len(set(values)):
        raise ContinuedOperationResponseError(f"{name} is invalid.")
    for value in values:
        _id(value, name)
    return values


@dataclass(frozen=True, slots=True)
class SettledOutcomeResponseRequest:
    response_request_id: str
    response_idempotency_key: str
    settlement_id: str
    settlement_digest: str
    policy_id: str
    policy_version: str
    policy_digest: str
    response_manifest_id: str
    response_manifest_version: str
    response_manifest_digest: str
    requested_response_type: ResponseType
    requested_scope: tuple[str, ...]
    requester_id: str
    requester_role: str
    requested_at: datetime
    correlation_id: str
    schema_version: str = CONTINUED_OPERATION_RESPONSE_CONTRACT_VERSION

    def __post_init__(self) -> None:
        for value, name in (
            (self.response_request_id, "response_request_id"),
            (self.response_idempotency_key, "response_idempotency_key"),
            (self.policy_id, "policy_id"), (self.policy_version, "policy_version"),
            (self.response_manifest_id, "response_manifest_id"),
            (self.response_manifest_version, "response_manifest_version"),
            (self.requester_id, "requester_id"), (self.requester_role, "requester_role"),
            (self.correlation_id, "correlation_id"),
        ):
            _id(value, name)
        for value, name in (
            (self.settlement_id, "settlement_id"), (self.settlement_digest, "settlement_digest"),
            (self.policy_digest, "policy_digest"),
            (self.response_manifest_digest, "response_manifest_digest"),
        ):
            _digest(value, name)
        if not isinstance(self.requested_response_type, ResponseType):
            raise ContinuedOperationResponseError("requested_response_type is invalid.")
        _ids(self.requested_scope, "requested_scope")
        object.__setattr__(self, "requested_at", _time(self.requested_at, "requested_at"))
        if self.schema_version != CONTINUED_OPERATION_RESPONSE_CONTRACT_VERSION:
            raise ContinuedOperationResponseError("response schema version is unsupported.")


@dataclass(frozen=True, slots=True)
class AuthoritativeSettlementRecord:
    evidence: ProtectedOperationSettlementEvidence
    committed: bool
    enforcement_request_id: str
    authorization_id: str
    original_scope: tuple[str, ...]

    def __post_init__(self) -> None:
        if type(self.evidence) is not ProtectedOperationSettlementEvidence or type(self.committed) is not bool:
            raise ContinuedOperationResponseError("settlement record is invalid.")
        _id(self.enforcement_request_id, "enforcement_request_id")
        _digest(self.authorization_id, "authorization_id")
        _ids(self.original_scope, "original_scope")


@dataclass(frozen=True, slots=True)
class ResponsePolicy:
    policy_id: str
    version: str
    permitted_failure_types: tuple[ResponseType, ...]
    permitted_suspended_types: tuple[ResponseType, ...]
    approved_manifest_references: tuple[str, ...]
    permitted_scopes: tuple[str, ...]
    authorized_roles: tuple[str, ...]
    maximum_authorization_seconds: int
    require_manual_review_for_suspended: bool = True

    def __post_init__(self) -> None:
        _id(self.policy_id, "policy_id"); _id(self.version, "policy_version")
        for values, name in ((self.permitted_failure_types, "permitted_failure_types"),
                             (self.permitted_suspended_types, "permitted_suspended_types")):
            if type(values) is not tuple or len(values) != len(set(values)) or any(not isinstance(v, ResponseType) for v in values):
                raise ContinuedOperationResponseError(f"{name} is invalid.")
        _ids(self.approved_manifest_references, "approved_manifest_references")
        _ids(self.permitted_scopes, "permitted_scopes")
        _ids(self.authorized_roles, "authorized_roles")
        if type(self.maximum_authorization_seconds) is not int or self.maximum_authorization_seconds <= 0:
            raise ContinuedOperationResponseError("maximum_authorization_seconds is invalid.")
        if type(self.require_manual_review_for_suspended) is not bool:
            raise ContinuedOperationResponseError("response policy is invalid.")


@dataclass(frozen=True, slots=True)
class ResponseManifest:
    manifest_id: str
    version: str
    response_type: ResponseType
    permitted_settlement_statuses: tuple[ProtectedOperationSettlementStatus, ...]
    remediation_capability: str
    required_evidence: tuple[str, ...]
    permitted_scopes: tuple[str, ...]
    prohibited_operations: tuple[str, ...]
    maximum_attempts: int
    lifetime_seconds: int
    required_roles: tuple[str, ...]
    constraints: tuple[str, ...]
    post_remediation_verification_required: bool

    def __post_init__(self) -> None:
        _id(self.manifest_id, "response_manifest_id"); _id(self.version, "response_manifest_version")
        if not isinstance(self.response_type, ResponseType):
            raise ContinuedOperationResponseError("response_type is invalid.")
        if (type(self.permitted_settlement_statuses) is not tuple or
                not self.permitted_settlement_statuses or
                len(self.permitted_settlement_statuses) != len(set(self.permitted_settlement_statuses)) or
                any(not isinstance(v, ProtectedOperationSettlementStatus) for v in self.permitted_settlement_statuses)):
            raise ContinuedOperationResponseError("permitted_settlement_statuses is invalid.")
        _id(self.remediation_capability, "remediation_capability")
        _ids(self.required_evidence, "required_evidence")
        _ids(self.permitted_scopes, "permitted_scopes")
        _ids(self.prohibited_operations, "prohibited_operations", empty=True)
        _ids(self.required_roles, "required_roles")
        _ids(self.constraints, "constraints", empty=True)
        if type(self.maximum_attempts) is not int or self.maximum_attempts <= 0:
            raise ContinuedOperationResponseError("maximum_attempts is invalid.")
        if type(self.lifetime_seconds) is not int or self.lifetime_seconds <= 0:
            raise ContinuedOperationResponseError("lifetime_seconds is invalid.")
        if type(self.post_remediation_verification_required) is not bool:
            raise ContinuedOperationResponseError("response manifest is invalid.")


@dataclass(frozen=True, slots=True)
class ResponseAuthorizationEvidence:
    response_authorization_id: str
    response_request_id: str
    response_idempotency_key: str
    settlement_id: str
    settlement_digest: str
    verification_id: str
    verification_evidence_digest: str
    execution_id: str
    execution_evidence_digest: str
    enforcement_request_id: str
    enforcement_evidence_digest: str
    authorization_id: str
    incident_id: str
    deployment_id: str
    operation_id: str
    settlement_status: ProtectedOperationSettlementStatus
    response_outcome: ResponseOutcome
    response_type: ResponseType
    response_manifest_id: str
    response_manifest_version: str
    response_manifest_digest: str
    remediation_capability: str
    policy_id: str
    policy_version: str
    policy_digest: str
    decision_reason_code: ResponseReasonCode
    scope: tuple[str, ...]
    constraints: tuple[str, ...]
    maximum_attempts: int
    expires_at: datetime
    created_at: datetime
    authorized_by: str
    authorization_digest: str
    signature: str
    schema_version: str = CONTINUED_OPERATION_RESPONSE_EVIDENCE_VERSION

    def __post_init__(self) -> None:
        for value, name in (
            (self.response_authorization_id, "response_authorization_id"),
            (self.settlement_id, "settlement_id"), (self.settlement_digest, "settlement_digest"),
            (self.verification_id, "verification_id"),
            (self.verification_evidence_digest, "verification_evidence_digest"),
            (self.execution_evidence_digest, "execution_evidence_digest"),
            (self.enforcement_evidence_digest, "enforcement_evidence_digest"),
            (self.authorization_id, "authorization_id"), (self.incident_id, "incident_id"),
            (self.response_manifest_digest, "response_manifest_digest"),
            (self.policy_digest, "policy_digest"),
            (self.authorization_digest, "authorization_digest"), (self.signature, "signature"),
        ):
            _digest(value, name)
        for value, name in (
            (self.response_request_id, "response_request_id"),
            (self.response_idempotency_key, "response_idempotency_key"),
            (self.execution_id, "execution_id"), (self.enforcement_request_id, "enforcement_request_id"),
            (self.deployment_id, "deployment_id"), (self.operation_id, "operation_id"),
            (self.response_manifest_id, "response_manifest_id"),
            (self.response_manifest_version, "response_manifest_version"),
            (self.remediation_capability, "remediation_capability"),
            (self.policy_id, "policy_id"), (self.policy_version, "policy_version"),
            (self.authorized_by, "authorized_by"),
        ):
            _id(value, name)
        if (not isinstance(self.settlement_status, ProtectedOperationSettlementStatus) or
                not isinstance(self.response_outcome, ResponseOutcome) or
                not isinstance(self.response_type, ResponseType) or
                not isinstance(self.decision_reason_code, ResponseReasonCode)):
            raise ContinuedOperationResponseError("response evidence is invalid.")
        _ids(self.scope, "scope"); _ids(self.constraints, "constraints", empty=True)
        if type(self.maximum_attempts) is not int or self.maximum_attempts <= 0:
            raise ContinuedOperationResponseError("maximum_attempts is invalid.")
        object.__setattr__(self, "expires_at", _time(self.expires_at, "expires_at"))
        object.__setattr__(self, "created_at", _time(self.created_at, "created_at"))
        if self.expires_at <= self.created_at:
            raise ContinuedOperationResponseError("response authorization expiry is invalid.")
        if self.schema_version != CONTINUED_OPERATION_RESPONSE_EVIDENCE_VERSION:
            raise ContinuedOperationResponseError("response evidence version is unsupported.")


@dataclass(frozen=True, slots=True)
class SettledOutcomeResponseResult:
    response_request_id: str
    outcome: ResponseOutcome
    reason_code: ResponseReasonCode
    decided_at: datetime
    evidence: ResponseAuthorizationEvidence | None = None
    committed: bool = False
    idempotent: bool = False

    def __post_init__(self) -> None:
        _id(self.response_request_id, "response_request_id")
        if (not isinstance(self.outcome, ResponseOutcome) or
                not isinstance(self.reason_code, ResponseReasonCode) or
                type(self.committed) is not bool or type(self.idempotent) is not bool):
            raise ContinuedOperationResponseError("response result is invalid.")
        if self.evidence is not None and type(self.evidence) is not ResponseAuthorizationEvidence:
            raise ContinuedOperationResponseError("response result is invalid.")
        if self.committed != (self.evidence is not None):
            raise ContinuedOperationResponseError("response commit state is invalid.")
        object.__setattr__(self, "decided_at", _time(self.decided_at, "decided_at"))


@dataclass(frozen=True, slots=True)
class AtomicResponseClaim:
    state: ResponseClaimState
    result: SettledOutcomeResponseResult | None = None


@dataclass(frozen=True, slots=True)
class AtlA20ResponseHandoff:
    response_authorization_id: str
    incident_id: str
    deployment_id: str
    artifact_digest: str
    action: str
    action_fingerprint: str
    scope: tuple[str, ...]
    constraints: tuple[str, ...]
    maximum_attempts: int
    expires_at: datetime
    authorization_digest: str
    signature: str

    def __post_init__(self) -> None:
        for value, name in ((self.response_authorization_id, "response_authorization_id"),
                            (self.incident_id, "incident_id"), (self.artifact_digest, "artifact_digest"),
                            (self.action_fingerprint, "action_fingerprint"),
                            (self.authorization_digest, "authorization_digest"), (self.signature, "signature")):
            _digest(value, name)
        _id(self.deployment_id, "deployment_id"); _id(self.action, "action")
        _ids(self.scope, "scope"); _ids(self.constraints, "constraints", empty=True)
        object.__setattr__(self, "expires_at", _time(self.expires_at, "expires_at"))


class PublicSettledOutcomeResponseV1(PublicContractModel):
    schema_version: str = CONTINUED_OPERATION_RESPONSE_CONTRACT_VERSION
    response_authorization_id: str | None = None
    response_request_id: str = Field(min_length=1)
    settlement_id: str = Field(min_length=1)
    incident_id: str | None = None
    outcome: ResponseOutcome
    response_type: ResponseType | None = None
    reason_code: ResponseReasonCode
    expires_at: datetime | None = None
    committed: bool
    idempotent: bool


class SettlementRecordRepository(Protocol):
    def get_committed(self, settlement_id: str) -> AuthoritativeSettlementRecord | None: ...


class ResponsePolicyRepository(Protocol):
    def get(self, policy_id: str, version: str) -> ResponsePolicy | None: ...


class ResponseManifestRepository(Protocol):
    def get(self, manifest_id: str, version: str) -> ResponseManifest | None: ...


class ResponseAuthorizationRepository(Protocol):
    def claim(self, *, lifecycle_key: str, response_request_id: str,
              idempotency_key: str, request_digest: str) -> AtomicResponseClaim: ...
    def commit(self, *, lifecycle_key: str, response_request_id: str,
               idempotency_key: str, request_digest: str,
               result: SettledOutcomeResponseResult) -> None: ...


class ResponseSigner(Protocol):
    def sign(self, payload: bytes) -> str: ...
    def verify(self, payload: bytes, signature: str) -> bool: ...


__all__ = [name for name in globals() if not name.startswith("_")]
