from __future__ import annotations

import base64

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from src.reference_architecture_authenticated_provenance_contract import (
    ReferenceArchitectureAuthenticatedProvenanceV1,
)
from src.reference_architecture_authenticated_provenance_signature_verification import (
    REFERENCE_ARCHITECTURE_AUTHENTICATED_PROVENANCE_SIGNATURE_VERIFICATION_CONTRACT_NAME,
    REFERENCE_ARCHITECTURE_AUTHENTICATED_PROVENANCE_SIGNATURE_VERIFICATION_CONTRACT_VERSION,
    verify_reference_architecture_authenticated_provenance_signature,
)
from src.reference_architecture_authenticated_provenance_signing_payload import (
    canonical_reference_architecture_authenticated_provenance_signing_payload,
)


PRIVATE_SEED = bytes(range(32))
OTHER_PRIVATE_SEED = bytes(range(1, 33))


def unsigned_provenance(
    *,
    producer_id: str = "aquagear-reference-app",
    key_id: str = "aquagear-reference-app:key:2026-01",
) -> ReferenceArchitectureAuthenticatedProvenanceV1:
    return ReferenceArchitectureAuthenticatedProvenanceV1.model_validate(
        {
            "contract_name": (
                "ai-test-lab.reference-architecture-authenticated-provenance"
            ),
            "contract_version": "1.0",
            "claims": {
                "attestation_id": "attestation-20260914-001",
                "producer_id": producer_id,
                "evidence_sha256": "a" * 64,
                "issued_at": "2026-09-14T19:30:00Z",
            },
            "proof": {
                "algorithm": "ed25519",
                "key_id": key_id,
                "signature_base64": base64.b64encode(bytes(64)).decode("ascii"),
            },
        }
    )


def signed_provenance(
    *,
    private_seed: bytes = PRIVATE_SEED,
    producer_id: str = "aquagear-reference-app",
    key_id: str = "aquagear-reference-app:key:2026-01",
) -> tuple[ReferenceArchitectureAuthenticatedProvenanceV1, bytes]:
    private_key = Ed25519PrivateKey.from_private_bytes(private_seed)
    draft = unsigned_provenance(producer_id=producer_id, key_id=key_id)
    signature = private_key.sign(
        canonical_reference_architecture_authenticated_provenance_signing_payload(draft)
    )
    signed = draft.model_copy(
        update={
            "proof": draft.proof.model_copy(
                update={
                    "signature_base64": base64.b64encode(signature).decode("ascii")
                }
            )
        }
    )
    public_key = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return signed, public_key


def test_signature_verification_contract_identity_is_frozen() -> None:
    assert (
        REFERENCE_ARCHITECTURE_AUTHENTICATED_PROVENANCE_SIGNATURE_VERIFICATION_CONTRACT_NAME
        == "ai-test-lab.reference-architecture-authenticated-provenance-signature-verification"
    )
    assert (
        REFERENCE_ARCHITECTURE_AUTHENTICATED_PROVENANCE_SIGNATURE_VERIFICATION_CONTRACT_VERSION
        == "1.0"
    )


def test_valid_signature_verifies() -> None:
    provenance, public_key = signed_provenance()

    assert verify_reference_architecture_authenticated_provenance_signature(
        provenance, public_key
    )


def test_known_rfc_8032_empty_message_vector_is_supported_by_backend() -> None:
    public_key = bytes.fromhex(
        "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a"
    )
    signature = bytes.fromhex(
        "e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e06522490155"
        "5fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b"
    )

    Ed25519PublicKey.from_public_bytes(public_key).verify(signature, b"")


def test_changed_signed_claim_does_not_verify() -> None:
    provenance, public_key = signed_provenance()
    changed = provenance.model_copy(
        update={
            "claims": provenance.claims.model_copy(
                update={"producer_id": "substituted-producer"}
            )
        }
    )

    assert not verify_reference_architecture_authenticated_provenance_signature(
        changed, public_key
    )


def test_changed_key_id_does_not_verify() -> None:
    provenance, public_key = signed_provenance()
    changed = provenance.model_copy(
        update={
            "proof": provenance.proof.model_copy(update={"key_id": "different-key"})
        }
    )

    assert not verify_reference_architecture_authenticated_provenance_signature(
        changed, public_key
    )


def test_wrong_public_key_does_not_verify() -> None:
    provenance, _ = signed_provenance()
    _, wrong_public_key = signed_provenance(private_seed=OTHER_PRIVATE_SEED)

    assert not verify_reference_architecture_authenticated_provenance_signature(
        provenance, wrong_public_key
    )


def test_changed_signature_does_not_verify() -> None:
    provenance, public_key = signed_provenance()
    signature = bytearray(base64.b64decode(provenance.proof.signature_base64))
    signature[0] ^= 1
    changed = provenance.model_copy(
        update={
            "proof": provenance.proof.model_copy(
                update={
                    "signature_base64": base64.b64encode(signature).decode("ascii")
                }
            )
        }
    )

    assert not verify_reference_architecture_authenticated_provenance_signature(
        changed, public_key
    )


def test_verification_does_not_mutate_contract() -> None:
    provenance, public_key = signed_provenance()
    before = provenance.model_dump(mode="json")

    verify_reference_architecture_authenticated_provenance_signature(
        provenance, public_key
    )

    assert provenance.model_dump(mode="json") == before


@pytest.mark.parametrize("invalid", [None, {}, b"{}", "provenance"])
def test_non_contract_inputs_are_rejected(invalid: object) -> None:
    with pytest.raises(TypeError, match="ReferenceArchitectureAuthenticatedProvenanceV1"):
        verify_reference_architecture_authenticated_provenance_signature(
            invalid,  # type: ignore[arg-type]
            bytes(32),
        )


@pytest.mark.parametrize("invalid", [None, "key", bytearray(32), memoryview(bytes(32))])
def test_non_bytes_public_keys_are_rejected(invalid: object) -> None:
    provenance, _ = signed_provenance()

    with pytest.raises(TypeError, match="public_key must be bytes"):
        verify_reference_architecture_authenticated_provenance_signature(
            provenance,
            invalid,  # type: ignore[arg-type]
        )


@pytest.mark.parametrize("invalid", [b"", bytes(31), bytes(33)])
def test_wrong_length_public_keys_are_rejected(invalid: bytes) -> None:
    provenance, _ = signed_provenance()

    with pytest.raises(ValueError, match="32-byte Ed25519 public key"):
        verify_reference_architecture_authenticated_provenance_signature(
            provenance, invalid
        )
