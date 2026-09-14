from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from src.reference_architecture_authenticated_provenance_contract import (
    ReferenceArchitectureAuthenticatedProvenanceV1,
)
from src.reference_architecture_authenticated_provenance_signature_verification import (
    verify_reference_architecture_authenticated_provenance_signature,
)


REFERENCE_ARCHITECTURE_AUTHENTICATED_PROVENANCE_SIGNER_KEY_BINDING_CONTRACT_NAME = (
    "ai-test-lab.reference-architecture-authenticated-provenance-signer-key-binding"
)
REFERENCE_ARCHITECTURE_AUTHENTICATED_PROVENANCE_SIGNER_KEY_BINDING_CONTRACT_VERSION = (
    "1.0"
)

_ED25519_PUBLIC_KEY_BYTES = 32
_MAX_PUBLIC_IDENTITY_LENGTH = 256


def _validate_identity(value: object, field_name: str) -> str:
    if type(value) is not str or not value:
        raise ValueError(f"{field_name} must be a non-empty string.")
    if len(value) > _MAX_PUBLIC_IDENTITY_LENGTH:
        raise ValueError(f"{field_name} must not exceed 256 characters.")
    if any(character.isspace() or not character.isprintable() for character in value):
        raise ValueError(
            f"{field_name} must contain visible non-whitespace characters."
        )
    return value


@dataclass(frozen=True, slots=True)
class ReferenceArchitectureResolvedSignerKeyBindingV1:
    """Caller-authorized mapping from one producer and key ID to a public key.

    This value is an input to verification, not a trust decision made by AI Test
    Lab. The caller remains responsible for resolving and authorizing the
    mapping through its own key-management policy.
    """

    producer_id: str
    key_id: str
    algorithm: Literal["ed25519"]
    public_key: bytes

    def __post_init__(self) -> None:
        _validate_identity(self.producer_id, "producer_id")
        _validate_identity(self.key_id, "key_id")
        if self.algorithm != "ed25519":
            raise ValueError("algorithm must be ed25519.")
        if type(self.public_key) is not bytes:
            raise TypeError("public_key must be bytes.")
        if len(self.public_key) != _ED25519_PUBLIC_KEY_BYTES:
            raise ValueError("public_key must be a 32-byte Ed25519 public key.")


def verify_reference_architecture_authenticated_provenance_signer_key_binding(
    provenance: ReferenceArchitectureAuthenticatedProvenanceV1,
    binding: ReferenceArchitectureResolvedSignerKeyBindingV1,
) -> bool:
    """Verify declared signer identity, key reference, and detached signature.

    Verification succeeds only when the caller-authorized binding names the
    exact producer, key ID, and algorithm carried by the signed provenance and
    its public key validates the A.03.03 canonical payload.
    """

    if not isinstance(provenance, ReferenceArchitectureAuthenticatedProvenanceV1):
        raise TypeError(
            "provenance must be a "
            "ReferenceArchitectureAuthenticatedProvenanceV1."
        )
    if not isinstance(binding, ReferenceArchitectureResolvedSignerKeyBindingV1):
        raise TypeError(
            "binding must be a ReferenceArchitectureResolvedSignerKeyBindingV1."
        )

    if provenance.claims.producer_id != binding.producer_id:
        return False
    if provenance.proof.key_id != binding.key_id:
        return False
    if provenance.proof.algorithm != binding.algorithm:
        return False

    return verify_reference_architecture_authenticated_provenance_signature(
        provenance,
        binding.public_key,
    )


__all__ = [
    "REFERENCE_ARCHITECTURE_AUTHENTICATED_PROVENANCE_SIGNER_KEY_BINDING_CONTRACT_NAME",
    "REFERENCE_ARCHITECTURE_AUTHENTICATED_PROVENANCE_SIGNER_KEY_BINDING_CONTRACT_VERSION",
    "ReferenceArchitectureResolvedSignerKeyBindingV1",
    "verify_reference_architecture_authenticated_provenance_signer_key_binding",
]
