from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any, Callable

from src.reference_architecture_evidence_admission_contract import REFERENCE_ARCHITECTURE_EVIDENCE_ADMISSION_CONTRACT_VERSION
from src.reference_architecture_evidence_ledger import EvidenceLedgerPort, verify_evidence_ledger_chain
from src.reference_architecture_evidence_ledger_admission import AdmittedEvidenceAuthorization
from src.reference_architecture_evidence_ledger_contract import (
    EvidenceLedgerAppendResult, LedgerEntryStatus, LedgerFailureReason,
)
from src.reference_architecture_evidence_ledger_outcome import EvidenceLedgerPublicOutcomeV1, project_evidence_ledger_outcome
from src.reference_architecture_evidence_ledger_translation import EvidenceLedgerTranslationError, translate_untrusted_evidence_ledger_append_request

def _failed(status: LedgerEntryStatus, reason: LedgerFailureReason) -> EvidenceLedgerPublicOutcomeV1:
    return project_evidence_ledger_outcome(EvidenceLedgerAppendResult(status, reason))

def append_admitted_evidence_to_ledger(payload: Mapping[str, Any], *, authorization: AdmittedEvidenceAuthorization,
    ledger: EvidenceLedgerPort, clock: Callable[[], datetime] | None = None) -> EvidenceLedgerPublicOutcomeV1:
    """Complete fail-closed ATL-A.06 boundary with a trusted clock and explicit projection."""
    if not callable(getattr(ledger, "append", None)) or not callable(getattr(ledger, "chain", None)):
        raise TypeError("ledger must implement the evidence-ledger storage port.")
    now = (clock or (lambda: datetime.now(timezone.utc)))()
    try:
        request = translate_untrusted_evidence_ledger_append_request(payload, authorization=authorization, recorded_at=now)
    except EvidenceLedgerTranslationError:
        return _failed(LedgerEntryStatus.REJECTED, LedgerFailureReason.INVALID_APPEND_REQUEST)
    if authorization.admission_contract_version != REFERENCE_ARCHITECTURE_EVIDENCE_ADMISSION_CONTRACT_VERSION:
        return _failed(LedgerEntryStatus.REJECTED, LedgerFailureReason.ADMISSION_CONTRACT_UNSUPPORTED)
    if now.astimezone(timezone.utc) > authorization.expires_at.astimezone(timezone.utc):
        return _failed(LedgerEntryStatus.REJECTED, LedgerFailureReason.ADMISSION_EXPIRED)
    binding = (request.evidence_sha256, request.evidence_type, request.producer_id,
        request.evaluation_run_id, request.admission_decision_id, request.provenance_reference,
        request.evidence_contract_version, request.admission_contract_version, request.policy_version)
    authorized = (authorization.evidence_sha256, authorization.evidence_type, authorization.producer_id,
        authorization.evaluation_run_id, authorization.decision_id, authorization.provenance_reference,
        authorization.evidence_contract_version, authorization.admission_contract_version, authorization.policy_version)
    if binding != authorized:
        return _failed(LedgerEntryStatus.REJECTED, LedgerFailureReason.EVIDENCE_BINDING_MISMATCH)
    try:
        result = ledger.append(request)
        verification = None if result.entry is None else verify_evidence_ledger_chain(ledger.chain(result.entry.chain_id))
        if result.entry is not None and (verification is None or not verification.verified):
            return _failed(LedgerEntryStatus.ERROR, LedgerFailureReason.STORAGE_ERROR)
        return project_evidence_ledger_outcome(result, verification)
    except Exception:
        return _failed(LedgerEntryStatus.ERROR, LedgerFailureReason.STORAGE_ERROR)
