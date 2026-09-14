from __future__ import annotations

import hashlib
import json

import pytest

from src.public_contract import serialize_public_contract
from src.reference_architecture_compatibility_contract import (
    supported_reference_architecture_compatibility_contract,
)
from src.reference_architecture_conformance_evidence_binding_outcome import (
    bind_public_reference_architecture_conformance_evidence,
)
from src.reference_architecture_conformance_evidence_binding_serialization import (
    ReferenceArchitectureConformanceEvidenceBindingSerializationError,
    decode_reference_architecture_conformance_evidence_binding_outcome,
    encode_reference_architecture_conformance_evidence_binding_outcome,
)
from src.reference_architecture_round_trip_orchestration import (
    orchestrate_correlated_reference_architecture_round_trip,
)


def canonical_sha256(value: object) -> str:
    document = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(document).hexdigest()


def evidence_document(*, corrupt_digest: bool = False) -> bytes:
    evaluation = {"conforms": True, "violations": []}
    unsigned = {
        "schema_version": "1.0",
        "architecture_version": "v1",
        "evaluation": evaluation,
        "evaluation_sha256": canonical_sha256(evaluation),
    }
    evidence = {
        **unsigned,
        "evidence_sha256": (
            "0" * 64 if corrupt_digest else canonical_sha256(unsigned)
        ),
    }
    return json.dumps(
        {
            "schema": "aquagear.reference-architecture-conformance-evidence",
            "version": "1",
            "evidence": evidence,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def compatibility_payload() -> dict[str, object]:
    return serialize_public_contract(
        supported_reference_architecture_compatibility_contract()
    )


def request_identity() -> dict[str, object]:
    return {
        "contract_version": "v1",
        "integration_id": "integration-7",
        "correlation_id": "correlation-11",
        "source_system": "ai-test-lab",
        "operation": "enforce",
    }


def response_payload(
    *,
    document: bytes | None = None,
    include_artifact: bool = True,
    artifact_type: str = "conformance-evidence",
) -> dict[str, object]:
    artifact: dict[str, object] | None = None
    if include_artifact:
        artifact = {
            "artifact_id": "evidence-7",
            "artifact_type": artifact_type,
            "content_type": "application/json",
            "payload": document if document is not None else evidence_document(),
            "schema_version": "1.0",
        }
    return {
        "contract_version": "v1",
        "integration_id": "integration-7",
        "correlation_id": "correlation-11",
        "source_system": "aquagear-reference-app",
        "operation": "enforce",
        "status": "completed",
        "artifact": artifact,
        "metadata": ({"key": "provider_token", "value": "must-not-cross"},),
    }


class RecordingPort:
    def __init__(self, response: dict[str, object]) -> None:
        self.response = response
        self.requests: list[object] = []

    def integrate(self, request: object) -> dict[str, object]:
        self.requests.append(request)
        return self.response


def execute_public_wire_document(
    response: dict[str, object],
) -> tuple[RecordingPort, bytes]:
    port = RecordingPort(response)
    round_trip = orchestrate_correlated_reference_architecture_round_trip(
        compatibility_payload(),
        request_identity(),
        port,
    )
    outcome = bind_public_reference_architecture_conformance_evidence(round_trip)
    return port, encode_reference_architecture_conformance_evidence_binding_outcome(
        outcome
    )


def test_complete_success_path_produces_decodable_public_evidence() -> None:
    port, document = execute_public_wire_document(response_payload())

    decoded = decode_reference_architecture_conformance_evidence_binding_outcome(
        document
    )

    assert len(port.requests) == 1
    assert decoded.succeeded is True
    assert decoded.failure is None
    assert decoded.binding is not None
    assert decoded.binding.integration_id == "integration-7"
    assert decoded.binding.correlation_id == "correlation-11"
    assert decoded.binding.evidence.evidence.evaluation == {
        "conforms": True,
        "violations": (),
    }
    assert (
        encode_reference_architecture_conformance_evidence_binding_outcome(decoded)
        == document
    )


@pytest.mark.parametrize(
    ("response", "stage", "code"),
    [
        (
            response_payload(include_artifact=False),
            "artifact_validation",
            "missing_evidence_artifact",
        ),
        (
            response_payload(artifact_type="private-evidence"),
            "artifact_validation",
            "invalid_evidence_transport",
        ),
        (
            response_payload(document=evidence_document(corrupt_digest=True)),
            "integrity",
            "evidence_integrity_failed",
        ),
    ],
)
def test_complete_rejection_paths_produce_decodable_redacted_failures(
    response: dict[str, object],
    stage: str,
    code: str,
) -> None:
    _, document = execute_public_wire_document(response)

    decoded = decode_reference_architecture_conformance_evidence_binding_outcome(
        document
    )

    assert decoded.succeeded is False
    assert decoded.binding is None
    assert decoded.failure is not None
    assert decoded.failure.stage.value == stage
    assert decoded.failure.code.value == code
    assert decoded.failure.retryable is False
    assert decoded.failure.integration_id == "integration-7"
    assert decoded.failure.correlation_id == "correlation-11"


def test_end_to_end_wire_output_preserves_the_ip_boundary() -> None:
    _, success_document = execute_public_wire_document(response_payload())
    _, failure_document = execute_public_wire_document(
        response_payload(document=b'{"provider_secret":"must-not-cross"}')
    )

    for document in (success_document, failure_document):
        for forbidden in (
            b"artifact_id",
            b"payload",
            b"payload_base64",
            b"metadata",
            b"provider_token",
            b"must-not-cross",
            b"source_system",
            b"traceback",
        ):
            assert forbidden not in document


def test_tampering_after_end_to_end_export_fails_closed() -> None:
    _, document = execute_public_wire_document(response_payload())
    payload = json.loads(document)
    payload["binding"]["provider_state"] = "must-not-cross"
    tampered = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    with pytest.raises(
        ReferenceArchitectureConformanceEvidenceBindingSerializationError
    ):
        decode_reference_architecture_conformance_evidence_binding_outcome(tampered)
