from __future__ import annotations

import json
from types import MappingProxyType

import pytest

from src.public_contract import serialize_public_contract
from src.reference_architecture_conformance_evidence_document_translation import (
    REFERENCE_ARCHITECTURE_CONFORMANCE_EVIDENCE_DOCUMENT_TRANSLATION_CONTRACT_NAME,
    REFERENCE_ARCHITECTURE_CONFORMANCE_EVIDENCE_DOCUMENT_TRANSLATION_CONTRACT_VERSION,
    ReferenceArchitectureConformanceEvidenceDocumentTranslationError,
    translate_untrusted_reference_architecture_conformance_evidence_document,
)
from src.reference_architecture_conformance_evidence_intake_contract import (
    ReferenceArchitectureConformanceEvidenceIntakeV1,
)


EVALUATION_SHA256 = "1" * 64
EVIDENCE_SHA256 = "a" * 64


def producer_export() -> dict[str, object]:
    return {
        "schema": "aquagear.reference-architecture-conformance-evidence",
        "version": "1",
        "evidence": {
            "schema_version": "1.0",
            "architecture_version": "v1",
            "evaluation": {
                "conforms": True,
                "requirements": [
                    {"requirement_id": "provider_neutral_contract", "passed": True}
                ],
            },
            "evaluation_sha256": EVALUATION_SHA256,
            "evidence_sha256": EVIDENCE_SHA256,
        },
    }


def encode(payload: object) -> bytes:
    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")


def test_translation_contract_identity_is_frozen() -> None:
    assert (
        REFERENCE_ARCHITECTURE_CONFORMANCE_EVIDENCE_DOCUMENT_TRANSLATION_CONTRACT_NAME
        == "ai-test-lab.reference-architecture-conformance-evidence-document-translation"
    )
    assert (
        REFERENCE_ARCHITECTURE_CONFORMANCE_EVIDENCE_DOCUMENT_TRANSLATION_CONTRACT_VERSION
        == "1.0"
    )


def test_exact_a434_document_translates_into_a0201_contract() -> None:
    result = translate_untrusted_reference_architecture_conformance_evidence_document(
        encode(producer_export())
    )

    assert isinstance(result, ReferenceArchitectureConformanceEvidenceIntakeV1)
    assert serialize_public_contract(result) == producer_export()


def test_translation_accepts_utf8_content_and_json_whitespace() -> None:
    payload = producer_export()
    payload["evidence"]["evaluation"]["note"] = "válido 🌊"  # type: ignore[index]
    document = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")

    result = translate_untrusted_reference_architecture_conformance_evidence_document(
        document
    )

    assert result.evidence.evaluation["note"] == "válido 🌊"


@pytest.mark.parametrize(
    "document",
    [
        b"",
        b"not-json",
        b"[]",
        b"null",
        b"\xff",
        b'[{"schema":"wrong-container"}]',
        b'{"schema":NaN}',
        b'{"schema":Infinity}',
    ],
)
def test_malformed_or_non_object_documents_fail_closed(document: bytes) -> None:
    with pytest.raises(
        ReferenceArchitectureConformanceEvidenceDocumentTranslationError
    ):
        translate_untrusted_reference_architecture_conformance_evidence_document(document)


@pytest.mark.parametrize(
    "document",
    [
        b'{"schema":"first","schema":"second"}',
        (
            b'{"schema":"aquagear.reference-architecture-conformance-evidence",'
            b'"version":"1","evidence":{"schema_version":"1.0",'
            b'"architecture_version":"v1","evaluation":{"conforms":true,'
            b'"conforms":false},"evaluation_sha256":"'
            + EVALUATION_SHA256.encode("ascii")
            + b'","evidence_sha256":"'
            + EVIDENCE_SHA256.encode("ascii")
            + b'"}}'
        ),
    ],
)
def test_duplicate_keys_at_any_depth_fail_closed(document: bytes) -> None:
    with pytest.raises(
        ReferenceArchitectureConformanceEvidenceDocumentTranslationError,
        match="unambiguous",
    ):
        translate_untrusted_reference_architecture_conformance_evidence_document(document)


@pytest.mark.parametrize(
    ("location", "field", "value"),
    [
        ("envelope", "internal_trace", "secret"),
        ("evidence", "private_score", 0.99),
        ("envelope", "version", "2"),
        ("evidence", "architecture_version", "v2"),
        ("evidence", "evidence_sha256", "not-a-digest"),
    ],
)
def test_schema_violations_fail_closed(
    location: str, field: str, value: object
) -> None:
    payload = producer_export()
    target = payload if location == "envelope" else payload["evidence"]
    target[field] = value  # type: ignore[index]

    with pytest.raises(
        ReferenceArchitectureConformanceEvidenceDocumentTranslationError,
        match="frozen intake schema",
    ):
        translate_untrusted_reference_architecture_conformance_evidence_document(
            encode(payload)
        )


def test_translation_requires_exact_bytes() -> None:
    for document in ("{}", bytearray(b"{}"), memoryview(b"{}")):
        with pytest.raises(TypeError, match="bytes"):
            translate_untrusted_reference_architecture_conformance_evidence_document(
                document  # type: ignore[arg-type]
            )


def test_translated_contract_is_detached_and_recursively_immutable() -> None:
    document = bytearray(encode(producer_export()))
    result = translate_untrusted_reference_architecture_conformance_evidence_document(
        bytes(document)
    )
    document[:] = b"{}"

    assert result.evidence.evaluation["conforms"] is True
    assert isinstance(result.evidence.evaluation, MappingProxyType)
    assert isinstance(result.evidence.evaluation["requirements"], tuple)
    with pytest.raises(TypeError):
        result.evidence.evaluation["conforms"] = False  # type: ignore[index]


def test_translation_does_not_claim_digest_integrity() -> None:
    payload = producer_export()
    payload["evidence"]["evaluation"]["conforms"] = False  # type: ignore[index]

    result = translate_untrusted_reference_architecture_conformance_evidence_document(
        encode(payload)
    )

    assert result.evidence.evaluation["conforms"] is False
    assert result.evidence.evaluation_sha256 == EVALUATION_SHA256
    assert result.evidence.evidence_sha256 == EVIDENCE_SHA256
