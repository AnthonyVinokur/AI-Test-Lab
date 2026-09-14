from __future__ import annotations

import base64
from dataclasses import FrozenInstanceError

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from src.reference_architecture_authenticated_provenance_contract import (
    ReferenceArchitectureAuthenticatedProvenanceV1,
)
from src.reference_architecture_authenticated_provenance_signer_key_binding import (
    REFERENCE_ARCHITECTURE_AUTHENTICATED_PROVENANCE_SIGNER_KEY_BINDING_CONTRACT_NAME,
    REFERENCE_ARCHITECTURE_AUTHENTICATED_PROVENANCE_SIGNER_KEY_BINDING_CONTRACT_VERSION,
    ReferenceArchitectureResolvedSignerKeyBindingV1,
    verify_reference_architecture_authenticated_provenance_signer_key_binding,
)
from src.reference_architecture_authenticated_provenance_signing_payload import (
    canonical_reference_architecture_authenticated_provenance_signing_payload,
)


PRIVATE_SEED = bytes(range(32))
OTHER_PRIVATE_SEED = bytes(range(1, 33))
PRODUCER_ID = "aquagear-reference-app"
KEY_ID = "aquagear-reference-app:key:2026-01"


def signed_provenance(
    *,
    private_seed: bytes = PRIVATE_SEED,
    producer_id: str = PRODUCER_ID,
    key_id: str = KEY_ID,
) -> tuple[ReferenceArchitectureAuthenticatedProvenanceV1, bytes]:
    private_key = Ed25519PrivateKey.from_private_bytes(private_seed)
    draft = ReferenceArchitectureAuthenticatedProvenanceV1.model_validate(
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
    signature = private_key.sign(
        canonical_reference_architecture_authenticated_provenance_signing_payload(draft)
    )
    provenance = draft.model_copy(
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
    return provenance, public_key


def binding(
    public_key: bytes,
    *,
    producer_id: str = PRODUCER_ID,
    key_id: str = KEY_ID,
) -> ReferenceArchitectureResolvedSignerKeyBindingV1:
    return ReferenceArchitectureResolvedSignerKeyBindingV1(
        producer_id=producer_id,
        key_id=key_id,
        algorithm="ed25519",
        public_key=public_key,
    )


def test_signer_key_binding_contract_identity_is_frozen() -> None:
    assert (
        REFERENCE_ARCHITECTURE_AUTHENTICATED_PROVENANCE_SIGNER_KEY_BINDING_CONTRACT_NAME
        == "ai-test-lab.reference-architecture-authenticated-provenance-signer-key-binding"
    )
    assert (
        REFERENCE_ARCHITECTURE_AUTHENTICATED_PROVENANCE_SIGNER_KEY_BINDING_CONTRACT_VERSION
        == "1.0"
    )


def test_matching_authorized_signer_key_binding_verifies() -> None:
    provenance, public_key = signed_provenance()

    assert verify_reference_architecture_authenticated_provenance_signer_key_binding(
        provenance,
        binding(public_key),
    )


def test_same_key_is_not_authorized_for_a_different_producer() -> None:
    provenance, public_key = signed_provenance()

    assert not verify_reference_architecture_authenticated_provenance_signer_key_binding(
        provenance,
        binding(public_key, producer_id="different-producer"),
    )


def test_same_key_is_not_authorized_under_a_different_key_reference() -> None:
    provenance, public_key = signed_provenance()

    assert not verify_reference_architecture_authenticated_provenance_signer_key_binding(
        provenance,
        binding(public_key, key_id="different-key"),
    )


def test_matching_identity_with_wrong_public_key_does_not_verify() -> None:
    provenance, _ = signed_provenance()
    _, other_public_key = signed_provenance(private_seed=OTHER_PRIVATE_SEED)

    assert not verify_reference_architecture_authenticated_provenance_signer_key_binding(
        provenance,
        binding(other_public_key),
    )


def test_binding_is_immutable() -> None:
    _, public_key = signed_provenance()
    resolved = binding(public_key)

    with pytest.raises(FrozenInstanceError):
        resolved.key_id = "substituted"  # type: ignore[misc]


def test_verification_does_not_mutate_inputs() -> None:
    provenance, public_key = signed_provenance()
    resolved = binding(public_key)
    provenance_before = provenance.model_dump(mode="json")

    verify_reference_architecture_authenticated_provenance_signer_key_binding(
        provenance,
        resolved,
    )

    assert provenance.model_dump(mode="json") == provenance_before
    assert resolved == binding(public_key)


@pytest.mark.parametrize("invalid", [None, {}, b"{}", "provenance"])
def test_non_contract_provenance_is_rejected(invalid: object) -> None:
    _, public_key = signed_provenance()

    with pytest.raises(TypeError, match="ReferenceArchitectureAuthenticatedProvenanceV1"):
        verify_reference_architecture_authenticated_provenance_signer_key_binding(
            invalid,  # type: ignore[arg-type]
            binding(public_key),
        )


@pytest.mark.parametrize("invalid", [None, {}, bytes(32), "binding"])
def test_non_binding_inputs_are_rejected(invalid: object) -> None:
    provenance, _ = signed_provenance()

    with pytest.raises(TypeError, match="ReferenceArchitectureResolvedSignerKeyBindingV1"):
        verify_reference_architecture_authenticated_provenance_signer_key_binding(
            provenance,
            invalid,  # type: ignore[arg-type]
        )


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("producer_id", ""),
        ("producer_id", "producer with spaces"),
        ("producer_id", "p" * 257),
        ("producer_id", 7),
        ("key_id", ""),
        ("key_id", "key\nreference"),
        ("key_id", "k" * 257),
        ("key_id", b"key"),
    ],
)
def test_invalid_binding_identities_are_rejected(
    field_name: str,
    value: object,
) -> None:
    _, public_key = signed_provenance()
    values: dict[str, object] = {
        "producer_id": PRODUCER_ID,
        "key_id": KEY_ID,
        "algorithm": "ed25519",
        "public_key": public_key,
    }
    values[field_name] = value

    with pytest.raises(ValueError, match=field_name):
        ReferenceArchitectureResolvedSignerKeyBindingV1(**values)  # type: ignore[arg-type]


def test_unsupported_binding_algorithm_is_rejected() -> None:
    _, public_key = signed_provenance()

    with pytest.raises(ValueError, match="algorithm must be ed25519"):
        ReferenceArchitectureResolvedSignerKeyBindingV1(
            producer_id=PRODUCER_ID,
            key_id=KEY_ID,
            algorithm="rsa",  # type: ignore[arg-type]
            public_key=public_key,
        )


@pytest.mark.parametrize("invalid", [None, "key", bytearray(32), memoryview(bytes(32))])
def test_non_bytes_binding_public_keys_are_rejected(invalid: object) -> None:
    with pytest.raises(TypeError, match="public_key must be bytes"):
        ReferenceArchitectureResolvedSignerKeyBindingV1(
            producer_id=PRODUCER_ID,
            key_id=KEY_ID,
            algorithm="ed25519",
            public_key=invalid,  # type: ignore[arg-type]
        )


@pytest.mark.parametrize("invalid", [b"", bytes(31), bytes(33)])
def test_wrong_length_binding_public_keys_are_rejected(invalid: bytes) -> None:
    with pytest.raises(ValueError, match="32-byte Ed25519 public key"):
        ReferenceArchitectureResolvedSignerKeyBindingV1(
            producer_id=PRODUCER_ID,
            key_id=KEY_ID,
            algorithm="ed25519",
            public_key=invalid,
        )


def test_production_binding_module_has_no_private_key_capability() -> None:
    import src.reference_architecture_authenticated_provenance_signer_key_binding as module

    assert "Ed25519PrivateKey" not in vars(module)
    assert all("private" not in name.lower() for name in module.__all__)
