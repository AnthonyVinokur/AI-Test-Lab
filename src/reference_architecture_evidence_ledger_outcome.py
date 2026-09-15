from __future__ import annotations

import json
from typing import Literal

from pydantic import model_validator

from src.public_contract import PublicContractModel, serialize_public_contract
from src.reference_architecture_evidence_ledger_contract import (
    REFERENCE_ARCHITECTURE_EVIDENCE_LEDGER_CONTRACT_VERSION, EvidenceLedgerAppendResult,
    EvidenceLedgerVerificationResult, LedgerEntryStatus, LedgerFailureReason,
)

class EvidenceLedgerPublicOutcomeV1(PublicContractModel):
    contract_version: Literal["1.0"] = REFERENCE_ARCHITECTURE_EVIDENCE_LEDGER_CONTRACT_VERSION
    status: LedgerEntryStatus
    reason_code: LedgerFailureReason
    ledger_entry_id: str | None = None
    evidence_chain_id: str | None = None
    sequence_number: int | None = None
    evidence_sha256: str | None = None
    evaluation_run_id: str | None = None
    recorded_at: str | None = None
    verification_state: Literal["verified", "not_verified"]

    @model_validator(mode="after")
    def validate_public_state(self) -> "EvidenceLedgerPublicOutcomeV1":
        fields = (self.ledger_entry_id, self.evidence_chain_id, self.sequence_number,
            self.evidence_sha256, self.evaluation_run_id, self.recorded_at)
        successful = self.status in {LedgerEntryStatus.RECORDED, LedgerEntryStatus.ALREADY_RECORDED}
        if successful != all(value is not None for value in fields):
            raise ValueError("Only successful outcomes may expose a complete recorded entry.")
        if not successful and any(value is not None for value in fields):
            raise ValueError("Failed outcomes cannot expose partial ledger state.")
        if self.verification_state == "verified" and not successful:
            raise ValueError("Only successful outcomes can be verified.")
        return self

def project_evidence_ledger_outcome(result: EvidenceLedgerAppendResult,
    verification: EvidenceLedgerVerificationResult | None = None) -> EvidenceLedgerPublicOutcomeV1:
    if not isinstance(result, EvidenceLedgerAppendResult): raise TypeError("result must be an internal ledger result.")
    entry = result.entry
    return EvidenceLedgerPublicOutcomeV1(status=result.status, reason_code=result.reason,
        ledger_entry_id=None if entry is None else entry.entry_id,
        evidence_chain_id=None if entry is None else entry.chain_id,
        sequence_number=None if entry is None else entry.sequence,
        evidence_sha256=None if entry is None else entry.evidence_sha256,
        evaluation_run_id=None if entry is None else entry.evaluation_run_id,
        recorded_at=None if entry is None else entry.recorded_at.isoformat(timespec="seconds").replace("+00:00", "Z"),
        verification_state="verified" if verification is not None and verification.verified else "not_verified")

def encode_evidence_ledger_outcome(outcome: EvidenceLedgerPublicOutcomeV1) -> bytes:
    return json.dumps(serialize_public_contract(outcome), sort_keys=True, separators=(",", ":"),
        ensure_ascii=False, allow_nan=False).encode("utf-8")

def decode_evidence_ledger_outcome(document: bytes) -> EvidenceLedgerPublicOutcomeV1:
    if type(document) is not bytes: raise TypeError("document must be bytes.")
    return EvidenceLedgerPublicOutcomeV1.model_validate_json(document)
