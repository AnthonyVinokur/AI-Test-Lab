from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from pydantic import Field

from src.public_contract import PublicContractModel
from src.reference_architecture_deployment_execution_contract import digest, identifier, utc


CONTINUED_OPERATION_AUTHORIZATION_CONTRACT_VERSION = "1.0"
CONTINUED_OPERATION_AUTHORIZATION_ALGORITHM = "ed25519"
CONTINUED_OPERATION_AUTHORIZATION_DIGEST_ALGORITHM = "sha256"
CONTINUED_OPERATION_AUTHORIZATION_PURPOSE = "trusted-deployment-continued-operation"


class ContinuedOperationAuthorizationError(ValueError):
    """Normalized fail-closed error at the ATL-A.25 boundary."""


class ContinuedOperationAuthorizationState(str, Enum):
    AUTHORIZED = "authorized"
    DENIED = "denied"
    REVIEW_REQUIRED = "review_required"


class ContinuedOperationLifecycleState(str, Enum):
    ACTIVE = "active"
    REVOKED = "revoked"
    SUPERSEDED = "superseded"


class ContinuedOperationAuthorizationReasonCode(str, Enum):
    READINESS_NOT_ELIGIBLE = "readiness_not_eligible"
    READINESS_REFERENCE_EXPIRED = "readiness_reference_expired"
    REQUEST_BINDING_INVALID = "request_binding_invalid"
    CONTINUED_OPERATION_NOT_PERMITTED = "continued_operation_not_permitted"
    AUTHORIZATION_POLICY_UNAVAILABLE = "authorization_policy_unavailable"
    AUTHORIZATION_AUTHORITY_NOT_TRUSTED = "authorization_authority_not_trusted"


class ContinuedOperationAuthorizationInternalReason(str, Enum):
    INVALID_REQUEST = "invalid_request"
    READINESS_AUTHENTICATION_REJECTED = "readiness_authentication_rejected"
    READINESS_AUTHENTICATION_INCOMPLETE = "readiness_authentication_incomplete"
    READINESS_STATUS_INELIGIBLE = "readiness_status_ineligible"
    TRUSTED_REFERENCE_MISSING = "trusted_reference_missing"
    TRUSTED_REFERENCE_INCONSISTENT = "trusted_reference_inconsistent"
    READINESS_REFERENCE_EXPIRED = "readiness_reference_expired"
    DEPLOYMENT_MISMATCH = "deployment_mismatch"
    POLICY_UNAVAILABLE = "policy_unavailable"
    POLICY_MISMATCH = "policy_mismatch"
    POLICY_NOT_ACTIVE = "policy_not_active"
    CONTRACT_VERSION_NOT_PERMITTED = "contract_version_not_permitted"
    READINESS_AUTHORITY_NOT_PERMITTED = "readiness_authority_not_permitted"
    DEPLOYMENT_NOT_PERMITTED = "deployment_not_permitted"
    CONSUMER_NOT_PERMITTED = "consumer_not_permitted"
    PURPOSE_NOT_PERMITTED = "purpose_not_permitted"
    REQUEST_TIME_INVALID = "request_time_invalid"
    REQUESTED_DURATION_EXCEEDED = "requested_duration_exceeded"
    REQUESTED_EXPIRY_EXCEEDED = "requested_expiry_exceeded"
    SIGNING_KEY_UNAVAILABLE = "signing_key_unavailable"
    SIGNING_AUTHORITY_MISMATCH = "signing_authority_mismatch"
    SIGNING_AUTHORITY_NOT_ACTIVE = "signing_authority_not_active"
    SIGNING_FAILED = "signing_failed"
    INVALID_AUTHORIZATION_SIGNATURE = "invalid_authorization_signature"
    AUTHORIZATION_BINDING_INVALID = "authorization_binding_invalid"
    AUTHORIZATION_EXPIRED = "authorization_expired"
    AUTHORIZATION_NOT_YET_VALID = "authorization_not_yet_valid"
    AUTHORIZATION_NOT_APPLICABLE = "authorization_not_applicable"


def _instant(value: datetime, name: str) -> datetime:
    try:
        return utc(value, name)
    except (ValueError, OverflowError):
        raise ContinuedOperationAuthorizationError(f"{name} is invalid.") from None


def _identifier_set(value: object, name: str) -> None:
    if type(value) is not frozenset or not value:
        raise ContinuedOperationAuthorizationError(f"{name} is invalid.")
    try:
        for item in value:
            identifier(item, name)
    except ValueError:
        raise ContinuedOperationAuthorizationError(f"{name} is invalid.") from None


@dataclass(frozen=True, slots=True)
class ContinuedOperationRequest:
    request_id: str
    deployment_id: str
    consumer_id: str
    purpose: str
    requested_at: datetime
    evaluation_time: datetime
    requested_until: datetime
    policy_id: str
    policy_version: str
    expected_readiness_contract_version: str
    contract_version: str = CONTINUED_OPERATION_AUTHORIZATION_CONTRACT_VERSION

    def __post_init__(self) -> None:
        try:
            for value, name in (
                (self.request_id, "request_id"), (self.deployment_id, "deployment_id"),
                (self.consumer_id, "consumer_id"), (self.purpose, "purpose"),
                (self.policy_id, "policy_id"), (self.policy_version, "policy_version"),
                (self.expected_readiness_contract_version, "expected_readiness_contract_version"),
            ):
                identifier(value, name)
        except ValueError:
            raise ContinuedOperationAuthorizationError("continued-operation request is invalid.") from None
        requested_at = _instant(self.requested_at, "requested_at")
        evaluation_time = _instant(self.evaluation_time, "evaluation_time")
        requested_until = _instant(self.requested_until, "requested_until")
        if requested_at > evaluation_time or requested_until <= evaluation_time:
            raise ContinuedOperationAuthorizationError("continued-operation request interval is invalid.")
        if self.contract_version != CONTINUED_OPERATION_AUTHORIZATION_CONTRACT_VERSION:
            raise ContinuedOperationAuthorizationError("continued-operation contract is unsupported.")
        object.__setattr__(self, "requested_at", requested_at)
        object.__setattr__(self, "evaluation_time", evaluation_time)
        object.__setattr__(self, "requested_until", requested_until)


@dataclass(frozen=True, slots=True)
class ContinuedOperationGrant:
    deployment_id: str
    permitted_consumers: frozenset[str]
    permitted_purposes: frozenset[str]

    def __post_init__(self) -> None:
        try:
            identifier(self.deployment_id, "deployment_id")
        except ValueError:
            raise ContinuedOperationAuthorizationError("continued-operation grant is invalid.") from None
        _identifier_set(self.permitted_consumers, "permitted_consumers")
        _identifier_set(self.permitted_purposes, "permitted_purposes")


@dataclass(frozen=True, slots=True)
class AuthorizationSigningAuthority:
    signer_id: str
    key_id: str
    algorithm: str
    active_from: datetime
    expires_at: datetime
    lifecycle_state: ContinuedOperationLifecycleState
    permitted_deployments: frozenset[str]

    def __post_init__(self) -> None:
        try:
            identifier(self.signer_id, "signer_id")
            identifier(self.key_id, "key_id")
        except ValueError:
            raise ContinuedOperationAuthorizationError("authorization signing authority is invalid.") from None
        if self.algorithm != CONTINUED_OPERATION_AUTHORIZATION_ALGORITHM:
            raise ContinuedOperationAuthorizationError("authorization signing algorithm is unsupported.")
        active_from = _instant(self.active_from, "active_from")
        expires_at = _instant(self.expires_at, "expires_at")
        if expires_at <= active_from or not isinstance(
            self.lifecycle_state, ContinuedOperationLifecycleState
        ):
            raise ContinuedOperationAuthorizationError("authorization signing authority is invalid.")
        _identifier_set(self.permitted_deployments, "permitted_deployments")
        object.__setattr__(self, "active_from", active_from)
        object.__setattr__(self, "expires_at", expires_at)


@dataclass(frozen=True, slots=True)
class ContinuedOperationAuthorizationPolicy:
    policy_id: str
    policy_version: str
    active_from: datetime
    expires_at: datetime
    lifecycle_state: ContinuedOperationLifecycleState
    grants: tuple[ContinuedOperationGrant, ...]
    maximum_duration_seconds: int
    accepted_readiness_contract_versions: frozenset[str]
    permitted_readiness_authorities: frozenset[tuple[str, str]]
    signing_authority: AuthorizationSigningAuthority
    require_resolved_signing_key: bool = True

    def __post_init__(self) -> None:
        try:
            identifier(self.policy_id, "policy_id")
            identifier(self.policy_version, "policy_version")
        except ValueError:
            raise ContinuedOperationAuthorizationError("continued-operation policy is invalid.") from None
        active_from = _instant(self.active_from, "active_from")
        expires_at = _instant(self.expires_at, "expires_at")
        if expires_at <= active_from or not isinstance(
            self.lifecycle_state, ContinuedOperationLifecycleState
        ):
            raise ContinuedOperationAuthorizationError("continued-operation policy is invalid.")
        if (type(self.grants) is not tuple or not self.grants or
                any(type(item) is not ContinuedOperationGrant for item in self.grants)):
            raise ContinuedOperationAuthorizationError("continued-operation policy grants are invalid.")
        deployments = [grant.deployment_id for grant in self.grants]
        if len(deployments) != len(set(deployments)):
            raise ContinuedOperationAuthorizationError("continued-operation policy grants are ambiguous.")
        if type(self.maximum_duration_seconds) is not int or self.maximum_duration_seconds <= 0:
            raise ContinuedOperationAuthorizationError("maximum authorization duration is invalid.")
        _identifier_set(self.accepted_readiness_contract_versions,
                        "accepted_readiness_contract_versions")
        if type(self.permitted_readiness_authorities) is not frozenset or not self.permitted_readiness_authorities:
            raise ContinuedOperationAuthorizationError("permitted readiness authorities are invalid.")
        try:
            for authority in self.permitted_readiness_authorities:
                if type(authority) is not tuple or len(authority) != 2:
                    raise ValueError
                identifier(authority[0], "readiness_issuer_id")
                identifier(authority[1], "readiness_key_id")
        except ValueError:
            raise ContinuedOperationAuthorizationError("permitted readiness authorities are invalid.") from None
        if type(self.signing_authority) is not AuthorizationSigningAuthority:
            raise ContinuedOperationAuthorizationError("authorization signing authority is invalid.")
        if type(self.require_resolved_signing_key) is not bool:
            raise ContinuedOperationAuthorizationError("resolved signing-key requirement is invalid.")
        object.__setattr__(self, "active_from", active_from)
        object.__setattr__(self, "expires_at", expires_at)


@dataclass(frozen=True, slots=True)
class ResolvedAuthorizationVerificationKey:
    signer_id: str
    key_id: str
    algorithm: str
    public_key: bytes
    active_from: datetime
    expires_at: datetime
    lifecycle_state: ContinuedOperationLifecycleState

    def __post_init__(self) -> None:
        try:
            identifier(self.signer_id, "signer_id")
            identifier(self.key_id, "key_id")
        except ValueError:
            raise ContinuedOperationAuthorizationError("resolved authorization key is invalid.") from None
        if self.algorithm != CONTINUED_OPERATION_AUTHORIZATION_ALGORITHM:
            raise ContinuedOperationAuthorizationError("resolved authorization key algorithm is unsupported.")
        if type(self.public_key) is not bytes or len(self.public_key) != 32:
            raise ContinuedOperationAuthorizationError("resolved authorization key is invalid.")
        active_from = _instant(self.active_from, "active_from")
        expires_at = _instant(self.expires_at, "expires_at")
        if expires_at <= active_from or not isinstance(
            self.lifecycle_state, ContinuedOperationLifecycleState
        ):
            raise ContinuedOperationAuthorizationError("resolved authorization key is invalid.")
        object.__setattr__(self, "active_from", active_from)
        object.__setattr__(self, "expires_at", expires_at)


@dataclass(frozen=True, slots=True)
class ContinuedOperationAuthorization:
    authorization_id: str
    request_id: str
    deployment_id: str
    consumer_id: str
    purpose: str
    readiness_attestation_digest: str
    readiness_binding_fingerprint: str
    readiness_issuer_id: str
    readiness_key_id: str
    readiness_contract_version: str
    authorization_policy_id: str
    authorization_policy_version: str
    authorization_signer_id: str
    authorization_key_id: str
    requested_at: datetime
    issued_at: datetime
    not_before: datetime
    expires_at: datetime
    proposition_digest: str
    signature_algorithm: str
    signature_base64: str
    contract_version: str = CONTINUED_OPERATION_AUTHORIZATION_CONTRACT_VERSION

    def __post_init__(self) -> None:
        try:
            digest(self.authorization_id, "authorization_id")
            digest(self.readiness_attestation_digest, "readiness_attestation_digest")
            digest(self.readiness_binding_fingerprint, "readiness_binding_fingerprint")
            digest(self.proposition_digest, "proposition_digest")
            for value, name in (
                (self.request_id, "request_id"), (self.deployment_id, "deployment_id"),
                (self.consumer_id, "consumer_id"), (self.purpose, "purpose"),
                (self.readiness_issuer_id, "readiness_issuer_id"),
                (self.readiness_key_id, "readiness_key_id"),
                (self.readiness_contract_version, "readiness_contract_version"),
                (self.authorization_policy_id, "authorization_policy_id"),
                (self.authorization_policy_version, "authorization_policy_version"),
                (self.authorization_signer_id, "authorization_signer_id"),
                (self.authorization_key_id, "authorization_key_id"),
            ):
                identifier(value, name)
        except ValueError:
            raise ContinuedOperationAuthorizationError("continued-operation authorization is invalid.") from None
        requested_at = _instant(self.requested_at, "requested_at")
        issued_at = _instant(self.issued_at, "issued_at")
        not_before = _instant(self.not_before, "not_before")
        expires_at = _instant(self.expires_at, "expires_at")
        if requested_at > issued_at or issued_at != not_before or expires_at <= not_before:
            raise ContinuedOperationAuthorizationError("continued-operation validity is invalid.")
        if self.signature_algorithm != CONTINUED_OPERATION_AUTHORIZATION_ALGORITHM:
            raise ContinuedOperationAuthorizationError("authorization signature algorithm is unsupported.")
        if self.contract_version != CONTINUED_OPERATION_AUTHORIZATION_CONTRACT_VERSION:
            raise ContinuedOperationAuthorizationError("continued-operation contract is unsupported.")
        try:
            signature = base64.b64decode(self.signature_base64, validate=True)
        except (binascii.Error, ValueError, TypeError):
            raise ContinuedOperationAuthorizationError("authorization signature is invalid.") from None
        if len(signature) != 64 or base64.b64encode(signature).decode("ascii") != self.signature_base64:
            raise ContinuedOperationAuthorizationError("authorization signature is invalid.")
        object.__setattr__(self, "requested_at", requested_at)
        object.__setattr__(self, "issued_at", issued_at)
        object.__setattr__(self, "not_before", not_before)
        object.__setattr__(self, "expires_at", expires_at)


@dataclass(frozen=True, slots=True)
class ContinuedOperationAuthorizationOutcome:
    deployment_id: str
    purpose: str
    state: ContinuedOperationAuthorizationState
    public_reason_codes: tuple[ContinuedOperationAuthorizationReasonCode, ...]
    internal_reasons: tuple[ContinuedOperationAuthorizationInternalReason, ...]
    decided_at: datetime
    authorization: ContinuedOperationAuthorization | None = None

    def __post_init__(self) -> None:
        try:
            identifier(self.deployment_id, "deployment_id")
            identifier(self.purpose, "purpose")
        except ValueError:
            raise ContinuedOperationAuthorizationError("authorization outcome is invalid.") from None
        if not isinstance(self.state, ContinuedOperationAuthorizationState):
            raise ContinuedOperationAuthorizationError("authorization outcome is invalid.")
        if (type(self.public_reason_codes) is not tuple or
                any(not isinstance(item, ContinuedOperationAuthorizationReasonCode)
                    for item in self.public_reason_codes) or
                len(set(self.public_reason_codes)) != len(self.public_reason_codes)):
            raise ContinuedOperationAuthorizationError("authorization outcome is invalid.")
        if (type(self.internal_reasons) is not tuple or
                any(not isinstance(item, ContinuedOperationAuthorizationInternalReason)
                    for item in self.internal_reasons) or
                len(set(self.internal_reasons)) != len(self.internal_reasons)):
            raise ContinuedOperationAuthorizationError("authorization outcome is invalid.")
        successful = self.state is ContinuedOperationAuthorizationState.AUTHORIZED
        if successful != (type(self.authorization) is ContinuedOperationAuthorization):
            raise ContinuedOperationAuthorizationError("authorization outcome is inconsistent.")
        if successful and (self.public_reason_codes or self.internal_reasons):
            raise ContinuedOperationAuthorizationError("authorized outcome cannot contain failures.")
        if not successful and (not self.public_reason_codes or not self.internal_reasons):
            raise ContinuedOperationAuthorizationError("failed outcome requires normalized reasons.")
        object.__setattr__(self, "decided_at", _instant(self.decided_at, "decided_at"))

    @property
    def authorized(self) -> bool:
        return self.state is ContinuedOperationAuthorizationState.AUTHORIZED


@dataclass(frozen=True, slots=True)
class ContinuedOperationAuthorizationVerification:
    valid: bool
    active: bool
    applicable: bool
    reason_code: ContinuedOperationAuthorizationReasonCode | None
    internal_reason: ContinuedOperationAuthorizationInternalReason | None
    checked_at: datetime
    authorization_id: str | None
    expires_at: datetime | None

    def __post_init__(self) -> None:
        if type(self.valid) is not bool or type(self.active) is not bool or type(self.applicable) is not bool:
            raise ContinuedOperationAuthorizationError("authorization verification is invalid.")
        successful = self.valid and self.active and self.applicable
        if successful != (self.reason_code is None and self.internal_reason is None):
            raise ContinuedOperationAuthorizationError("authorization verification is inconsistent.")
        if self.authorization_id is not None:
            try:
                digest(self.authorization_id, "authorization_id")
            except ValueError:
                raise ContinuedOperationAuthorizationError("authorization verification is invalid.") from None
        object.__setattr__(self, "checked_at", _instant(self.checked_at, "checked_at"))
        if self.expires_at is not None:
            object.__setattr__(self, "expires_at", _instant(self.expires_at, "expires_at"))


class PublicContinuedOperationAuthorizationV1(PublicContractModel):
    schema_version: str = CONTINUED_OPERATION_AUTHORIZATION_CONTRACT_VERSION
    deployment_id: str = Field(min_length=1)
    purpose: str = Field(min_length=1)
    authorization_state: ContinuedOperationAuthorizationState
    reason_codes: tuple[ContinuedOperationAuthorizationReasonCode, ...]
    decided_at: datetime
    expires_at: datetime | None = None


__all__ = [
    name for name in globals()
    if name.startswith("ContinuedOperation") or name.startswith("AuthorizationSigning")
    or name.startswith("ResolvedAuthorization") or name.startswith("PublicContinued")
]
__all__ += [
    "CONTINUED_OPERATION_AUTHORIZATION_ALGORITHM",
    "CONTINUED_OPERATION_AUTHORIZATION_CONTRACT_VERSION",
    "CONTINUED_OPERATION_AUTHORIZATION_DIGEST_ALGORITHM",
    "CONTINUED_OPERATION_AUTHORIZATION_PURPOSE",
]
