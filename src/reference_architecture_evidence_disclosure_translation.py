from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from src.reference_architecture_evidence_disclosure_contract import DisclosureRequest
from src.reference_architecture_evidence_package_contract import EvidencePackage


class DisclosureTranslationError(ValueError): pass


_FIELDS = {"request_id", "requester_id", "recipient_id", "purpose", "environment", "package",
           "requested_record_ids", "requested_fields", "output_format", "authorization_id",
           "requested_at", "contract_version"}
_REQUIRED = _FIELDS - {"contract_version"}


def translate_untrusted_disclosure_request(payload: Mapping[str, Any]) -> DisclosureRequest:
    if not isinstance(payload, Mapping) or set(payload) - _FIELDS or not _REQUIRED.issubset(payload):
        raise DisclosureTranslationError("The disclosure request is malformed.")
    try:
        records, fields = payload["requested_record_ids"], payload["requested_fields"]
        if not isinstance(records, (list, tuple)) or not isinstance(fields, (list, tuple)):
            raise ValueError
        requested_at = payload["requested_at"]
        if isinstance(requested_at, str): requested_at = datetime.fromisoformat(requested_at.replace("Z", "+00:00"))
        package = payload["package"]
        if not isinstance(package, EvidencePackage): raise ValueError
        return DisclosureRequest(payload["request_id"], payload["requester_id"], payload["recipient_id"],
            payload["purpose"], payload["environment"], package, tuple(records), tuple(fields),
            payload["output_format"], payload["authorization_id"], requested_at,
            payload.get("contract_version", "1.0"))
    except (KeyError, TypeError, ValueError) as error:
        raise DisclosureTranslationError("The disclosure request is malformed.") from error
