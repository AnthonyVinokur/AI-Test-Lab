from __future__ import annotations

import json

import pytest

from src.reference_architecture_conformance_evidence_binding_failure_normalization import (
    ReferenceArchitectureConformanceEvidenceBindingFailureCode,
    ReferenceArchitectureConformanceEvidenceBindingFailureStage,
    ReferenceArchitectureConformanceEvidenceBindingFailureV1,
)
from src.reference_architecture_conformance_evidence_binding_outcome import (
    ReferenceArchitectureConformanceEvidenceBindingOutcomeV1,
    ReferenceArchitectureConformanceEvidenceBindingSuccessV1,
)
from src.reference_architecture_conformance_evidence_binding_serialization import (
    REFERENCE_ARCHITECTURE_CONFORMANCE_EVIDENCE_BINDING_SERIALIZATION_FORMAT,
    REFERENCE_ARCHITECTURE_CONFORMANCE_EVIDENCE_BINDING_SERIALIZATION_VERSION,
    ReferenceArchitectureConformanceEvidenceBindingSerializationError,
    decode_reference_architecture_conformance_evidence_binding_outcome,
    encode_reference_architecture_conformance_evidence_binding_outcome,
    serialize_reference_architecture_conformance_evidence_binding_outcome,
)
from src.reference_architecture_conformance_evidence_intake_contract import (
    supported_reference_architecture_conformance_evidence_intake_contract,
)


DIGEST = "a" * 64


def success_outcome() -> ReferenceArchitectureConformanceEvidenceBindingOutcomeV1:
    evidence = supported_reference_architecture_conformance_evidence_intake_contract(
        evaluation={"conforms": True, "violations": []},
        evaluation_sha256=DIGEST,
        evidence_sha256=DIGEST,
    )
    return ReferenceArchitectureConformanceEvidenceBindingOutcomeV1(
        succeeded=True,
        binding=ReferenceArchitectureConformanceEvidenceBindingSuccessV1(
            integration_id="integration-7",
            correlation_id="correlation-11",
            evidence=evidence,
        ),
    )


def failure_outcome() -> ReferenceArchitectureConformanceEvidenceBindingOutcomeV1:
    return ReferenceArchitectureConformanceEvidenceBindingOutcomeV1(
        succeeded=False,
        failure=ReferenceArchitectureConformanceEvidenceBindingFailureV1(
            stage=ReferenceArchitectureConformanceEvidenceBindingFailureStage.INTEGRITY,
            code=ReferenceArchitectureConformanceEvidenceBindingFailureCode.EVIDENCE_INTEGRITY_FAILED,
            message="The evidence document failed integrity verification.",
            retryable=False,
            integration_id="integration-7",
            correlation_id="correlation-11",
        ),
    )


@pytest.mark.parametrize("outcome", [success_outcome(), failure_outcome()])
def test_outcome_round_trips_through_canonical_json(
    outcome: ReferenceArchitectureConformanceEvidenceBindingOutcomeV1,
) -> None:
    encoded = encode_reference_architecture_conformance_evidence_binding_outcome(
        outcome
    )

    assert (
        decode_reference_architecture_conformance_evidence_binding_outcome(encoded)
        == outcome
    )
    assert (
        encode_reference_architecture_conformance_evidence_binding_outcome(outcome)
        == encoded
    )


def test_encoding_is_compact_sorted_utf8_json() -> None:
    encoded = encode_reference_architecture_conformance_evidence_binding_outcome(
        success_outcome()
    )

    assert encoded.decode("utf-8") == json.dumps(
        json.loads(encoded),
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    assert REFERENCE_ARCHITECTURE_CONFORMANCE_EVIDENCE_BINDING_SERIALIZATION_FORMAT == "json"
    assert REFERENCE_ARCHITECTURE_CONFORMANCE_EVIDENCE_BINDING_SERIALIZATION_VERSION == "1.0"


def test_mapping_serialization_is_detached_from_the_model() -> None:
    outcome = success_outcome()
    payload = serialize_reference_architecture_conformance_evidence_binding_outcome(
        outcome
    )
    payload["binding"]["integration_id"] = "changed"  # type: ignore[index]

    assert outcome.binding is not None
    assert outcome.binding.integration_id == "integration-7"


def test_serializer_accepts_only_the_a0207_public_outcome() -> None:
    with pytest.raises(TypeError, match="A.02.07"):
        serialize_reference_architecture_conformance_evidence_binding_outcome(
            object()  # type: ignore[arg-type]
        )


@pytest.mark.parametrize(
    "document",
    [
        b"not-json",
        b"[]",
        b'{"succeeded":true}',
        b'{"succeeded":true,"binding":null,"failure":null}',
        b'{"succeeded":false,"binding":{},"failure":{}}',
        b'{"succeeded":true,"binding":{},"internal_trace":"secret"}',
        b"\xff",
    ],
)
def test_decoder_fails_closed(document: bytes) -> None:
    with pytest.raises(
        ReferenceArchitectureConformanceEvidenceBindingSerializationError
    ):
        decode_reference_architecture_conformance_evidence_binding_outcome(document)


@pytest.mark.parametrize("document", ["{}", bytearray(b"{}"), memoryview(b"{}")])
def test_decoder_requires_exact_bytes(document: object) -> None:
    with pytest.raises(TypeError, match="bytes"):
        decode_reference_architecture_conformance_evidence_binding_outcome(
            document  # type: ignore[arg-type]
        )


def test_success_document_contains_only_approved_public_state() -> None:
    document = encode_reference_architecture_conformance_evidence_binding_outcome(
        success_outcome()
    )
    payload = json.loads(document)

    assert set(payload) == {
        "contract_name",
        "outcome_contract_version",
        "succeeded",
        "binding",
        "failure",
    }
    assert set(payload["binding"]) == {
        "integration_id",
        "correlation_id",
        "evidence",
    }
    for forbidden in (
        b"artifact",
        b"payload",
        b"response",
        b"metadata",
        b"source_system",
        b"traceback",
        b"provider",
        b"secret",
    ):
        assert forbidden not in document


def test_failure_document_contains_only_the_redacted_failure() -> None:
    document = encode_reference_architecture_conformance_evidence_binding_outcome(
        failure_outcome()
    )
    payload = json.loads(document)

    assert payload["binding"] is None
    assert set(payload["failure"]) == {
        "contract_name",
        "failure_contract_version",
        "stage",
        "code",
        "message",
        "retryable",
        "integration_id",
        "correlation_id",
    }
    assert b"traceback" not in document
    assert b"provider_payload" not in document
    assert b"secret" not in document
