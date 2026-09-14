from __future__ import annotations

import json

import pytest

from src.reference_architecture_response_translation import (
    ProviderNeutralIntegrationResponseV1,
)
from src.reference_architecture_round_trip_failure_normalization import (
    ReferenceArchitectureFailureCode,
    ReferenceArchitectureFailureStage,
    ReferenceArchitectureRoundTripFailureV1,
)
from src.reference_architecture_round_trip_outcome_projection import (
    ReferenceArchitectureRoundTripOutcomeV1,
)
from src.reference_architecture_round_trip_serialization import (
    ReferenceArchitectureRoundTripSerializationError,
    decode_reference_architecture_round_trip_outcome,
    encode_reference_architecture_round_trip_outcome,
    serialize_reference_architecture_round_trip_outcome,
)


def success_outcome() -> ReferenceArchitectureRoundTripOutcomeV1:
    return ReferenceArchitectureRoundTripOutcomeV1(
        succeeded=True,
        response=ProviderNeutralIntegrationResponseV1(
            contract_version="v1",
            integration_id="integration-7",
            correlation_id="correlation-11",
            source_system="aquagear-reference-app",
            operation="enforce",
            status="completed",
        ),
    )


def failure_outcome() -> ReferenceArchitectureRoundTripOutcomeV1:
    return ReferenceArchitectureRoundTripOutcomeV1(
        succeeded=False,
        failure=ReferenceArchitectureRoundTripFailureV1(
            stage=ReferenceArchitectureFailureStage.PROVIDER_INVOCATION,
            code=ReferenceArchitectureFailureCode.PROVIDER_INVOCATION_FAILED,
            message="The provider could not complete the integration request.",
            retryable=True,
            integration_id="integration-7",
            correlation_id="correlation-11",
        ),
    )


@pytest.mark.parametrize("outcome", [success_outcome(), failure_outcome()])
def test_outcome_round_trips_through_canonical_json(
    outcome: ReferenceArchitectureRoundTripOutcomeV1,
) -> None:
    encoded = encode_reference_architecture_round_trip_outcome(outcome)
    assert decode_reference_architecture_round_trip_outcome(encoded) == outcome
    assert encode_reference_architecture_round_trip_outcome(outcome) == encoded


def test_encoding_is_compact_sorted_utf8_json() -> None:
    encoded = encode_reference_architecture_round_trip_outcome(success_outcome())
    assert encoded.decode("utf-8") == json.dumps(
        json.loads(encoded),
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def test_mapping_serialization_is_detached_from_the_model() -> None:
    outcome = success_outcome()
    payload = serialize_reference_architecture_round_trip_outcome(outcome)
    payload["response"]["integration_id"] = "changed"  # type: ignore[index]
    assert outcome.response is not None
    assert outcome.response.integration_id == "integration-7"


def test_serializer_accepts_only_the_a018_public_outcome() -> None:
    with pytest.raises(TypeError, match="A.01.8"):
        serialize_reference_architecture_round_trip_outcome(object())  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "document",
    [
        b"not-json",
        b"[]",
        b'{"succeeded":true}',
        b'{"succeeded":true,"response":null,"failure":null}',
        b'{"succeeded":true,"response":{},"internal_trace":"secret"}',
        b"\xff",
    ],
)
def test_decoder_fails_closed(document: bytes) -> None:
    with pytest.raises(ReferenceArchitectureRoundTripSerializationError):
        decode_reference_architecture_round_trip_outcome(document)


def test_decoder_requires_bytes() -> None:
    with pytest.raises(TypeError, match="bytes"):
        decode_reference_architecture_round_trip_outcome("{}")  # type: ignore[arg-type]


def test_failure_document_contains_no_unapproved_state() -> None:
    document = encode_reference_architecture_round_trip_outcome(failure_outcome())
    assert b"traceback" not in document
    assert b"provider_payload" not in document
    assert b"secret" not in document
    assert set(json.loads(document)) == {
        "contract_name",
        "outcome_contract_version",
        "succeeded",
        "response",
        "failure",
    }
