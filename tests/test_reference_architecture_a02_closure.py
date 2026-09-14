from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

import pytest

from src.public_contract import serialize_public_contract
from src.reference_architecture_compatibility_contract import (
    AQUAGEAR_REFERENCE_ARCHITECTURE_CONFORMANCE_CONTRACT_VERSION,
    AQUAGEAR_REFERENCE_ARCHITECTURE_CONTRACT_VERSION,
    supported_reference_architecture_compatibility_contract,
)
from src.reference_architecture_conformance_evidence_binding_failure_normalization import (
    REFERENCE_ARCHITECTURE_CONFORMANCE_EVIDENCE_BINDING_FAILURE_CONTRACT_VERSION,
)
from src.reference_architecture_conformance_evidence_binding_outcome import (
    REFERENCE_ARCHITECTURE_CONFORMANCE_EVIDENCE_BINDING_OUTCOME_CONTRACT_VERSION,
    bind_public_reference_architecture_conformance_evidence,
)
from src.reference_architecture_conformance_evidence_binding_serialization import (
    REFERENCE_ARCHITECTURE_CONFORMANCE_EVIDENCE_BINDING_SERIALIZATION_FORMAT,
    REFERENCE_ARCHITECTURE_CONFORMANCE_EVIDENCE_BINDING_SERIALIZATION_VERSION,
    ReferenceArchitectureConformanceEvidenceBindingSerializationError,
    decode_reference_architecture_conformance_evidence_binding_outcome,
    encode_reference_architecture_conformance_evidence_binding_outcome,
)
from src.reference_architecture_conformance_evidence_compatibility_verification import (
    REFERENCE_ARCHITECTURE_CONFORMANCE_EVIDENCE_COMPATIBILITY_VERIFICATION_CONTRACT_VERSION,
)
from src.reference_architecture_conformance_evidence_document_translation import (
    REFERENCE_ARCHITECTURE_CONFORMANCE_EVIDENCE_DOCUMENT_TRANSLATION_CONTRACT_VERSION,
)
from src.reference_architecture_conformance_evidence_intake_contract import (
    AQUAGEAR_CONFORMANCE_EVIDENCE_EXPORT_VERSION,
    AQUAGEAR_CONFORMANCE_EVIDENCE_SCHEMA_VERSION,
    AQUAGEAR_FROZEN_ARCHITECTURE_VERSION,
    REFERENCE_ARCHITECTURE_CONFORMANCE_EVIDENCE_INTAKE_CONTRACT_VERSION,
)
from src.reference_architecture_conformance_evidence_integrity_verification import (
    REFERENCE_ARCHITECTURE_CONFORMANCE_EVIDENCE_INTEGRITY_VERIFICATION_CONTRACT_VERSION,
)
from src.reference_architecture_conformance_evidence_round_trip_binding import (
    REFERENCE_ARCHITECTURE_CONFORMANCE_EVIDENCE_ROUND_TRIP_BINDING_CONTRACT_VERSION,
)
from src.reference_architecture_round_trip_orchestration import (
    orchestrate_correlated_reference_architecture_round_trip,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
A02_MODULES = tuple(
    sorted(
        (PROJECT_ROOT / "src").glob(
            "reference_architecture_conformance_evidence_*.py"
        )
    )
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


def response_payload(*, document: bytes | None = None) -> dict[str, object]:
    return {
        "contract_version": "v1",
        "integration_id": "integration-7",
        "correlation_id": "correlation-11",
        "source_system": "aquagear-reference-app",
        "operation": "enforce",
        "status": "completed",
        "artifact": {
            "artifact_id": "evidence-7",
            "artifact_type": "conformance-evidence",
            "content_type": "application/json",
            "payload": document if document is not None else evidence_document(),
            "schema_version": "1.0",
        },
        "metadata": ({"key": "provider_token", "value": "must-not-cross"},),
    }


class RecordingPort:
    def __init__(self, response: dict[str, object]) -> None:
        self.response = response
        self.calls = 0

    def integrate(self, request: object) -> dict[str, object]:
        self.calls += 1
        return self.response


def public_document(response: dict[str, object]) -> tuple[RecordingPort, bytes]:
    port = RecordingPort(response)
    round_trip = orchestrate_correlated_reference_architecture_round_trip(
        serialize_public_contract(
            supported_reference_architecture_compatibility_contract()
        ),
        {
            "contract_version": "v1",
            "integration_id": "integration-7",
            "correlation_id": "correlation-11",
            "source_system": "ai-test-lab",
            "operation": "enforce",
        },
        port,
    )
    outcome = bind_public_reference_architecture_conformance_evidence(round_trip)
    return port, encode_reference_architecture_conformance_evidence_binding_outcome(
        outcome
    )


def test_frozen_versions_remain_exactly_at_the_a02_baseline() -> None:
    assert {
        REFERENCE_ARCHITECTURE_CONFORMANCE_EVIDENCE_INTAKE_CONTRACT_VERSION,
        REFERENCE_ARCHITECTURE_CONFORMANCE_EVIDENCE_DOCUMENT_TRANSLATION_CONTRACT_VERSION,
        REFERENCE_ARCHITECTURE_CONFORMANCE_EVIDENCE_INTEGRITY_VERIFICATION_CONTRACT_VERSION,
        REFERENCE_ARCHITECTURE_CONFORMANCE_EVIDENCE_COMPATIBILITY_VERIFICATION_CONTRACT_VERSION,
        REFERENCE_ARCHITECTURE_CONFORMANCE_EVIDENCE_ROUND_TRIP_BINDING_CONTRACT_VERSION,
        REFERENCE_ARCHITECTURE_CONFORMANCE_EVIDENCE_BINDING_FAILURE_CONTRACT_VERSION,
        REFERENCE_ARCHITECTURE_CONFORMANCE_EVIDENCE_BINDING_OUTCOME_CONTRACT_VERSION,
        REFERENCE_ARCHITECTURE_CONFORMANCE_EVIDENCE_BINDING_SERIALIZATION_VERSION,
        AQUAGEAR_CONFORMANCE_EVIDENCE_SCHEMA_VERSION,
        AQUAGEAR_REFERENCE_ARCHITECTURE_CONFORMANCE_CONTRACT_VERSION,
    } == {"1.0"}
    assert {
        AQUAGEAR_FROZEN_ARCHITECTURE_VERSION,
        AQUAGEAR_REFERENCE_ARCHITECTURE_CONTRACT_VERSION,
    } == {"v1"}
    assert AQUAGEAR_CONFORMANCE_EVIDENCE_EXPORT_VERSION == "1"
    assert (
        REFERENCE_ARCHITECTURE_CONFORMANCE_EVIDENCE_BINDING_SERIALIZATION_FORMAT
        == "json"
    )


def test_frozen_success_document_is_stable_and_minimal() -> None:
    port, document = public_document(response_payload())
    decoded = decode_reference_architecture_conformance_evidence_binding_outcome(
        document
    )

    assert port.calls == 1
    assert decoded.succeeded is True
    assert encode_reference_architecture_conformance_evidence_binding_outcome(
        decoded
    ) == document
    assert set(json.loads(document)) == {
        "binding",
        "contract_name",
        "failure",
        "outcome_contract_version",
        "succeeded",
    }
    assert document.startswith(
        b'{"binding":{"correlation_id":"correlation-11","evidence":'
    )
    assert document.endswith(b',"succeeded":true}')


def test_tampered_evidence_fails_closed_without_leaking_attacker_state() -> None:
    _, document = public_document(
        response_payload(document=evidence_document(corrupt_digest=True))
    )
    decoded = decode_reference_architecture_conformance_evidence_binding_outcome(
        document
    )

    assert decoded.succeeded is False
    assert decoded.binding is None
    assert decoded.failure is not None
    assert decoded.failure.code.value == "evidence_integrity_failed"
    for forbidden in (
        b"artifact_id",
        b"payload",
        b"provider_token",
        b"must-not-cross",
        b"source_system",
        b"traceback",
        b"0" * 64,
    ):
        assert forbidden not in document


@pytest.mark.parametrize(
    "document",
    [
        b'{"succeeded":true,"succeeded":false}',
        b'{"binding":null,"contract_name":NaN}',
        b'{"binding":null,"contract_name":"x","unknown":"attacker"}',
    ],
)
def test_ambiguous_or_extended_public_documents_fail_closed(
    document: bytes,
) -> None:
    with pytest.raises(
        ReferenceArchitectureConformanceEvidenceBindingSerializationError
    ):
        decode_reference_architecture_conformance_evidence_binding_outcome(document)


def test_a02_boundary_has_no_runtime_provider_or_transport_dependencies() -> None:
    forbidden_roots = {
        "anthropic",
        "aquagear",
        "boto3",
        "google",
        "httpx",
        "ollama",
        "openai",
        "reference_app",
        "requests",
    }
    violations: list[str] = []

    for module_path in A02_MODULES:
        tree = ast.parse(module_path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            imported: list[str] = []
            if isinstance(node, ast.Import):
                imported = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported = [node.module]
            for name in imported:
                if name.split(".", 1)[0] in forbidden_roots:
                    violations.append(f"{module_path.name}: {name}")

    assert violations == []
