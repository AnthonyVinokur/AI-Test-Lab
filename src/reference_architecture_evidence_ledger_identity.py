from __future__ import annotations

import json
from hashlib import sha256
from typing import Any

from src.reference_architecture_evidence_ledger_contract import (
    EvidenceChainId, EvidenceLedgerAppendRequest, EvidenceLedgerEntry, EvidenceLedgerEntryId, LedgerSequence,
)

def _hash(payload: dict[str, Any]) -> str:
    document = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    return sha256(document.encode("utf-8")).hexdigest()

def calculate_evidence_ledger_entry_id(request: EvidenceLedgerAppendRequest) -> EvidenceLedgerEntryId:
    """Logical identity deliberately excludes assigned time, sequence and storage IDs."""
    return EvidenceLedgerEntryId(_hash({"admission_decision_id": request.admission_decision_id,
        "admission_contract_version": request.admission_contract_version,
        "evidence_contract_version": request.evidence_contract_version, "evidence_sha256": request.evidence_sha256,
        "evidence_type": request.evidence_type, "evaluation_run_id": request.evaluation_run_id,
        "ledger_contract_version": request.ledger_contract_version, "policy_version": request.policy_version,
        "producer_id": request.producer_id, "provenance_reference": request.provenance_reference,
        "supersedes_entry_id": request.supersedes_entry_id}))

def calculate_evidence_chain_id(request: EvidenceLedgerAppendRequest) -> EvidenceChainId:
    return EvidenceChainId(_hash({"evidence_sha256": request.evidence_sha256,
        "evidence_type": request.evidence_type, "producer_id": request.producer_id}))

def calculate_evidence_ledger_entry_digest(*, request: EvidenceLedgerAppendRequest,
    entry_id: EvidenceLedgerEntryId, chain_id: EvidenceChainId, sequence: LedgerSequence,
    previous_entry_digest: str | None) -> str:
    return _hash({"entry_id": entry_id, "chain_id": chain_id, "sequence": sequence,
        "evidence_sha256": request.evidence_sha256, "evidence_type": request.evidence_type,
        "producer_id": request.producer_id, "evaluation_run_id": request.evaluation_run_id,
        "admission_decision_id": request.admission_decision_id, "provenance_reference": request.provenance_reference,
        "evidence_contract_version": request.evidence_contract_version,
        "admission_contract_version": request.admission_contract_version,
        "ledger_contract_version": request.ledger_contract_version, "policy_version": request.policy_version,
        "recorded_at": request.recorded_at.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "previous_entry_digest": previous_entry_digest, "supersedes_entry_id": request.supersedes_entry_id})

def request_from_evidence_ledger_entry(entry: EvidenceLedgerEntry) -> EvidenceLedgerAppendRequest:
    return EvidenceLedgerAppendRequest(entry.evidence_sha256, entry.evidence_type, entry.producer_id,
        entry.evaluation_run_id, entry.admission_decision_id, entry.provenance_reference,
        entry.evidence_contract_version, entry.admission_contract_version, entry.ledger_contract_version,
        entry.policy_version, entry.recorded_at, entry.supersedes_entry_id)
