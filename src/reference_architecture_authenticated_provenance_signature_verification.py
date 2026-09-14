from __future__ import annotations

import base64

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from src.reference_architecture_authenticated_provenance_contract import (
    ReferenceArchitectureAuthenticatedProvenanceV1,
)
from src.reference_architecture_authenticated_provenance_signing_payload import (
    canonical_reference_architecture_authenticated_provenance_signing_payload,
)


REFERENCE_ARCHITECTURE_AUTHENTICATED_PROVENANCE_SIGNATURE_VERIFICATION_CONTRACT_NAME = (
    "ai-test-lab.reference-architecture-authenticated-provenance-signature-verification"
)
REFERENCE_ARCHITECTURE_AUTHENTICATED_PROVENANCE_SIGNATURE_VERIFICATION_CONTRACT_VERSION = (
    "1.0"
)

_ED25519_PUBLIC_KEY_BYTES = 32


def verify_reference_architecture_authenticated_provenance_signature(
    provenance: ReferenceArchitectureAuthenticatedProvenanceV1,
    public_key: bytes,
) -> bool:
    """Verify an A.03 detached Ed25519 signature against its canonical payload.

    The caller supplies the already resolved public key. This primitive proves
    only that the holder of the corresponding private key signed the exact
    A.03.03 payload; it does not decide whether ``key_id`` or the key is trusted.
    """

    if not isinstance(provenance, ReferenceArchitectureAuthenticatedProvenanceV1):
        raise TypeError(
            "provenance must be a "
            "ReferenceArchitectureAuthenticatedProvenanceV1."
        )
    if type(public_key) is not bytes:
        raise TypeError("public_key must be bytes.")
    if len(public_key) != _ED25519_PUBLIC_KEY_BYTES:
        raise ValueError("public_key must be a 32-byte Ed25519 public key.")

    verifier = Ed25519PublicKey.from_public_bytes(public_key)
    signature = base64.b64decode(provenance.proof.signature_base64, validate=True)
    payload = canonical_reference_architecture_authenticated_provenance_signing_payload(
        provenance
    )

    try:
        verifier.verify(signature, payload)
    except InvalidSignature:
        return False
    return True


__all__ = [
    "REFERENCE_ARCHITECTURE_AUTHENTICATED_PROVENANCE_SIGNATURE_VERIFICATION_CONTRACT_NAME",
    "REFERENCE_ARCHITECTURE_AUTHENTICATED_PROVENANCE_SIGNATURE_VERIFICATION_CONTRACT_VERSION",
    "verify_reference_architecture_authenticated_provenance_signature",
]
