from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum


REFERENCE_ARCHITECTURE_TRUST_POLICY_CONTRACT_NAME = (
    "ai-test-lab.reference-architecture-trust-policy"
)
REFERENCE_ARCHITECTURE_TRUST_POLICY_CONTRACT_VERSION = "1.0"

_IDENTITY_PATTERN = re.compile(r"[^\s\x00-\x1f\x7f]{1,256}")


class ReferenceArchitectureTrustedKeyStatus(str, Enum):
    ACTIVE = "active"
    DISABLED = "disabled"
    REVOKED = "revoked"


def _identity(value: object, name: str) -> str:
    if type(value) is not str or _IDENTITY_PATTERN.fullmatch(value) is None:
        raise ValueError(f"{name} must contain 1-256 visible non-whitespace characters.")
    return value


def _utc(value: object, name: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ValueError(f"{name} must be a timezone-aware datetime.")
    normalized = value.astimezone(timezone.utc)
    if normalized.utcoffset() != timezone.utc.utcoffset(normalized):
        raise ValueError(f"{name} must be convertible to UTC.")
    return normalized


def _non_empty_scope(values: object, name: str) -> frozenset[str]:
    if not isinstance(values, frozenset) or not values:
        raise ValueError(f"{name} must be a non-empty frozenset.")
    for value in values:
        _identity(value, name)
    return values


@dataclass(frozen=True, slots=True)
class ReferenceArchitectureTrustedKeyV1:
    key_id: str
    public_key: bytes
    algorithm: str
    key_type: str
    activated_at: datetime
    expires_at: datetime | None
    status: ReferenceArchitectureTrustedKeyStatus
    permitted_purposes: frozenset[str]
    permitted_environments: frozenset[str]

    def __post_init__(self) -> None:
        _identity(self.key_id, "key_id")
        if type(self.public_key) is not bytes or not self.public_key:
            raise ValueError("public_key must be non-empty bytes.")
        _identity(self.algorithm, "algorithm")
        _identity(self.key_type, "key_type")
        activated_at = _utc(self.activated_at, "activated_at")
        object.__setattr__(self, "activated_at", activated_at)
        if self.expires_at is not None:
            expires_at = _utc(self.expires_at, "expires_at")
            if expires_at <= activated_at:
                raise ValueError("expires_at must be later than activated_at.")
            object.__setattr__(self, "expires_at", expires_at)
        if not isinstance(self.status, ReferenceArchitectureTrustedKeyStatus):
            raise ValueError("status must be a supported trusted-key status.")
        _non_empty_scope(self.permitted_purposes, "permitted_purposes")
        _non_empty_scope(self.permitted_environments, "permitted_environments")


@dataclass(frozen=True, slots=True)
class ReferenceArchitectureTrustedSignerV1:
    signer_id: str
    keys: tuple[ReferenceArchitectureTrustedKeyV1, ...]

    def __post_init__(self) -> None:
        _identity(self.signer_id, "signer_id")
        if type(self.keys) is not tuple or not self.keys:
            raise ValueError("keys must be a non-empty tuple.")
        if any(not isinstance(key, ReferenceArchitectureTrustedKeyV1) for key in self.keys):
            raise TypeError("keys must contain only trusted-key records.")
        key_ids = [key.key_id for key in self.keys]
        if len(key_ids) != len(set(key_ids)):
            raise ValueError("A signer cannot contain duplicate or ambiguous key IDs.")


@dataclass(frozen=True, slots=True)
class ReferenceArchitectureTrustPolicyV1:
    policy_id: str
    policy_version: str
    trusted_signers: tuple[ReferenceArchitectureTrustedSignerV1, ...]
    permitted_algorithms: frozenset[str]
    permitted_key_types: frozenset[str]

    def __post_init__(self) -> None:
        _identity(self.policy_id, "policy_id")
        _identity(self.policy_version, "policy_version")
        if type(self.trusted_signers) is not tuple or not self.trusted_signers:
            raise ValueError("trusted_signers must be a non-empty tuple.")
        if any(not isinstance(signer, ReferenceArchitectureTrustedSignerV1) for signer in self.trusted_signers):
            raise TypeError("trusted_signers must contain only trusted-signer records.")
        signer_ids = [signer.signer_id for signer in self.trusted_signers]
        if len(signer_ids) != len(set(signer_ids)):
            raise ValueError("A policy cannot contain duplicate or ambiguous signer IDs.")
        _non_empty_scope(self.permitted_algorithms, "permitted_algorithms")
        _non_empty_scope(self.permitted_key_types, "permitted_key_types")


__all__ = [
    "REFERENCE_ARCHITECTURE_TRUST_POLICY_CONTRACT_NAME",
    "REFERENCE_ARCHITECTURE_TRUST_POLICY_CONTRACT_VERSION",
    "ReferenceArchitectureTrustedKeyStatus",
    "ReferenceArchitectureTrustedKeyV1",
    "ReferenceArchitectureTrustedSignerV1",
    "ReferenceArchitectureTrustPolicyV1",
]
