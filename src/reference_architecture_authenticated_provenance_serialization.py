from __future__ import annotations

import json
from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from pydantic import ValidationError

from src.public_contract import serialize_public_contract
from src.reference_architecture_authenticated_provenance_outcome import (
    ReferenceArchitectureAuthenticatedProvenanceOutcomeV1,
)


REFERENCE_ARCHITECTURE_AUTHENTICATED_PROVENANCE_SERIALIZATION_FORMAT = "json"
REFERENCE_ARCHITECTURE_AUTHENTICATED_PROVENANCE_SERIALIZATION_VERSION = "1.0"


class ReferenceArchitectureAuthenticatedProvenanceSerializationError(ValueError):
    """Raised when a value cannot cross the frozen A.03.08 wire boundary."""


class _DuplicateObjectKeyError(ValueError):
    pass


def _object_without_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateObjectKeyError("Duplicate JSON object keys are not accepted.")
        result[key] = value
    return result


def _reject_non_standard_number(value: str) -> None:
    raise ValueError(f"Non-standard JSON number {value!r} is not accepted.")


def _validated_outcome(
    outcome: ReferenceArchitectureAuthenticatedProvenanceOutcomeV1,
) -> ReferenceArchitectureAuthenticatedProvenanceOutcomeV1:
    if not isinstance(outcome, ReferenceArchitectureAuthenticatedProvenanceOutcomeV1):
        raise TypeError("outcome must be an A.03.07 public provenance outcome.")
    try:
        return ReferenceArchitectureAuthenticatedProvenanceOutcomeV1.model_validate(
            serialize_public_contract(outcome)
        )
    except (TypeError, ValueError, ValidationError) as exc:
        raise ReferenceArchitectureAuthenticatedProvenanceSerializationError(
            "The public authenticated-provenance outcome is invalid."
        ) from exc


def serialize_reference_architecture_authenticated_provenance_outcome(
    outcome: ReferenceArchitectureAuthenticatedProvenanceOutcomeV1,
) -> dict[str, Any]:
    validated = _validated_outcome(outcome)
    payload = serialize_public_contract(validated)
    if not isinstance(payload, Mapping):
        raise ReferenceArchitectureAuthenticatedProvenanceSerializationError(
            "The public authenticated-provenance serializer produced an invalid payload."
        )
    return deepcopy(dict(payload))


def encode_reference_architecture_authenticated_provenance_outcome(
    outcome: ReferenceArchitectureAuthenticatedProvenanceOutcomeV1,
) -> bytes:
    payload = serialize_reference_architecture_authenticated_provenance_outcome(outcome)
    try:
        return json.dumps(
            payload, ensure_ascii=False, allow_nan=False, separators=(",", ":"), sort_keys=True
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ReferenceArchitectureAuthenticatedProvenanceSerializationError(
            "The public authenticated-provenance outcome is not JSON serializable."
        ) from exc


def decode_reference_architecture_authenticated_provenance_outcome(
    document: bytes,
) -> ReferenceArchitectureAuthenticatedProvenanceOutcomeV1:
    if type(document) is not bytes:
        raise TypeError("document must be UTF-8 JSON bytes.")
    try:
        payload = json.loads(
            document.decode("utf-8"),
            object_pairs_hook=_object_without_duplicate_keys,
            parse_constant=_reject_non_standard_number,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError, RecursionError) as exc:
        raise ReferenceArchitectureAuthenticatedProvenanceSerializationError(
            "The public authenticated-provenance document is not valid unambiguous UTF-8 JSON."
        ) from exc
    if not isinstance(payload, dict):
        raise ReferenceArchitectureAuthenticatedProvenanceSerializationError(
            "The public authenticated-provenance document must contain a JSON object."
        )
    try:
        return ReferenceArchitectureAuthenticatedProvenanceOutcomeV1.model_validate(payload)
    except (TypeError, ValueError, ValidationError) as exc:
        raise ReferenceArchitectureAuthenticatedProvenanceSerializationError(
            "The public authenticated-provenance document does not match the frozen schema."
        ) from exc


__all__ = [
    "REFERENCE_ARCHITECTURE_AUTHENTICATED_PROVENANCE_SERIALIZATION_FORMAT",
    "REFERENCE_ARCHITECTURE_AUTHENTICATED_PROVENANCE_SERIALIZATION_VERSION",
    "ReferenceArchitectureAuthenticatedProvenanceSerializationError",
    "decode_reference_architecture_authenticated_provenance_outcome",
    "encode_reference_architecture_authenticated_provenance_outcome",
    "serialize_reference_architecture_authenticated_provenance_outcome",
]
