from __future__ import annotations

import json
from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from pydantic import ValidationError

from src.public_contract import serialize_public_contract
from src.reference_architecture_trusted_evidence_outcome import ReferenceArchitectureTrustedEvidenceOutcomeV1


class ReferenceArchitectureTrustedEvidenceSerializationError(ValueError):
    pass


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON keys are not accepted.")
        result[key] = value
    return result


def serialize_reference_architecture_trusted_evidence_outcome(outcome: ReferenceArchitectureTrustedEvidenceOutcomeV1) -> dict[str, Any]:
    if not isinstance(outcome, ReferenceArchitectureTrustedEvidenceOutcomeV1):
        raise TypeError("outcome must be a public trusted-evidence outcome.")
    return deepcopy(serialize_public_contract(outcome))


def encode_reference_architecture_trusted_evidence_outcome(outcome: ReferenceArchitectureTrustedEvidenceOutcomeV1) -> bytes:
    try:
        return json.dumps(serialize_reference_architecture_trusted_evidence_outcome(outcome), sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ReferenceArchitectureTrustedEvidenceSerializationError("The trusted-evidence outcome is not serializable.") from exc


def decode_reference_architecture_trusted_evidence_outcome(document: bytes) -> ReferenceArchitectureTrustedEvidenceOutcomeV1:
    if type(document) is not bytes:
        raise TypeError("document must be UTF-8 JSON bytes.")
    try:
        payload = json.loads(document.decode("utf-8"), object_pairs_hook=_pairs, parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
        if not isinstance(payload, Mapping):
            raise ValueError("root is not an object")
        return ReferenceArchitectureTrustedEvidenceOutcomeV1.model_validate(payload)
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError, ValidationError, RecursionError) as exc:
        raise ReferenceArchitectureTrustedEvidenceSerializationError("The public trusted-evidence document is invalid.") from exc


__all__ = ["ReferenceArchitectureTrustedEvidenceSerializationError", "decode_reference_architecture_trusted_evidence_outcome", "encode_reference_architecture_trusted_evidence_outcome", "serialize_reference_architecture_trusted_evidence_outcome"]
