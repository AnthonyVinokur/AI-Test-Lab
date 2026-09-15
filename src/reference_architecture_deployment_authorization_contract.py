from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from src.reference_architecture_policy_decision_contract import (
    decision_digest, decision_identifier, decision_signature, decision_utc,
)


AUTHORIZATION_CONTRACT_VERSION = "1.0"
AUTHORIZATION_SERIALIZATION_ALGORITHM = "canonical-json-rfc8259"
AUTHORIZATION_DIGEST_ALGORITHM = "sha256"


class AuthorizationState(str, Enum):
    AUTHORIZED = "authorized"
    DENIED = "denied"
    INDETERMINATE = "indeterminate"
    INVALID = "invalid"


class AuthorizationLifecycleState(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    SUPERSEDED = "superseded"
    INVALID = "invalid"


class AuthorizationEventType(str, Enum):
    ISSUED = "issued"
    REVOKED = "revoked"
    SUPERSEDED = "superseded"


@dataclass(frozen=True, slots=True)
class DeploymentContext:
    artifact_id: str
    artifact_digest: str
    tenant_id: str
    environment: str
    release_id: str
    scope: str
    conditions: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        decision_identifier(self.artifact_id, "artifact_id")
        decision_digest(self.artifact_digest, "artifact_digest")
        for value, name in ((self.tenant_id, "tenant_id"), (self.environment, "environment"),
                            (self.release_id, "release_id"), (self.scope, "scope")):
            decision_identifier(value, name)
        if not isinstance(self.conditions, tuple) or len(self.conditions) != len(set(self.conditions)):
            raise ValueError("conditions must be a duplicate-free tuple.")
        for item in self.conditions:
            decision_identifier(item, "condition")


@dataclass(frozen=True, slots=True)
class AuthorizationPolicyReference:
    policy_id: str
    version: str
    digest: str

    def __post_init__(self) -> None:
        decision_identifier(self.policy_id, "authorization_policy_id")
        decision_identifier(self.version, "authorization_policy_version")
        decision_digest(self.digest, "authorization_policy_digest")


@dataclass(frozen=True, slots=True)
class DeploymentAuthorizationRequest:
    request_id: str
    decision_attestation_id: str
    approval_attestation_id: str
    context: DeploymentContext
    authorization_policy: AuthorizationPolicyReference
    requested_at: datetime
    correlation_id: str
    contract_version: str = AUTHORIZATION_CONTRACT_VERSION

    def __post_init__(self) -> None:
        decision_identifier(self.request_id, "request_id")
        decision_digest(self.decision_attestation_id, "decision_attestation_id")
        decision_digest(self.approval_attestation_id, "approval_attestation_id")
        if not isinstance(self.context, DeploymentContext):
            raise ValueError("context is invalid.")
        if not isinstance(self.authorization_policy, AuthorizationPolicyReference):
            raise ValueError("authorization_policy is invalid.")
        object.__setattr__(self, "requested_at", decision_utc(self.requested_at, "requested_at"))
        decision_identifier(self.correlation_id, "correlation_id")
        if self.contract_version != AUTHORIZATION_CONTRACT_VERSION:
            raise ValueError("contract_version is unsupported.")


@dataclass(frozen=True, slots=True)
class AuthorizationPolicy:
    policy_id: str
    version: str
    accepted_decision_versions: frozenset[str]
    accepted_approval_versions: frozenset[str]
    allowed_environments: frozenset[str]
    allowed_tenants: frozenset[str]
    maximum_decision_age_seconds: int
    maximum_approval_age_seconds: int
    minimum_remaining_lifetime_seconds: int
    required_conditions: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        decision_identifier(self.policy_id, "policy_id")
        decision_identifier(self.version, "version")
        for values, name in ((self.accepted_decision_versions, "accepted_decision_versions"),
                             (self.accepted_approval_versions, "accepted_approval_versions"),
                             (self.allowed_environments, "allowed_environments"),
                             (self.allowed_tenants, "allowed_tenants")):
            if not isinstance(values, frozenset) or not values:
                raise ValueError(f"{name} must be a non-empty frozenset.")
            for item in values:
                decision_identifier(item, name)
        for value, name in ((self.maximum_decision_age_seconds, "maximum_decision_age_seconds"),
                            (self.maximum_approval_age_seconds, "maximum_approval_age_seconds"),
                            (self.minimum_remaining_lifetime_seconds, "minimum_remaining_lifetime_seconds")):
            if type(value) is not int or value < 0:
                raise ValueError(f"{name} must be a non-negative integer.")
        for item in self.required_conditions:
            decision_identifier(item, "required_condition")


@dataclass(frozen=True, slots=True)
class VerifiedDecisionReference:
    attestation_id: str
    attestation_digest: str
    artifact_id: str
    policy_id: str
    policy_version: str
    policy_digest: str
    artifact_digest: str
    tenant_id: str
    environment: str
    evidence_references: tuple[str, ...]
    decided_at: datetime
    expires_at: datetime
    contract_version: str


@dataclass(frozen=True, slots=True)
class VerifiedApprovalReference:
    approval_id: str
    approval_digest: str
    decision_attestation_id: str
    artifact_digest: str
    tenant_id: str
    environment: str
    release_id: str
    scope: str
    conditions: tuple[str, ...]
    issued_at: datetime
    valid_from: datetime
    expires_at: datetime
    contract_version: str


@dataclass(frozen=True, slots=True)
class AuthorizationOutcome:
    state: AuthorizationState
    reason_code: str
    valid_from: datetime | None = None
    expires_at: datetime | None = None
    preserved_conditions: tuple[str, ...] = ()

    @property
    def authorized(self) -> bool:
        return self.state is AuthorizationState.AUTHORIZED


@dataclass(frozen=True, slots=True)
class DeploymentAuthorizationAttestation:
    authorization_id: str
    outcome: AuthorizationState
    artifact_id: str
    artifact_digest: str
    release_id: str
    tenant_id: str
    environment: str
    scope: str
    decision_attestation_id: str
    decision_attestation_digest: str
    approval_attestation_id: str
    approval_attestation_digest: str
    authorization_policy_id: str
    authorization_policy_version: str
    authorization_policy_digest: str
    conditions: tuple[str, ...]
    issued_at: datetime
    valid_from: datetime
    expires_at: datetime
    issuer_id: str
    key_id: str
    correlation_id: str
    payload_digest: str
    signature: str
    contract_version: str = AUTHORIZATION_CONTRACT_VERSION
    serialization_algorithm: str = AUTHORIZATION_SERIALIZATION_ALGORITHM
    digest_algorithm: str = AUTHORIZATION_DIGEST_ALGORITHM

    def __post_init__(self) -> None:
        for value, name in ((self.authorization_id, "authorization_id"),
                            (self.artifact_digest, "artifact_digest"),
                            (self.decision_attestation_id, "decision_attestation_id"),
                            (self.decision_attestation_digest, "decision_attestation_digest"),
                            (self.approval_attestation_id, "approval_attestation_id"),
                            (self.approval_attestation_digest, "approval_attestation_digest"),
                            (self.authorization_policy_digest, "authorization_policy_digest"),
                            (self.payload_digest, "payload_digest")):
            decision_digest(value, name)
        for value, name in ((self.artifact_id, "artifact_id"), (self.release_id, "release_id"),
                            (self.tenant_id, "tenant_id"), (self.environment, "environment"),
                            (self.scope, "scope"), (self.authorization_policy_id, "authorization_policy_id"),
                            (self.authorization_policy_version, "authorization_policy_version"),
                            (self.issuer_id, "issuer_id"), (self.key_id, "key_id"),
                            (self.correlation_id, "correlation_id")):
            decision_identifier(value, name)
        decision_signature(self.signature, "signature")
        if self.outcome is not AuthorizationState.AUTHORIZED:
            raise ValueError("only authorized outcomes may be attested.")
        for name in ("issued_at", "valid_from", "expires_at"):
            object.__setattr__(self, name, decision_utc(getattr(self, name), name))
        if not self.issued_at <= self.valid_from < self.expires_at:
            raise ValueError("authorization validity window is invalid.")


@dataclass(frozen=True, slots=True)
class AuthorizationLifecycleRecord:
    record_id: str
    authorization_id: str
    event_type: AuthorizationEventType
    actor_id: str
    reason_code: str
    occurred_at: datetime
    previous_record_id: str | None


@dataclass(frozen=True, slots=True)
class AuthorizationVerificationResult:
    valid: bool
    active: bool
    applicable: bool
    authorization_id: str | None
    lifecycle_state: AuthorizationLifecycleState
    reason_code: str
    artifact_digest: str | None
    environment: str | None
    conditions: tuple[str, ...]
    expires_at: datetime | None


@dataclass(frozen=True, slots=True)
class PublicAuthorizationResult:
    authorized: bool
    outcome: AuthorizationState
    reason_code: str
    authorization_id: str | None
    contract_version: str
    artifact_id: str | None
    artifact_digest: str | None
    environment: str | None
    issued_at: datetime | None
    expires_at: datetime | None
