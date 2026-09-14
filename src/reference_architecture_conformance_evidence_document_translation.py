from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError

from src.reference_architecture_conformance_evidence_intake_contract import (
    ReferenceArchitectureConformanceEvidenceIntakeV1,
)


REFERENCE_ARCHITECTURE_CONFORMANCE_EVIDENCE_DOCUMENT_TRANSLATION_CONTRACT_NAME = (
    "ai-test-lab.reference-architecture-conformance-evidence-document-translation"
)
REFERENCE_ARCHITECTURE_CONFORMANCE_EVIDENCE_DOCUMENT_TRANSLATION_CONTRACT_VERSION = (
    "1.0"
)


class ReferenceArchitectureConformanceEvidenceDocumentTranslationError(ValueError):
    """Raised when an untrusted evidence document cannot enter A.02.01."""


class _DuplicateObjectKeyError(ValueError):
    """Internal signal for an ambiguous JSON object."""


def _reject_non_standard_number(value: str) -> None:
    raise ValueError(f"Non-standard JSON number {value!r} is not accepted.")


def _object_without_duplicate_keys(
    pairs: list[tuple[str, Any]],
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateObjectKeyError("Duplicate JSON object keys are not accepted.")
        result[key] = value
    return result


def translate_untrusted_reference_architecture_conformance_evidence_document(
    document: bytes,
) -> ReferenceArchitectureConformanceEvidenceIntakeV1:
    """Decode untrusted UTF-8 JSON bytes into the frozen A.02.01 contract.

    Translation establishes only syntactic and structural validity. Published
    digest identities remain untrusted until ATL-A.02.03 verifies them.
    """

    if type(document) is not bytes:
        raise TypeError("document must be UTF-8 JSON bytes.")

    try:
        text = document.decode("utf-8")
        payload = json.loads(
            text,
            object_pairs_hook=_object_without_duplicate_keys,
            parse_constant=_reject_non_standard_number,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError, RecursionError) as exc:
        raise ReferenceArchitectureConformanceEvidenceDocumentTranslationError(
            "The conformance evidence document is not valid unambiguous UTF-8 JSON."
        ) from exc

    if type(payload) is not dict:
        raise ReferenceArchitectureConformanceEvidenceDocumentTranslationError(
            "The conformance evidence document must contain a JSON object."
        )

    try:
        return ReferenceArchitectureConformanceEvidenceIntakeV1.model_validate(payload)
    except (TypeError, ValueError, ValidationError) as exc:
        raise ReferenceArchitectureConformanceEvidenceDocumentTranslationError(
            "The conformance evidence document does not match the frozen intake schema."
        ) from exc


__all__ = [
    "REFERENCE_ARCHITECTURE_CONFORMANCE_EVIDENCE_DOCUMENT_TRANSLATION_CONTRACT_NAME",
    "REFERENCE_ARCHITECTURE_CONFORMANCE_EVIDENCE_DOCUMENT_TRANSLATION_CONTRACT_VERSION",
    "ReferenceArchitectureConformanceEvidenceDocumentTranslationError",
    "translate_untrusted_reference_architecture_conformance_evidence_document",
]
