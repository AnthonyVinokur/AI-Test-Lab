from __future__ import annotations

import base64
import json

import pytest
from pydantic import ValidationError

from src.public_contract import serialize_public_contract
from src.reference_architecture_authenticated_provenance_contract import (
    ReferenceArchitectureAuthenticatedProvenanceV1,
)
from src.reference_architecture_authenticated_provenance_document_translation import (
    REFERENCE_ARCHITECTURE_AUTHENTICATED_PROVENANCE_DOCUMENT_TRANSLATION_CONTRACT_NAME,
    REFERENCE_ARCHITECTURE_AUTHENTICATED_PROVENANCE_DOCUMENT_TRANSLATION_CONTRACT_VERSION,
    ReferenceArchitectureAuthenticatedProvenanceDocumentTranslationError,
    translate_untrusted_reference_architecture_authenticated_provenance_document,
)


EVIDENCE_SHA256 = "a" * 64
SIGNATURE_BASE64 = base64.b64encode(bytes(range(64))).decode("ascii")


def provenance_document() -> dict[str, object]:
    return {
        "contract_name": "ai-test-lab.reference-architecture-authenticated-provenance",
        "contract_version": "1.0",
        "claims": {
            "attestation_id": "attestation-20260914-001",
            "producer_id": "aquagear-reference-app",
            "evidence_sha256": EVIDENCE_SHA256,
            "issued_at": "2026-09-14T19:30:00Z",
        },
        "proof": {
            "algorithm": "ed25519",
            "key_id": "aquagear-reference-app:key:2026-01",
            "signature_base64": SIGNATURE_BASE64,
        },
    }


def encode(payload: object) -> bytes:
    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")


def test_translation_contract_identity_is_frozen() -> None:
    assert (
        REFERENCE_ARCHITECTURE_AUTHENTICATED_PROVENANCE_DOCUMENT_TRANSLATION_CONTRACT_NAME
        == "ai-test-lab.reference-architecture-authenticated-provenance-document-translation"
    )
    assert (
        REFERENCE_ARCHITECTURE_AUTHENTICATED_PROVENANCE_DOCUMENT_TRANSLATION_CONTRACT_VERSION
        == "1.0"
    )


def test_exact_provenance_document_translates_into_a0301_contract() -> None:
    document = provenance_document()

    result = translate_untrusted_reference_architecture_authenticated_provenance_document(
        encode(document)
    )

    assert isinstance(result, ReferenceArchitectureAuthenticatedProvenanceV1)
    assert serialize_public_contract(result) == document


def test_translation_accepts_json_whitespace() -> None:
    document = json.dumps(provenance_document(), indent=2).encode("utf-8")

    result = translate_untrusted_reference_architecture_authenticated_provenance_document(
        document
    )

    assert result.claims.producer_id == "aquagear-reference-app"


@pytest.mark.parametrize(
    "document",
    [
        b"",
        b"not-json",
        b"[]",
        b"null",
        b"\xff",
        b'[{"contract_name":"wrong-container"}]',
        b'{"contract_name":NaN}',
        b'{"contract_name":Infinity}',
    ],
)
def test_malformed_or_non_object_documents_fail_closed(document: bytes) -> None:
    with pytest.raises(
        ReferenceArchitectureAuthenticatedProvenanceDocumentTranslationError
    ):
        translate_untrusted_reference_architecture_authenticated_provenance_document(
            document
        )


@pytest.mark.parametrize(
    "document",
    [
        b'{"contract_name":"first","contract_name":"second"}',
        (
            b'{"contract_name":"ai-test-lab.reference-architecture-authenticated-provenance",'
            b'"contract_version":"1.0","claims":{"attestation_id":"first",'
            b'"attestation_id":"second","producer_id":"producer",'
            b'"evidence_sha256":"'
            + EVIDENCE_SHA256.encode("ascii")
            + b'","issued_at":"2026-09-14T19:30:00Z"},"proof":'
            b'{"algorithm":"ed25519","key_id":"key-1","signature_base64":"'
            + SIGNATURE_BASE64.encode("ascii")
            + b'"}}'
        ),
    ],
)
def test_duplicate_keys_at_any_depth_fail_closed(document: bytes) -> None:
    with pytest.raises(
        ReferenceArchitectureAuthenticatedProvenanceDocumentTranslationError,
        match="unambiguous",
    ):
        translate_untrusted_reference_architecture_authenticated_provenance_document(
            document
        )


@pytest.mark.parametrize(
    ("location", "field", "value"),
    [
        ("top", "internal_trust_score", 0.99),
        ("claims", "provider_state", "secret"),
        ("proof", "private_key", "must-not-cross-boundary"),
        ("top", "contract_version", "2.0"),
        ("claims", "evidence_sha256", "not-a-digest"),
        ("proof", "algorithm", "rsa-pss"),
    ],
)
def test_schema_violations_fail_closed(
    location: str, field: str, value: object
) -> None:
    payload = provenance_document()
    target = payload if location == "top" else payload[location]
    target[field] = value  # type: ignore[index]

    with pytest.raises(
        ReferenceArchitectureAuthenticatedProvenanceDocumentTranslationError,
        match="frozen provenance schema",
    ):
        translate_untrusted_reference_architecture_authenticated_provenance_document(
            encode(payload)
        )


def test_translation_requires_exact_bytes() -> None:
    for document in ("{}", bytearray(b"{}"), memoryview(b"{}")):
        with pytest.raises(TypeError, match="bytes"):
            translate_untrusted_reference_architecture_authenticated_provenance_document(
                document  # type: ignore[arg-type]
            )


def test_translated_contract_is_detached_and_immutable() -> None:
    document = bytearray(encode(provenance_document()))
    result = translate_untrusted_reference_architecture_authenticated_provenance_document(
        bytes(document)
    )
    document[:] = b"{}"

    assert result.claims.producer_id == "aquagear-reference-app"
    with pytest.raises(ValidationError):
        result.claims.producer_id = "substituted"  # type: ignore[misc]


def test_translation_does_not_claim_authenticity_or_trust() -> None:
    payload = provenance_document()
    payload["claims"]["producer_id"] = "untrusted-producer"  # type: ignore[index]

    result = translate_untrusted_reference_architecture_authenticated_provenance_document(
        encode(payload)
    )

    assert result.claims.producer_id == "untrusted-producer"
    assert result.proof.signature_base64 == SIGNATURE_BASE64
