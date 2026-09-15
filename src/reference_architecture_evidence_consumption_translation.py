from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.reference_architecture_evidence_consumption_contract import (
    EvidenceConsumptionRequest, EvidenceDisclosurePurpose,
)


class EvidenceConsumptionTranslationError(ValueError):
    pass


_FIELDS = {
    "requester_id", "requester_type", "tenant_id", "ledger_id", "evidence_ids", "run_id",
    "sequence_start", "sequence_end", "purpose", "target_environment", "package_version",
    "policy_id", "policy_version", "authorization_context",
}
_REQUIRED = {
    "requester_id", "requester_type", "tenant_id", "ledger_id", "purpose",
    "target_environment", "policy_id", "policy_version",
}


def translate_untrusted_evidence_consumption_request(payload: Mapping[str, Any]) -> EvidenceConsumptionRequest:
    """Copy an untrusted DTO into a validated immutable command before any port is called."""
    if not isinstance(payload, Mapping) or set(payload) - _FIELDS or not _REQUIRED.issubset(payload):
        raise EvidenceConsumptionTranslationError("The evidence consumption request is malformed.")
    try:
        ids = payload.get("evidence_ids", ())
        context = payload.get("authorization_context", {})
        if not isinstance(ids, (list, tuple)) or not isinstance(context, Mapping):
            raise ValueError
        return EvidenceConsumptionRequest(
            requester_id=payload["requester_id"], requester_type=payload["requester_type"],
            tenant_id=payload["tenant_id"], ledger_id=payload["ledger_id"],
            evidence_ids=tuple(ids), run_id=payload.get("run_id"),
            sequence_start=payload.get("sequence_start"), sequence_end=payload.get("sequence_end"),
            purpose=EvidenceDisclosurePurpose(payload["purpose"]), target_environment=payload["target_environment"],
            package_version=payload.get("package_version", "1.0"), policy_id=payload["policy_id"],
            policy_version=payload["policy_version"], authorization_context=dict(context),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise EvidenceConsumptionTranslationError("The evidence consumption request is malformed.") from error
