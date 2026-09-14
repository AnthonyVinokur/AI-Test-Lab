from __future__ import annotations

import json
from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from pydantic import ValidationError

from src.public_contract import serialize_public_contract
from src.reference_architecture_conformance_evidence_binding_outcome import (
    ReferenceArchitectureConformanceEvidenceBindingOutcomeV1,
)


REFERENCE_ARCHITECTURE_CONFORMANCE_EVIDENCE_BINDING_SERIALIZATION_FORMAT = "json"
REFERENCE_ARCHITECTURE_CONFORMANCE_EVIDENCE_BINDING_SERIALIZATION_VERSION = "1.0"


class ReferenceArchitectureConformanceEvidenceBindingSerializationError(ValueError):
    """Raised when a value cannot cross the frozen A.02.08 wire boundary."""


class _DuplicateObjectKeyError(ValueError):
    """Internal signal for an ambiguous public JSON document."""


def _object_without_duplicate_keys(
    pairs: list[tuple[str, Any]],
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateObjectKeyError(
                "Duplicate JSON object keys are not accepted."
            )
        result[key] = value
    return result


def _reject_non_standard_number(value: str) -> None:
    raise ValueError(f"Non-standard JSON number {value!r} is not accepted.")


def _validated_outcome(
    outcome: ReferenceArchitectureConformanceEvidenceBindingOutcomeV1,
) -> ReferenceArchitectureConformanceEvidenceBindingOutcomeV1:
    if not isinstance(
        outcome, ReferenceArchitectureConformanceEvidenceBindingOutcomeV1
    ):
        raise TypeError("outcome must be an A.02.07 public evidence-binding outcome.")

    try:
        # Revalidation protects the wire serializer from runtime-altered state.
        return ReferenceArchitectureConformanceEvidenceBindingOutcomeV1.model_validate(
            serialize_public_contract(outcome)
        )
    except (TypeError, ValueError, ValidationError) as exc:
        raise ReferenceArchitectureConformanceEvidenceBindingSerializationError(
            "The public evidence-binding outcome is invalid."
        ) from exc


def serialize_reference_architecture_conformance_evidence_binding_outcome(
    outcome: ReferenceArchitectureConformanceEvidenceBindingOutcomeV1,
) -> dict[str, Any]:
    """Return a detached JSON-safe mapping for one validated A.02.07 outcome."""

    validated = _validated_outcome(outcome)
    payload = serialize_public_contract(validated)
    if not isinstance(payload, Mapping):
        raise ReferenceArchitectureConformanceEvidenceBindingSerializationError(
            "The public evidence-binding serializer produced an invalid payload."
        )
    return deepcopy(dict(payload))


def encode_reference_architecture_conformance_evidence_binding_outcome(
    outcome: ReferenceArchitectureConformanceEvidenceBindingOutcomeV1,
) -> bytes:
    """Encode one outcome as deterministic, compact UTF-8 JSON bytes."""

    payload = serialize_reference_architecture_conformance_evidence_binding_outcome(
        outcome
    )
    try:
        text = json.dumps(
            payload,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    except (TypeError, ValueError) as exc:
        raise ReferenceArchitectureConformanceEvidenceBindingSerializationError(
            "The public evidence-binding outcome is not JSON serializable."
        ) from exc
    return text.encode("utf-8")


def decode_reference_architecture_conformance_evidence_binding_outcome(
    document: bytes,
) -> ReferenceArchitectureConformanceEvidenceBindingOutcomeV1:
    """Decode and fail-closed validate one A.02.08 UTF-8 JSON document."""

    if type(document) is not bytes:
        raise TypeError("document must be UTF-8 JSON bytes.")
    try:
        payload = json.loads(
            document.decode("utf-8"),
            object_pairs_hook=_object_without_duplicate_keys,
            parse_constant=_reject_non_standard_number,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError, RecursionError) as exc:
        raise ReferenceArchitectureConformanceEvidenceBindingSerializationError(
            "The public evidence-binding document is not valid unambiguous UTF-8 JSON."
        ) from exc
    if not isinstance(payload, dict):
        raise ReferenceArchitectureConformanceEvidenceBindingSerializationError(
            "The public evidence-binding document must contain a JSON object."
        )
    try:
        return ReferenceArchitectureConformanceEvidenceBindingOutcomeV1.model_validate(
            payload
        )
    except (TypeError, ValueError, ValidationError) as exc:
        raise ReferenceArchitectureConformanceEvidenceBindingSerializationError(
            "The public evidence-binding document does not match the frozen schema."
        ) from exc


__all__ = [
    "REFERENCE_ARCHITECTURE_CONFORMANCE_EVIDENCE_BINDING_SERIALIZATION_FORMAT",
    "REFERENCE_ARCHITECTURE_CONFORMANCE_EVIDENCE_BINDING_SERIALIZATION_VERSION",
    "ReferenceArchitectureConformanceEvidenceBindingSerializationError",
    "decode_reference_architecture_conformance_evidence_binding_outcome",
    "encode_reference_architecture_conformance_evidence_binding_outcome",
    "serialize_reference_architecture_conformance_evidence_binding_outcome",
]
