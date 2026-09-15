from __future__ import annotations

from collections.abc import Sequence
from threading import RLock
from typing import Protocol

from src.reference_architecture_evidence_ledger_contract import (
    REFERENCE_ARCHITECTURE_EVIDENCE_LEDGER_CONTRACT_VERSION, EvidenceChainId,
    EvidenceLedgerAppendRequest, EvidenceLedgerAppendResult, EvidenceLedgerEntry,
    EvidenceLedgerEntryId, EvidenceLedgerVerificationResult, LedgerEntryStatus,
    LedgerFailureReason, LedgerSequence, LedgerVerificationStatus,
)
from src.reference_architecture_evidence_ledger_identity import (
    calculate_evidence_chain_id, calculate_evidence_ledger_entry_digest,
    calculate_evidence_ledger_entry_id, request_from_evidence_ledger_entry,
)

class EvidenceLedgerPort(Protocol):
    """Replaceable storage contract used by the trusted orchestration boundary."""
    def append(self, request: EvidenceLedgerAppendRequest) -> EvidenceLedgerAppendResult: ...
    def chain(self, chain_id: EvidenceChainId) -> tuple[EvidenceLedgerEntry, ...]: ...

class InMemoryEvidenceLedger:
    """Thread-safe reference adapter; persistence vendors must preserve these semantics."""
    def __init__(self) -> None:
        self._entries: dict[EvidenceLedgerEntryId, EvidenceLedgerEntry] = {}
        self._chains: dict[EvidenceChainId, list[EvidenceLedgerEntryId]] = {}
        self._admissions: dict[str, EvidenceLedgerEntryId] = {}
        self._evidence: dict[str, EvidenceLedgerEntryId] = {}
        self._lock = RLock()

    def append(self, request: EvidenceLedgerAppendRequest) -> EvidenceLedgerAppendResult:
        if not isinstance(request, EvidenceLedgerAppendRequest): raise TypeError("request must be an append request.")
        with self._lock:
            entry_id = calculate_evidence_ledger_entry_id(request)
            if entry_id in self._entries:
                return EvidenceLedgerAppendResult(LedgerEntryStatus.ALREADY_RECORDED,
                    LedgerFailureReason.IDEMPOTENT_REPLAY, self._entries[entry_id])
            if request.admission_decision_id in self._admissions:
                return EvidenceLedgerAppendResult(LedgerEntryStatus.CONFLICT,
                    LedgerFailureReason.ADMISSION_ALREADY_RECORDED)
            if request.evidence_sha256 in self._evidence and request.supersedes_entry_id is None:
                return EvidenceLedgerAppendResult(LedgerEntryStatus.REJECTED, LedgerFailureReason.DUPLICATE_ENTRY)

            previous: EvidenceLedgerEntry | None = None
            if request.supersedes_entry_id is not None:
                previous = self._entries.get(request.supersedes_entry_id)
                if previous is None: return EvidenceLedgerAppendResult(LedgerEntryStatus.CONFLICT, LedgerFailureReason.CHAIN_HEAD_MISMATCH)
                chain_id = previous.chain_id
                if self._chains[chain_id][-1] != previous.entry_id:
                    return EvidenceLedgerAppendResult(LedgerEntryStatus.CONFLICT, LedgerFailureReason.CHAIN_HEAD_MISMATCH)
                if (request.producer_id, request.evidence_type) != (previous.producer_id, previous.evidence_type):
                    return EvidenceLedgerAppendResult(LedgerEntryStatus.REJECTED, LedgerFailureReason.EVIDENCE_BINDING_MISMATCH)
            else:
                chain_id = calculate_evidence_chain_id(request)
                if chain_id in self._chains:
                    return EvidenceLedgerAppendResult(LedgerEntryStatus.CONFLICT, LedgerFailureReason.SEQUENCE_CONFLICT)

            sequence = LedgerSequence(1 if previous is None else previous.sequence + 1)
            prior_digest = None if previous is None else previous.entry_digest
            digest = calculate_evidence_ledger_entry_digest(request=request, entry_id=entry_id,
                chain_id=chain_id, sequence=sequence, previous_entry_digest=prior_digest)
            entry = EvidenceLedgerEntry(entry_id, chain_id, sequence, request.evidence_sha256,
                request.evidence_type, request.producer_id, request.evaluation_run_id,
                request.admission_decision_id, request.provenance_reference, request.evidence_contract_version,
                request.admission_contract_version, request.ledger_contract_version, request.policy_version,
                request.recorded_at, prior_digest, digest, request.supersedes_entry_id)
            self._entries[entry_id] = entry; self._chains.setdefault(chain_id, []).append(entry_id)
            self._admissions[request.admission_decision_id] = entry_id; self._evidence[request.evidence_sha256] = entry_id
            return EvidenceLedgerAppendResult(LedgerEntryStatus.RECORDED, LedgerFailureReason.NONE, entry)

    def get(self, entry_id: EvidenceLedgerEntryId) -> EvidenceLedgerEntry | None: return self._entries.get(entry_id)
    def chain(self, chain_id: EvidenceChainId) -> tuple[EvidenceLedgerEntry, ...]:
        return tuple(self._entries[item] for item in self._chains.get(chain_id, ()))

def verify_evidence_ledger_chain(entries: Sequence[EvidenceLedgerEntry]) -> EvidenceLedgerVerificationResult:
    if not isinstance(entries, Sequence) or not entries:
        return EvidenceLedgerVerificationResult(LedgerVerificationStatus.INVALID, LedgerFailureReason.SEQUENCE_CONFLICT)
    seen_ids: set[str] = set(); chain_id = entries[0].chain_id
    for offset, entry in enumerate(entries, 1):
        if not isinstance(entry, EvidenceLedgerEntry):
            return EvidenceLedgerVerificationResult(LedgerVerificationStatus.INVALID, LedgerFailureReason.INVALID_APPEND_REQUEST)
        if entry.ledger_contract_version != REFERENCE_ARCHITECTURE_EVIDENCE_LEDGER_CONTRACT_VERSION:
            return EvidenceLedgerVerificationResult(LedgerVerificationStatus.INVALID, LedgerFailureReason.UNSUPPORTED_CONTRACT_VERSION, entry.entry_id)
        if entry.entry_id in seen_ids or entry.chain_id != chain_id or entry.sequence != offset:
            return EvidenceLedgerVerificationResult(LedgerVerificationStatus.INVALID, LedgerFailureReason.SEQUENCE_CONFLICT, entry.entry_id)
        previous = None if offset == 1 else entries[offset - 2]
        if entry.previous_entry_digest != (None if previous is None else previous.entry_digest):
            return EvidenceLedgerVerificationResult(LedgerVerificationStatus.INVALID, LedgerFailureReason.CHAIN_HEAD_MISMATCH, entry.entry_id)
        request = request_from_evidence_ledger_entry(entry)
        if calculate_evidence_ledger_entry_id(request) != entry.entry_id:
            return EvidenceLedgerVerificationResult(LedgerVerificationStatus.INVALID, LedgerFailureReason.EVIDENCE_BINDING_MISMATCH, entry.entry_id)
        expected = calculate_evidence_ledger_entry_digest(request=request, entry_id=entry.entry_id,
            chain_id=entry.chain_id, sequence=entry.sequence, previous_entry_digest=entry.previous_entry_digest)
        if expected != entry.entry_digest:
            return EvidenceLedgerVerificationResult(LedgerVerificationStatus.INVALID, LedgerFailureReason.EVIDENCE_BINDING_MISMATCH, entry.entry_id)
        if previous is not None and entry.supersedes_entry_id != previous.entry_id:
            return EvidenceLedgerVerificationResult(LedgerVerificationStatus.INVALID, LedgerFailureReason.CHAIN_HEAD_MISMATCH, entry.entry_id)
        seen_ids.add(entry.entry_id)
    return EvidenceLedgerVerificationResult(LedgerVerificationStatus.VERIFIED, LedgerFailureReason.NONE)
