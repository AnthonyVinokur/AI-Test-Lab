from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from src.reference_architecture_evidence_ledger_admission import AdmittedEvidenceAuthorization
from src.reference_architecture_evidence_ledger_contract import (
    REFERENCE_ARCHITECTURE_EVIDENCE_LEDGER_CONTRACT_NAME,
    REFERENCE_ARCHITECTURE_EVIDENCE_LEDGER_CONTRACT_VERSION, EvidenceLedgerAppendRequest,
)

class EvidenceLedgerTranslationError(ValueError): pass

_FIELDS = {"contract_name", "contract_version", "evidence_sha256", "evidence_type", "producer_id",
    "evaluation_run_id", "admission_decision_id", "provenance_reference", "evidence_contract_version",
    "admission_contract_version", "policy_version", "supersedes_entry_id"}

def translate_untrusted_evidence_ledger_append_request(payload: Mapping[str, Any], *,
    authorization: AdmittedEvidenceAuthorization, recorded_at: datetime) -> EvidenceLedgerAppendRequest:
    try:
        if not isinstance(payload, Mapping) or set(payload) != _FIELDS:
            raise EvidenceLedgerTranslationError("append request must contain exactly the frozen schema fields.")
        if payload["contract_name"] != REFERENCE_ARCHITECTURE_EVIDENCE_LEDGER_CONTRACT_NAME or payload["contract_version"] != REFERENCE_ARCHITECTURE_EVIDENCE_LEDGER_CONTRACT_VERSION:
            raise EvidenceLedgerTranslationError("The ledger contract is unsupported.")
        if not isinstance(authorization, AdmittedEvidenceAuthorization) or not authorization.authentic:
            raise EvidenceLedgerTranslationError("A trusted admission authorization is required.")
        return EvidenceLedgerAppendRequest(evidence_sha256=payload["evidence_sha256"], evidence_type=payload["evidence_type"],
            producer_id=payload["producer_id"], evaluation_run_id=payload["evaluation_run_id"],
            admission_decision_id=payload["admission_decision_id"], provenance_reference=payload["provenance_reference"],
            evidence_contract_version=payload["evidence_contract_version"], admission_contract_version=payload["admission_contract_version"],
            ledger_contract_version=payload["contract_version"], policy_version=payload["policy_version"],
            recorded_at=recorded_at, supersedes_entry_id=payload["supersedes_entry_id"])
    except EvidenceLedgerTranslationError: raise
    except (KeyError, TypeError, ValueError) as exc:
        raise EvidenceLedgerTranslationError("The append request is malformed or ambiguous.") from exc
