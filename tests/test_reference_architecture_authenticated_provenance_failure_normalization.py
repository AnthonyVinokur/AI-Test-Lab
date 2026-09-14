from __future__ import annotations

import base64
import json
from dataclasses import FrozenInstanceError

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from src.reference_architecture_authenticated_provenance_contract import (
    ReferenceArchitectureAuthenticatedProvenanceV1,
)
from src.reference_architecture_authenticated_provenance_failure_normalization import (
    REFERENCE_ARCHITECTURE_AUTHENTICATED_PROVENANCE_FAILURE_CONTRACT_NAME,
    ReferenceArchitectureAuthenticatedProvenanceFailureStage,
    ReferenceArchitectureNormalizedAuthenticatedProvenanceV1,
    authenticate_reference_architecture_provenance_with_normalized_failure,
)
from src.reference_architecture_authenticated_provenance_signer_key_binding import (
    ReferenceArchitectureResolvedSignerKeyBindingV1,
)
from src.reference_architecture_authenticated_provenance_signing_payload import (
    canonical_reference_architecture_authenticated_provenance_signing_payload,
)


def signed_document(
    *, producer_id: str = "producer-7", key_id: str = "key-11"
) -> tuple[bytes, ReferenceArchitectureResolvedSignerKeyBindingV1]:
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    draft = ReferenceArchitectureAuthenticatedProvenanceV1.model_validate(
        {
            "contract_name": "ai-test-lab.reference-architecture-authenticated-provenance",
            "contract_version": "1.0",
            "claims": {
                "attestation_id": "attestation-3",
                "producer_id": producer_id,
                "evidence_sha256": "a" * 64,
                "issued_at": "2026-09-14T20:00:00Z",
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
    payload = draft.model_dump(mode="json")
    payload["proof"]["signature_base64"] = base64.b64encode(signature).decode("ascii")
    return (
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8"),
        ReferenceArchitectureResolvedSignerKeyBindingV1(
            producer_id=producer_id,
            key_id=key_id,
            algorithm="ed25519",
            public_key=public_key,
        ),
    )


def test_valid_document_and_authorized_binding_succeed() -> None:
    document, binding = signed_document()

    outcome = authenticate_reference_architecture_provenance_with_normalized_failure(
        document, binding
    )

    assert outcome.succeeded is True
    assert outcome.failure is None
    assert outcome.provenance is not None
    assert outcome.provenance.claims.attestation_id == "attestation-3"


@pytest.mark.parametrize("document", [b"not-json", b'{"contract_name":"wrong"}', None])
def test_invalid_documents_are_normalized_without_claim_identifiers(
    document: object,
) -> None:
    _, binding = signed_document()

    outcome = authenticate_reference_architecture_provenance_with_normalized_failure(
        document, binding  # type: ignore[arg-type]
    )

    assert outcome.failure is not None
    assert outcome.failure.stage.value == "document_translation"
    assert outcome.failure.code.value == "invalid_provenance_document"
    assert outcome.failure.attestation_id is None
    assert outcome.failure.producer_id is None
    assert outcome.failure.key_id is None


def test_invalid_binding_input_is_normalized_after_safe_translation() -> None:
    document, _ = signed_document()

    outcome = authenticate_reference_architecture_provenance_with_normalized_failure(
        document, object()  # type: ignore[arg-type]
    )

    assert outcome.failure is not None
    assert outcome.failure.stage.value == "binding_validation"
    assert outcome.failure.code.value == "invalid_signer_key_binding"
    assert outcome.failure.attestation_id == "attestation-3"
    assert outcome.failure.producer_id == "producer-7"
    assert outcome.failure.key_id == "key-11"


@pytest.mark.parametrize("mismatch", ["producer", "key", "public_key"])
def test_all_authentication_mismatches_have_one_safe_failure(mismatch: str) -> None:
    document, binding = signed_document()
    if mismatch == "producer":
        binding = ReferenceArchitectureResolvedSignerKeyBindingV1(
            producer_id="another-producer",
            key_id=binding.key_id,
            algorithm="ed25519",
            public_key=binding.public_key,
        )
    elif mismatch == "key":
        binding = ReferenceArchitectureResolvedSignerKeyBindingV1(
            producer_id=binding.producer_id,
            key_id="another-key",
            algorithm="ed25519",
            public_key=binding.public_key,
        )
    else:
        binding = ReferenceArchitectureResolvedSignerKeyBindingV1(
            producer_id=binding.producer_id,
            key_id=binding.key_id,
            algorithm="ed25519",
            public_key=bytes(range(32)),
        )

    outcome = authenticate_reference_architecture_provenance_with_normalized_failure(
        document, binding
    )

    assert outcome.failure is not None
    assert outcome.failure.stage.value == "authentication"
    assert outcome.failure.code.value == "authentication_failed"
    assert outcome.failure.message == (
        "The authenticated provenance could not be authenticated."
    )
    assert outcome.failure.retryable is False


def test_unexpected_verifier_error_is_redacted_and_normalized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import src.reference_architecture_authenticated_provenance_failure_normalization as module

    document, binding = signed_document()

    def fail(*args: object) -> bool:
        raise RuntimeError("secret-provider-detail")

    monkeypatch.setattr(
        module,
        "verify_reference_architecture_authenticated_provenance_signer_key_binding",
        fail,
    )
    outcome = authenticate_reference_architecture_provenance_with_normalized_failure(
        document, binding
    )

    assert outcome.failure is not None
    assert outcome.failure.code.value == "provenance_verification_failed"
    assert "secret" not in outcome.failure.message


def test_public_failure_contract_is_frozen_minimal_and_redacted() -> None:
    document, binding = signed_document()
    wrong_binding = ReferenceArchitectureResolvedSignerKeyBindingV1(
        producer_id=binding.producer_id,
        key_id=binding.key_id,
        algorithm="ed25519",
        public_key=bytes(range(32)),
    )
    outcome = authenticate_reference_architecture_provenance_with_normalized_failure(
        document, wrong_binding
    )
    assert outcome.failure is not None
    failure = outcome.failure

    assert failure.contract_name == (
        REFERENCE_ARCHITECTURE_AUTHENTICATED_PROVENANCE_FAILURE_CONTRACT_NAME
    )
    assert failure.failure_contract_version == "1.0"
    serialized = failure.model_dump(mode="json")
    assert set(serialized) == {
        "contract_name",
        "failure_contract_version",
        "stage",
        "code",
        "message",
        "retryable",
        "attestation_id",
        "producer_id",
        "key_id",
    }
    assert "signature" not in serialized
    assert "public_key" not in serialized
    assert "document" not in serialized
    with pytest.raises((TypeError, ValueError)):
        failure.message = "changed"  # type: ignore[misc]


def test_internal_result_requires_exactly_one_branch_and_is_frozen() -> None:
    with pytest.raises(ValueError, match="Exactly one"):
        ReferenceArchitectureNormalizedAuthenticatedProvenanceV1()
    document, binding = signed_document()
    outcome = authenticate_reference_architecture_provenance_with_normalized_failure(
        document, binding
    )
    with pytest.raises(FrozenInstanceError):
        outcome.provenance = None  # type: ignore[misc]


def test_control_flow_exceptions_are_not_normalized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import src.reference_architecture_authenticated_provenance_failure_normalization as module

    document, binding = signed_document()

    def interrupt(*args: object) -> bool:
        raise KeyboardInterrupt

    monkeypatch.setattr(
        module,
        "verify_reference_architecture_authenticated_provenance_signer_key_binding",
        interrupt,
    )
    with pytest.raises(KeyboardInterrupt):
        authenticate_reference_architecture_provenance_with_normalized_failure(
            document, binding
        )


def test_normalizer_rejects_invalid_explicit_stage() -> None:
    from src.reference_architecture_authenticated_provenance_failure_normalization import (
        normalize_reference_architecture_authenticated_provenance_failure,
    )

    failure = normalize_reference_architecture_authenticated_provenance_failure(
        RuntimeError("hidden"),
        stage=ReferenceArchitectureAuthenticatedProvenanceFailureStage.AUTHENTICATION,
    )
    assert failure.code.value == "provenance_verification_failed"
