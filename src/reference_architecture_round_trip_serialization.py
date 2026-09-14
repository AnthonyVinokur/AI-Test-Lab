from __future__ import annotations

import json
from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from pydantic import ValidationError

from src.public_contract import serialize_public_contract
from src.reference_architecture_round_trip_outcome_projection import (
    ReferenceArchitectureRoundTripOutcomeV1,
)


REFERENCE_ARCHITECTURE_ROUND_TRIP_SERIALIZATION_FORMAT = "json"
REFERENCE_ARCHITECTURE_ROUND_TRIP_SERIALIZATION_VERSION = "1.0"


class ReferenceArchitectureRoundTripSerializationError(ValueError):
    """Raised when a value cannot cross the frozen A.01.9 boundary."""


def _validated_outcome(
    outcome: ReferenceArchitectureRoundTripOutcomeV1,
) -> ReferenceArchitectureRoundTripOutcomeV1:
    if not isinstance(outcome, ReferenceArchitectureRoundTripOutcomeV1):
        raise TypeError("outcome must be an A.01.8 public round-trip outcome.")

    try:
        # Revalidation protects the serializer from runtime-altered model state.
        return ReferenceArchitectureRoundTripOutcomeV1.model_validate(
            outcome.model_dump(mode="python", round_trip=True)
        )
    except (TypeError, ValueError, ValidationError) as exc:
        raise ReferenceArchitectureRoundTripSerializationError(
            "The public round-trip outcome is invalid."
        ) from exc


def serialize_reference_architecture_round_trip_outcome(
    outcome: ReferenceArchitectureRoundTripOutcomeV1,
) -> dict[str, Any]:
    """Return a detached JSON-safe mapping for one validated A.01.8 outcome."""

    validated = _validated_outcome(outcome)
    payload = serialize_public_contract(validated)
    if not isinstance(payload, Mapping):
        raise ReferenceArchitectureRoundTripSerializationError(
            "The public round-trip serializer produced an invalid payload."
        )
    return deepcopy(dict(payload))


def encode_reference_architecture_round_trip_outcome(
    outcome: ReferenceArchitectureRoundTripOutcomeV1,
) -> bytes:
    """Encode one outcome as deterministic, compact UTF-8 JSON bytes."""

    payload = serialize_reference_architecture_round_trip_outcome(outcome)
    try:
        text = json.dumps(
            payload,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    except (TypeError, ValueError) as exc:
        raise ReferenceArchitectureRoundTripSerializationError(
            "The public round-trip outcome is not JSON serializable."
        ) from exc
    return text.encode("utf-8")


def decode_reference_architecture_round_trip_outcome(
    document: bytes,
) -> ReferenceArchitectureRoundTripOutcomeV1:
    """Decode and fail-closed validate one canonical A.01.9 JSON document."""

    if type(document) is not bytes:
        raise TypeError("document must be UTF-8 JSON bytes.")
    try:
        payload = json.loads(document.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReferenceArchitectureRoundTripSerializationError(
            "The public round-trip document is not valid UTF-8 JSON."
        ) from exc
    if not isinstance(payload, dict):
        raise ReferenceArchitectureRoundTripSerializationError(
            "The public round-trip document must contain a JSON object."
        )
    try:
        return ReferenceArchitectureRoundTripOutcomeV1.model_validate(payload)
    except (TypeError, ValueError, ValidationError) as exc:
        raise ReferenceArchitectureRoundTripSerializationError(
            "The public round-trip document does not match the frozen schema."
        ) from exc


__all__ = [
    "REFERENCE_ARCHITECTURE_ROUND_TRIP_SERIALIZATION_FORMAT",
    "REFERENCE_ARCHITECTURE_ROUND_TRIP_SERIALIZATION_VERSION",
    "ReferenceArchitectureRoundTripSerializationError",
    "decode_reference_architecture_round_trip_outcome",
    "encode_reference_architecture_round_trip_outcome",
    "serialize_reference_architecture_round_trip_outcome",
]
