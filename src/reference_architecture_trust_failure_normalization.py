from __future__ import annotations

from enum import Enum

from src.reference_architecture_trust_policy_evaluation import ReferenceArchitectureTrustCheckError
from src.reference_architecture_trust_policy_translation import ReferenceArchitectureTrustPolicyTranslationError
from src.reference_architecture_trusted_key_resolution import ReferenceArchitectureTrustedKeyResolutionError


class ReferenceArchitectureTrustFailureCode(str, Enum):
    UNKNOWN_SIGNER = "unknown_signer"
    UNKNOWN_KEY = "unknown_key"
    SIGNER_KEY_MISMATCH = "signer_key_mismatch"
    AMBIGUOUS_KEY = "ambiguous_key"
    KEY_NOT_YET_ACTIVE = "key_not_yet_active"
    KEY_EXPIRED = "key_expired"
    KEY_DISABLED = "key_disabled"
    KEY_REVOKED = "key_revoked"
    PURPOSE_NOT_AUTHORIZED = "purpose_not_authorized"
    ENVIRONMENT_NOT_AUTHORIZED = "environment_not_authorized"
    ALGORITHM_NOT_PERMITTED = "algorithm_not_permitted"
    KEY_TYPE_NOT_PERMITTED = "key_type_not_permitted"
    INVALID_TRUST_POLICY = "invalid_trust_policy"
    TRUST_EVALUATION_FAILED = "trust_evaluation_failed"


def normalize_reference_architecture_trust_failure(error: Exception) -> ReferenceArchitectureTrustFailureCode:
    if isinstance(error, ReferenceArchitectureTrustedKeyResolutionError):
        return ReferenceArchitectureTrustFailureCode(error.code.value)
    if isinstance(error, ReferenceArchitectureTrustCheckError):
        return ReferenceArchitectureTrustFailureCode(error.code.value)
    if isinstance(error, ReferenceArchitectureTrustPolicyTranslationError):
        return ReferenceArchitectureTrustFailureCode.INVALID_TRUST_POLICY
    return ReferenceArchitectureTrustFailureCode.TRUST_EVALUATION_FAILED


__all__ = ["ReferenceArchitectureTrustFailureCode", "normalize_reference_architecture_trust_failure"]
