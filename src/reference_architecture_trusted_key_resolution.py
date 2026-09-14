from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from src.reference_architecture_authenticated_provenance_outcome import (
    ReferenceArchitectureAuthenticatedProvenanceOutcomeV1,
)
from src.reference_architecture_trust_policy_contract import (
    ReferenceArchitectureTrustedKeyV1,
    ReferenceArchitectureTrustPolicyV1,
)


class ReferenceArchitectureTrustedKeyResolutionCode(str, Enum):
    UNKNOWN_SIGNER = "unknown_signer"
    UNKNOWN_KEY = "unknown_key"
    SIGNER_KEY_MISMATCH = "signer_key_mismatch"
    AMBIGUOUS_KEY = "ambiguous_key"


class ReferenceArchitectureTrustedKeyResolutionError(ValueError):
    def __init__(self, code: ReferenceArchitectureTrustedKeyResolutionCode):
        super().__init__(code.value)
        self.code = code


@dataclass(frozen=True, slots=True)
class ReferenceArchitectureResolvedTrustedKeyV1:
    signer_id: str
    key: ReferenceArchitectureTrustedKeyV1


def resolve_reference_architecture_trusted_key(
    authenticated: ReferenceArchitectureAuthenticatedProvenanceOutcomeV1,
    policy: ReferenceArchitectureTrustPolicyV1,
) -> ReferenceArchitectureResolvedTrustedKeyV1:
    if not isinstance(authenticated, ReferenceArchitectureAuthenticatedProvenanceOutcomeV1) or not authenticated.succeeded or authenticated.authentication is None:
        raise TypeError("authenticated must be a successful ATL-A.03 public outcome.")
    if not isinstance(policy, ReferenceArchitectureTrustPolicyV1):
        raise TypeError("policy must be a ReferenceArchitectureTrustPolicyV1.")
    claim = authenticated.authentication
    signers = [signer for signer in policy.trusted_signers if signer.signer_id == claim.producer_id]
    if not signers:
        raise ReferenceArchitectureTrustedKeyResolutionError(ReferenceArchitectureTrustedKeyResolutionCode.UNKNOWN_SIGNER)
    matches = [key for signer in signers for key in signer.keys if key.key_id == claim.key_id]
    if not matches:
        if any(key.key_id == claim.key_id for signer in policy.trusted_signers for key in signer.keys):
            raise ReferenceArchitectureTrustedKeyResolutionError(ReferenceArchitectureTrustedKeyResolutionCode.SIGNER_KEY_MISMATCH)
        raise ReferenceArchitectureTrustedKeyResolutionError(ReferenceArchitectureTrustedKeyResolutionCode.UNKNOWN_KEY)
    if len(matches) != 1:
        raise ReferenceArchitectureTrustedKeyResolutionError(ReferenceArchitectureTrustedKeyResolutionCode.AMBIGUOUS_KEY)
    return ReferenceArchitectureResolvedTrustedKeyV1(signer_id=claim.producer_id, key=matches[0])


__all__ = ["ReferenceArchitectureResolvedTrustedKeyV1", "ReferenceArchitectureTrustedKeyResolutionCode", "ReferenceArchitectureTrustedKeyResolutionError", "resolve_reference_architecture_trusted_key"]
