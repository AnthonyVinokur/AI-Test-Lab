from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from src.reference_architecture_trust_policy_contract import (
    ReferenceArchitectureTrustedKeyStatus,
    ReferenceArchitectureTrustPolicyV1,
)
from src.reference_architecture_trusted_key_resolution import ReferenceArchitectureResolvedTrustedKeyV1


class ReferenceArchitectureTrustCheckCode(str, Enum):
    KEY_NOT_YET_ACTIVE = "key_not_yet_active"
    KEY_EXPIRED = "key_expired"
    KEY_DISABLED = "key_disabled"
    KEY_REVOKED = "key_revoked"
    PURPOSE_NOT_AUTHORIZED = "purpose_not_authorized"
    ENVIRONMENT_NOT_AUTHORIZED = "environment_not_authorized"
    ALGORITHM_NOT_PERMITTED = "algorithm_not_permitted"
    KEY_TYPE_NOT_PERMITTED = "key_type_not_permitted"


class ReferenceArchitectureTrustCheckError(ValueError):
    def __init__(self, code: ReferenceArchitectureTrustCheckCode):
        super().__init__(code.value)
        self.code = code


def evaluate_reference_architecture_key_validity(resolved: ReferenceArchitectureResolvedTrustedKeyV1, evaluated_at: datetime) -> None:
    if not isinstance(resolved, ReferenceArchitectureResolvedTrustedKeyV1):
        raise TypeError("resolved must be a resolved trusted key.")
    if not isinstance(evaluated_at, datetime) or evaluated_at.tzinfo is None:
        raise ValueError("evaluated_at must be an explicit timezone-aware datetime.")
    instant = evaluated_at.astimezone(timezone.utc)
    key = resolved.key
    if key.status is ReferenceArchitectureTrustedKeyStatus.REVOKED:
        raise ReferenceArchitectureTrustCheckError(ReferenceArchitectureTrustCheckCode.KEY_REVOKED)
    if key.status is ReferenceArchitectureTrustedKeyStatus.DISABLED:
        raise ReferenceArchitectureTrustCheckError(ReferenceArchitectureTrustCheckCode.KEY_DISABLED)
    if instant < key.activated_at:
        raise ReferenceArchitectureTrustCheckError(ReferenceArchitectureTrustCheckCode.KEY_NOT_YET_ACTIVE)
    if key.expires_at is not None and instant >= key.expires_at:
        raise ReferenceArchitectureTrustCheckError(ReferenceArchitectureTrustCheckCode.KEY_EXPIRED)


def authorize_reference_architecture_trust_scope(resolved: ReferenceArchitectureResolvedTrustedKeyV1, purpose: str, environment: str) -> None:
    if purpose not in resolved.key.permitted_purposes:
        raise ReferenceArchitectureTrustCheckError(ReferenceArchitectureTrustCheckCode.PURPOSE_NOT_AUTHORIZED)
    if environment not in resolved.key.permitted_environments:
        raise ReferenceArchitectureTrustCheckError(ReferenceArchitectureTrustCheckCode.ENVIRONMENT_NOT_AUTHORIZED)


def enforce_reference_architecture_cryptographic_policy(resolved: ReferenceArchitectureResolvedTrustedKeyV1, authenticated_algorithm: str, policy: ReferenceArchitectureTrustPolicyV1) -> None:
    if authenticated_algorithm != resolved.key.algorithm or authenticated_algorithm not in policy.permitted_algorithms:
        raise ReferenceArchitectureTrustCheckError(ReferenceArchitectureTrustCheckCode.ALGORITHM_NOT_PERMITTED)
    if resolved.key.key_type not in policy.permitted_key_types:
        raise ReferenceArchitectureTrustCheckError(ReferenceArchitectureTrustCheckCode.KEY_TYPE_NOT_PERMITTED)


__all__ = ["ReferenceArchitectureTrustCheckCode", "ReferenceArchitectureTrustCheckError", "authorize_reference_architecture_trust_scope", "enforce_reference_architecture_cryptographic_policy", "evaluate_reference_architecture_key_validity"]
