from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import NewType


REFERENCE_ARCHITECTURE_EVIDENCE_LEDGER_CONTRACT_NAME = "ai-test-lab.reference-architecture-evidence-ledger"
REFERENCE_ARCHITECTURE_EVIDENCE_LEDGER_CONTRACT_VERSION = "1.0"

EvidenceLedgerEntryId = NewType("EvidenceLedgerEntryId", str)
EvidenceChainId = NewType("EvidenceChainId", str)
LedgerSequence = NewType("LedgerSequence", int)

_IDENTITY = re.compile(r"[^\s\x00-\x1f\x7f]{1,256}")
_DIGEST = re.compile(r"[0-9a-f]{64}")


class LedgerEntryStatus(str, Enum):
    RECORDED = "recorded"
    ALREADY_RECORDED = "already_recorded"
    REJECTED = "rejected"
    CONFLICT = "conflict"
    ERROR = "error"


class LedgerFailureReason(str, Enum):
    NONE = "none"
    INVALID_APPEND_REQUEST = "invalid_append_request"
    ADMISSION_NOT_CONFIRMED = "admission_not_confirmed"
    ADMISSION_CONTRACT_UNSUPPORTED = "admission_contract_unsupported"
    ADMISSION_EXPIRED = "admission_expired"
    EVIDENCE_BINDING_MISMATCH = "evidence_binding_mismatch"
    IDEMPOTENT_REPLAY = "idempotent_replay"
    DUPLICATE_ENTRY = "duplicate_entry"
    ADMISSION_ALREADY_RECORDED = "admission_already_recorded"
    SEQUENCE_CONFLICT = "sequence_conflict"
    CHAIN_HEAD_MISMATCH = "chain_head_mismatch"
    UNSUPPORTED_CONTRACT_VERSION = "unsupported_contract_version"
    STORAGE_ERROR = "storage_error"


class LedgerVerificationStatus(str, Enum):
    VERIFIED = "verified"
    INVALID = "invalid"


def _id(value: object, name: str) -> str:
    if type(value) is not str or _IDENTITY.fullmatch(value) is None:
        raise ValueError(f"{name} must contain 1-256 visible non-whitespace characters.")
    return value


def _digest(value: object, name: str) -> str:
    if type(value) is not str or _DIGEST.fullmatch(value) is None:
        raise ValueError(f"{name} must be 64 lowercase hexadecimal characters.")
    return value


def _utc(value: object, name: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ValueError(f"{name} must be a timezone-aware datetime.")
    return value.astimezone(timezone.utc)


@dataclass(frozen=True, slots=True)
class EvidenceLedgerAppendRequest:
    evidence_sha256: str
    evidence_type: str
    producer_id: str
    evaluation_run_id: str
    admission_decision_id: str
    provenance_reference: str
    evidence_contract_version: str
    admission_contract_version: str
    ledger_contract_version: str
    policy_version: str
    recorded_at: datetime
    supersedes_entry_id: EvidenceLedgerEntryId | None = None

    def __post_init__(self) -> None:
        _digest(self.evidence_sha256, "evidence_sha256")
        for value, name in ((self.evidence_type, "evidence_type"), (self.producer_id, "producer_id"),
            (self.evaluation_run_id, "evaluation_run_id"), (self.admission_decision_id, "admission_decision_id"),
            (self.provenance_reference, "provenance_reference"), (self.evidence_contract_version, "evidence_contract_version"),
            (self.admission_contract_version, "admission_contract_version"), (self.ledger_contract_version, "ledger_contract_version"),
            (self.policy_version, "policy_version")):
            _id(value, name)
        object.__setattr__(self, "recorded_at", _utc(self.recorded_at, "recorded_at"))
        if self.supersedes_entry_id is not None:
            _digest(self.supersedes_entry_id, "supersedes_entry_id")


@dataclass(frozen=True, slots=True)
class EvidenceLedgerEntry:
    entry_id: EvidenceLedgerEntryId
    chain_id: EvidenceChainId
    sequence: LedgerSequence
    evidence_sha256: str
    evidence_type: str
    producer_id: str
    evaluation_run_id: str
    admission_decision_id: str
    provenance_reference: str
    evidence_contract_version: str
    admission_contract_version: str
    ledger_contract_version: str
    policy_version: str
    recorded_at: datetime
    previous_entry_digest: str | None
    entry_digest: str
    supersedes_entry_id: EvidenceLedgerEntryId | None = None

    def __post_init__(self) -> None:
        _digest(self.entry_id, "entry_id"); _digest(self.chain_id, "chain_id")
        _digest(self.evidence_sha256, "evidence_sha256"); _digest(self.entry_digest, "entry_digest")
        if type(self.sequence) is not int or self.sequence < 1:
            raise ValueError("sequence must be a positive integer.")
        if (self.sequence == 1) != (self.previous_entry_digest is None):
            raise ValueError("Only the first entry may omit previous_entry_digest.")
        if self.previous_entry_digest is not None: _digest(self.previous_entry_digest, "previous_entry_digest")
        EvidenceLedgerAppendRequest(self.evidence_sha256, self.evidence_type, self.producer_id,
            self.evaluation_run_id, self.admission_decision_id, self.provenance_reference,
            self.evidence_contract_version, self.admission_contract_version, self.ledger_contract_version,
            self.policy_version, self.recorded_at, self.supersedes_entry_id)


@dataclass(frozen=True, slots=True)
class EvidenceLedgerAppendResult:
    status: LedgerEntryStatus
    reason: LedgerFailureReason
    entry: EvidenceLedgerEntry | None = None

    def __post_init__(self) -> None:
        success = self.status in {LedgerEntryStatus.RECORDED, LedgerEntryStatus.ALREADY_RECORDED}
        if success != (self.entry is not None): raise ValueError("Successful ledger results require an entry.")
        if self.status is LedgerEntryStatus.RECORDED and self.reason is not LedgerFailureReason.NONE:
            raise ValueError("A newly recorded result cannot have a failure reason.")


@dataclass(frozen=True, slots=True)
class EvidenceLedgerVerificationResult:
    status: LedgerVerificationStatus
    reason: LedgerFailureReason
    affected_entry_id: EvidenceLedgerEntryId | None = None

    @property
    def verified(self) -> bool: return self.status is LedgerVerificationStatus.VERIFIED
