from __future__ import annotations

import base64
from dataclasses import FrozenInstanceError

import pytest
from pydantic import ValidationError

from src.public_contract import serialize_public_contract
from src.reference_architecture_response_translation import (
    ProviderNeutralIntegrationOperationV1,
    ProviderNeutralIntegrationStatusV1,
    ReferenceArchitectureResponseTranslationError,
    translate_reference_architecture_response,
)


def response_payload() -> dict[str, object]:
    return {
        "contract_version": "v1",
        "integration_id": "integration-001",
        "correlation_id": "correlation-001",
        "source_system": "aquagear-reference-app",
        "operation": "return",
        "status": "completed",
        "artifact": {
            "artifact_id": "evidence-001",
            "artifact_type": "conformance-evidence",
            "content_type": "application/json",
            "payload": b'{"valid":true}',
            "schema_version": "v1",
        },
        "metadata": (
            {"key": "producer", "value": "aquagear"},
            {"key": "profile", "value": "reference"},
        ),
    }


def test_translates_complete_frozen_v1_response() -> None:
    result = translate_reference_architecture_response(response_payload())

    assert result.response.operation is ProviderNeutralIntegrationOperationV1.RETURN
    assert result.response.status is ProviderNeutralIntegrationStatusV1.COMPLETED
    assert result.response.artifact is not None
    assert result.response.artifact.payload_base64 == base64.b64encode(
        b'{"valid":true}'
    ).decode("ascii")
    assert tuple(item.key for item in result.response.metadata) == (
        "producer",
        "profile",
    )


def test_public_serialization_contains_only_approved_fields() -> None:
    serialized = serialize_public_contract(
        translate_reference_architecture_response(response_payload())
    )

    assert serialized["contract_name"] == (
        "ai-test-lab.reference-architecture-response-translation"
    )
    assert "payload" not in serialized["response"]["artifact"]
    assert serialized["response"]["artifact"]["payload_base64"]


def test_optional_artifact_is_supported() -> None:
    payload = response_payload()
    payload["artifact"] = None

    result = translate_reference_architecture_response(payload)

    assert result.response.artifact is None


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("contract_version", "v2"),
        ("integration_id", ""),
        ("operation", "evaluate"),
        ("status", "unknown"),
    ],
)
def test_invalid_response_values_are_rejected(field: str, value: object) -> None:
    payload = response_payload()
    payload[field] = value

    with pytest.raises(ReferenceArchitectureResponseTranslationError):
        translate_reference_architecture_response(payload)


@pytest.mark.parametrize("payload", [None, [], {}, {"unknown": "value"}])
def test_malformed_response_is_rejected(payload: object) -> None:
    with pytest.raises(ReferenceArchitectureResponseTranslationError):
        translate_reference_architecture_response(payload)  # type: ignore[arg-type]


def test_extra_response_field_is_rejected() -> None:
    payload = response_payload()
    payload["private_score"] = 0.99

    with pytest.raises(ReferenceArchitectureResponseTranslationError):
        translate_reference_architecture_response(payload)


def test_empty_or_non_bytes_artifact_payload_is_rejected() -> None:
    for value in (b"", "secret"):
        payload = response_payload()
        payload["artifact"] = {
            **payload["artifact"],  # type: ignore[misc]
            "payload": value,
        }
        with pytest.raises(ReferenceArchitectureResponseTranslationError):
            translate_reference_architecture_response(payload)


def test_duplicate_metadata_key_is_rejected() -> None:
    payload = response_payload()
    payload["metadata"] = (
        {"key": "same", "value": "one"},
        {"key": "same", "value": "two"},
    )

    with pytest.raises(ReferenceArchitectureResponseTranslationError):
        translate_reference_architecture_response(payload)


def test_result_and_nested_contracts_are_immutable() -> None:
    result = translate_reference_architecture_response(response_payload())

    with pytest.raises((FrozenInstanceError, ValidationError, TypeError)):
        result.response.status = ProviderNeutralIntegrationStatusV1.FAILED  # type: ignore[misc]


def test_translation_does_not_mutate_provider_payload() -> None:
    payload = response_payload()
    artifact = dict(payload["artifact"])  # type: ignore[arg-type]
    metadata = tuple(dict(item) for item in payload["metadata"])  # type: ignore[union-attr]

    translate_reference_architecture_response(payload)

    assert payload["artifact"] == artifact
    assert payload["metadata"] == metadata
