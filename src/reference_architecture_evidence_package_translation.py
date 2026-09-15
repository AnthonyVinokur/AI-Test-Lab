from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.reference_architecture_evidence_package_contract import EvidencePackageRequest


class EvidencePackageTranslationError(ValueError):
    pass


_FIELDS = {"ledger_id", "evidence_ids", "run_id", "sequence_start", "sequence_end", "format_version", "metadata"}


def translate_untrusted_evidence_package_request(payload: Mapping[str, Any]) -> EvidencePackageRequest:
    if not isinstance(payload, Mapping) or set(payload) - _FIELDS or "ledger_id" not in payload:
        raise EvidencePackageTranslationError("The evidence package request is malformed.")
    try:
        evidence_ids = payload.get("evidence_ids", ())
        if not isinstance(evidence_ids, (list, tuple)):
            raise ValueError
        return EvidencePackageRequest(
            ledger_id=payload["ledger_id"], evidence_ids=tuple(evidence_ids), run_id=payload.get("run_id"),
            sequence_start=payload.get("sequence_start"), sequence_end=payload.get("sequence_end"),
            format_version=payload.get("format_version", "1.0"), metadata=payload.get("metadata", {}),
        )
    except (TypeError, ValueError, KeyError) as error:
        raise EvidencePackageTranslationError("The evidence package request is malformed.") from error
