from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from pydantic import Field

from src.public_contract import PublicContractModel
from src.reference_architecture_deployment_execution_contract import digest, identifier, utc
from src.reference_architecture_deployment_readiness_contract import DeploymentReadinessStatus


READINESS_AUTHENTICATION_CONTRACT_VERSION = "1.0"
READINESS_AUTHENTICATION_ALGORITHM = "ed25519"
READINESS_AUTHENTICATION_PURPOSE = "deployment-readiness-authentication"


class ReadinessAuthenticationError(ValueError):
    """Normalized fail-closed error at the readiness-authentication boundary."""


class ReadinessAuthenticationState(str, Enum):
    VERIFIED = "verified"
    REJECTED = "rejected"
    REVIEW_REQUIRED = "review_required"


class ReadinessAuthenticationReasonCode(str, Enum):
    AUTHENTICITY_NOT_VERIFIED = "readiness_authenticity_not_verified"
    BINDING_INVALID = "readiness_binding_invalid"
    RECORD_EXPIRED = "readiness_record_expired"
    AUTHORITY_NOT_TRUSTED = "readiness_authority_not_trusted"
    VERIFICATION_MATERIAL_UNAVAILABLE = "readiness_verification_material_unavailable"


class ReadinessAuthenticationInternalReason(str, Enum):
    INVALID_REVALIDATION_RESULT = "invalid_revalidation_result"
    ATTESTATION_BINDING_MISMATCH = "attestation_binding_mismatch"
    INVALID_ATTESTATION = "invalid_attestation"
    INVALID_BINDING_TIME = "invalid_binding_time"
    BINDING_EXPIRED = "binding_expired"
    CLAIMS_MISMATCH = "claims_mismatch"
    UNSUPPORTED_CONTRACT = "unsupported_contract"
    UNSUPPORTED_ALGORITHM = "unsupported_algorithm"
    INVALID_SIGNATURE = "invalid_signature"
    POLICY_UNAVAILABLE = "policy_unavailable"
    KEY_UNAVAILABLE = "key_unavailable"
    POLICY_MISMATCH = "policy_mismatch"
    ISSUER_NOT_AUTHORIZED = "issuer_not_authorized"
    AUTHORITY_NOT_ACTIVE = "authority_not_active"
    KEY_MISMATCH = "key_mismatch"
    KEY_NOT_ACTIVE = "key_not_active"
    KEY_INVALID = "key_invalid"


class ReadinessAuthorityStatus(str, Enum):
    ACTIVE = "active"
    REVOKED = "revoked"
    SUPERSEDED = "superseded"


def _instant(value: datetime, name: str) -> datetime:
    try:
        return utc(value, name)
    except (ValueError, OverflowError):
        raise ReadinessAuthenticationError(f"{name} is invalid.") from None


@dataclass(frozen=True, slots=True)
class ReadinessAuthenticationClaims:
    deployment_id: str
    readiness_status: DeploymentReadinessStatus
    readiness_reason_codes: tuple[str, ...]
    attestation_digest: str
    binding_fingerprint: str
    issuer_id: str
    key_id: str
    algorithm: str
    policy_id: str
    policy_version: str
    issued_at: datetime
    expires_at: datetime
    contract_version: str = READINESS_AUTHENTICATION_CONTRACT_VERSION

    def __post_init__(self) -> None:
        try:
            for value, name in ((self.deployment_id, "deployment_id"),
                                (self.issuer_id, "issuer_id"), (self.key_id, "key_id"),
                                (self.policy_id, "policy_id"), (self.policy_version, "policy_version")):
                identifier(value, name)
            digest(self.attestation_digest, "attestation_digest")
            digest(self.binding_fingerprint, "binding_fingerprint")
        except ValueError:
            raise ReadinessAuthenticationError("readiness authentication claims are invalid.") from None
        if not isinstance(self.readiness_status, DeploymentReadinessStatus):
            raise ReadinessAuthenticationError("readiness authentication status is invalid.")
        if (type(self.readiness_reason_codes) is not tuple or
                any(type(reason) is not str or not reason for reason in self.readiness_reason_codes) or
                len(set(self.readiness_reason_codes)) != len(self.readiness_reason_codes)):
            raise ReadinessAuthenticationError("readiness authentication reasons are invalid.")
        if self.algorithm != READINESS_AUTHENTICATION_ALGORITHM:
            raise ReadinessAuthenticationError("readiness authentication algorithm is unsupported.")
        if self.contract_version != READINESS_AUTHENTICATION_CONTRACT_VERSION:
            raise ReadinessAuthenticationError("readiness authentication contract is unsupported.")
        issued_at = _instant(self.issued_at, "issued_at")
        expires_at = _instant(self.expires_at, "expires_at")
        if expires_at <= issued_at:
            raise ReadinessAuthenticationError("readiness authentication validity is invalid.")
        object.__setattr__(self, "issued_at", issued_at)
        object.__setattr__(self, "expires_at", expires_at)


@dataclass(frozen=True, slots=True)
class SignedReadinessEnvelope:
    claims: ReadinessAuthenticationClaims
    signature_base64: str

    def __post_init__(self) -> None:
        if not isinstance(self.claims, ReadinessAuthenticationClaims):
            raise ReadinessAuthenticationError("readiness authentication claims are invalid.")
        try:
            decoded = base64.b64decode(self.signature_base64, validate=True)
        except (binascii.Error, ValueError, TypeError):
            raise ReadinessAuthenticationError("readiness authentication signature is invalid.") from None
        if len(decoded) != 64 or base64.b64encode(decoded).decode("ascii") != self.signature_base64:
            raise ReadinessAuthenticationError("readiness authentication signature is invalid.")


@dataclass(frozen=True, slots=True)
class AuthorizedReadinessIssuerKey:
    issuer_id: str
    key_id: str
    algorithm: str
    active_from: datetime
    expires_at: datetime | None
    status: ReadinessAuthorityStatus
    permitted_deployments: frozenset[str]

    def __post_init__(self) -> None:
        for value, name in ((self.issuer_id, "issuer_id"), (self.key_id, "key_id")):
            try:
                identifier(value, name)
            except ValueError:
                raise ReadinessAuthenticationError("readiness authority is invalid.") from None
        if self.algorithm != READINESS_AUTHENTICATION_ALGORITHM:
            raise ReadinessAuthenticationError("readiness authority algorithm is unsupported.")
        active_from = _instant(self.active_from, "active_from")
        expires_at = None if self.expires_at is None else _instant(self.expires_at, "expires_at")
        if expires_at is not None and expires_at <= active_from:
            raise ReadinessAuthenticationError("readiness authority validity is invalid.")
        if not isinstance(self.status, ReadinessAuthorityStatus):
            raise ReadinessAuthenticationError("readiness authority status is invalid.")
        if (type(self.permitted_deployments) is not frozenset or not self.permitted_deployments or
                any(type(item) is not str or not item for item in self.permitted_deployments)):
            raise ReadinessAuthenticationError("readiness authority scope is invalid.")
        object.__setattr__(self, "active_from", active_from)
        object.__setattr__(self, "expires_at", expires_at)


@dataclass(frozen=True, slots=True)
class ReadinessAuthenticationPolicy:
    policy_id: str
    policy_version: str
    authorizations: tuple[AuthorizedReadinessIssuerKey, ...]
    accepted_contract_versions: frozenset[str] = frozenset({READINESS_AUTHENTICATION_CONTRACT_VERSION})

    def __post_init__(self) -> None:
        try:
            identifier(self.policy_id, "policy_id")
            identifier(self.policy_version, "policy_version")
        except ValueError:
            raise ReadinessAuthenticationError("readiness authentication policy is invalid.") from None
        if (type(self.authorizations) is not tuple or not self.authorizations or
                any(not isinstance(item, AuthorizedReadinessIssuerKey) for item in self.authorizations)):
            raise ReadinessAuthenticationError("readiness authentication policy is invalid.")
        identities = [(item.issuer_id, item.key_id) for item in self.authorizations]
        if len(identities) != len(set(identities)):
            raise ReadinessAuthenticationError("readiness authentication policy is ambiguous.")
        if type(self.accepted_contract_versions) is not frozenset or not self.accepted_contract_versions:
            raise ReadinessAuthenticationError("readiness authentication policy versions are invalid.")
        if any(type(version) is not str or not version for version in self.accepted_contract_versions):
            raise ReadinessAuthenticationError("readiness authentication policy versions are invalid.")


@dataclass(frozen=True, slots=True)
class ResolvedReadinessVerificationKey:
    issuer_id: str
    key_id: str
    algorithm: str
    public_key: bytes
    active_from: datetime
    expires_at: datetime | None
    status: ReadinessAuthorityStatus

    def __post_init__(self) -> None:
        try:
            identifier(self.issuer_id, "issuer_id")
            identifier(self.key_id, "key_id")
        except ValueError:
            raise ReadinessAuthenticationError("resolved readiness key is invalid.") from None
        if self.algorithm != READINESS_AUTHENTICATION_ALGORITHM:
            raise ReadinessAuthenticationError("resolved readiness key algorithm is unsupported.")
        if type(self.public_key) is not bytes or len(self.public_key) != 32:
            raise ReadinessAuthenticationError("resolved readiness key is invalid.")
        active_from = _instant(self.active_from, "active_from")
        expires_at = None if self.expires_at is None else _instant(self.expires_at, "expires_at")
        if expires_at is not None and expires_at <= active_from:
            raise ReadinessAuthenticationError("resolved readiness key validity is invalid.")
        if not isinstance(self.status, ReadinessAuthorityStatus):
            raise ReadinessAuthenticationError("resolved readiness key status is invalid.")
        object.__setattr__(self, "active_from", active_from)
        object.__setattr__(self, "expires_at", expires_at)


@dataclass(frozen=True, slots=True)
class TrustedReadinessReference:
    deployment_id: str
    attestation_digest: str
    binding_fingerprint: str
    issuer_id: str
    key_id: str
    verified_at: datetime
    expires_at: datetime
    contract_version: str = READINESS_AUTHENTICATION_CONTRACT_VERSION

    def __post_init__(self) -> None:
        try:
            for value, name in ((self.deployment_id, "deployment_id"),
                                (self.issuer_id, "issuer_id"), (self.key_id, "key_id")):
                identifier(value, name)
            digest(self.attestation_digest, "attestation_digest")
            digest(self.binding_fingerprint, "binding_fingerprint")
        except ValueError:
            raise ReadinessAuthenticationError("trusted readiness reference is invalid.") from None
        verified_at = _instant(self.verified_at, "verified_at")
        expires_at = _instant(self.expires_at, "expires_at")
        if expires_at <= verified_at or self.contract_version != READINESS_AUTHENTICATION_CONTRACT_VERSION:
            raise ReadinessAuthenticationError("trusted readiness reference is invalid.")
        object.__setattr__(self, "verified_at", verified_at)
        object.__setattr__(self, "expires_at", expires_at)


@dataclass(frozen=True, slots=True)
class ReadinessAuthenticationOutcome:
    deployment_id: str
    readiness_status: DeploymentReadinessStatus
    authentication_state: ReadinessAuthenticationState
    public_reason_codes: tuple[ReadinessAuthenticationReasonCode, ...]
    internal_reasons: tuple[ReadinessAuthenticationInternalReason, ...]
    verified_at: datetime
    trusted_reference: TrustedReadinessReference | None = None

    def __post_init__(self) -> None:
        try:
            identifier(self.deployment_id, "deployment_id")
        except ValueError:
            raise ReadinessAuthenticationError("readiness authentication outcome is invalid.") from None
        if (not isinstance(self.readiness_status, DeploymentReadinessStatus) or
                not isinstance(self.authentication_state, ReadinessAuthenticationState)):
            raise ReadinessAuthenticationError("readiness authentication outcome is invalid.")
        if (type(self.public_reason_codes) is not tuple or
                any(not isinstance(item, ReadinessAuthenticationReasonCode)
                    for item in self.public_reason_codes) or
                len(set(self.public_reason_codes)) != len(self.public_reason_codes)):
            raise ReadinessAuthenticationError("readiness authentication outcome is invalid.")
        if (type(self.internal_reasons) is not tuple or
                any(not isinstance(item, ReadinessAuthenticationInternalReason)
                    for item in self.internal_reasons) or
                len(set(self.internal_reasons)) != len(self.internal_reasons)):
            raise ReadinessAuthenticationError("readiness authentication outcome is invalid.")
        verified_at = _instant(self.verified_at, "verified_at")
        should_trust = (self.authentication_state is ReadinessAuthenticationState.VERIFIED and
                        self.readiness_status is DeploymentReadinessStatus.READY)
        if should_trust != isinstance(self.trusted_reference, TrustedReadinessReference):
            raise ReadinessAuthenticationError("readiness authentication outcome is inconsistent.")
        if self.authentication_state is ReadinessAuthenticationState.VERIFIED:
            if self.public_reason_codes or self.internal_reasons:
                raise ReadinessAuthenticationError("verified readiness cannot contain authentication failures.")
        elif not self.public_reason_codes or not self.internal_reasons or self.trusted_reference is not None:
            raise ReadinessAuthenticationError("failed readiness authentication requires normalized reasons.")
        object.__setattr__(self, "verified_at", verified_at)

    @property
    def eligible_for_reliance(self) -> bool:
        return (self.authentication_state is ReadinessAuthenticationState.VERIFIED and
                self.readiness_status is DeploymentReadinessStatus.READY and
                self.trusted_reference is not None)


class PublicReadinessAuthenticationOutcomeV1(PublicContractModel):
    schema_version: str = READINESS_AUTHENTICATION_CONTRACT_VERSION
    deployment_id: str = Field(min_length=1)
    readiness_status: DeploymentReadinessStatus
    authentication_state: ReadinessAuthenticationState
    reason_codes: tuple[ReadinessAuthenticationReasonCode, ...]
    verified_at: datetime


__all__ = [name for name in globals() if name.startswith("Readiness") or name.startswith("Trusted") or
           name.startswith("Authorized") or name.startswith("Resolved") or name.startswith("Public")]
__all__ += ["READINESS_AUTHENTICATION_ALGORITHM", "READINESS_AUTHENTICATION_CONTRACT_VERSION",
            "READINESS_AUTHENTICATION_PURPOSE", "SignedReadinessEnvelope"]
