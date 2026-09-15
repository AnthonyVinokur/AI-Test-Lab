from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping


EVIDENCE_PACKAGE_FORMAT_VERSION = "1.0"
EVIDENCE_PACKAGE_HASH_ALGORITHM = "sha256"
_ID = re.compile(r"[^\s\x00-\x1f\x7f]{1,256}")
_DIGEST = re.compile(r"[0-9a-f]{64}")


class PackageStatus(str, Enum):
    VALID = "valid"
    INVALID = "invalid"
    REJECTED = "rejected"
    ERROR = "error"


class PackageReasonCode(str, Enum):
    PACKAGE_VALID = "package_valid"
    MALFORMED_REQUEST = "malformed_request"
    UNSUPPORTED_PACKAGE_VERSION = "unsupported_package_version"
    LEDGER_NOT_FOUND = "ledger_not_found"
    EVIDENCE_NOT_FOUND = "evidence_not_found"
    EVIDENCE_NOT_ADMITTED = "evidence_not_admitted"
    LEDGER_VERIFICATION_FAILED = "ledger_verification_failed"
    UNAUTHORIZED_SELECTION = "unauthorized_selection"
    EMPTY_SELECTION = "empty_selection"
    DUPLICATE_EVIDENCE_REFERENCE = "duplicate_evidence_reference"
    MANIFEST_MISMATCH = "manifest_mismatch"
    PACKAGE_DIGEST_MISMATCH = "package_digest_mismatch"
    EVIDENCE_DIGEST_MISMATCH = "evidence_digest_mismatch"
    CHAIN_PROOF_INVALID = "chain_proof_invalid"
    RUN_BINDING_MISMATCH = "run_binding_mismatch"
    ADMISSION_BINDING_MISMATCH = "admission_binding_mismatch"
    PACKAGE_INCOMPLETE = "package_incomplete"
    UNSUPPORTED_ALGORITHM = "unsupported_algorithm"
    INTERNAL_PACKAGE_ERROR = "internal_package_error"


def _identifier(value: object, name: str) -> str:
    if type(value) is not str or _ID.fullmatch(value) is None:
        raise ValueError(f"{name} must contain 1-256 visible non-whitespace characters.")
    return value


def _digest(value: object, name: str) -> str:
    if type(value) is not str or _DIGEST.fullmatch(value) is None:
        raise ValueError(f"{name} must be 64 lowercase hexadecimal characters.")
    return value


def _metadata(value: object) -> dict[str, str]:
    if not isinstance(value, Mapping) or len(value) > 32:
        raise ValueError("metadata must be an object with at most 32 entries.")
    result: dict[str, str] = {}
    for key, item in value.items():
        result[_identifier(key, "metadata key")] = _identifier(item, "metadata value")
    return result


@dataclass(frozen=True, slots=True)
class EvidencePackageRequest:
    ledger_id: str
    evidence_ids: tuple[str, ...] = ()
    run_id: str | None = None
    sequence_start: int | None = None
    sequence_end: int | None = None
    format_version: str = EVIDENCE_PACKAGE_FORMAT_VERSION
    metadata: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _digest(self.ledger_id, "ledger_id")
        if not isinstance(self.evidence_ids, tuple):
            raise ValueError("evidence_ids must be a tuple.")
        for item in self.evidence_ids:
            _digest(item, "evidence_id")
        if len(set(self.evidence_ids)) != len(self.evidence_ids):
            raise ValueError("evidence_ids must not contain duplicates.")
        if self.run_id is not None:
            _identifier(self.run_id, "run_id")
        for value, name in ((self.sequence_start, "sequence_start"), (self.sequence_end, "sequence_end")):
            if value is not None and (type(value) is not int or value < 1):
                raise ValueError(f"{name} must be a positive integer.")
        if self.sequence_start is not None and self.sequence_end is not None and self.sequence_start > self.sequence_end:
            raise ValueError("sequence_start must not exceed sequence_end.")
        _identifier(self.format_version, "format_version")
        object.__setattr__(self, "metadata", _metadata(self.metadata))


@dataclass(frozen=True, slots=True)
class PackagedEvidenceRecord:
    evidence_id: str
    ledger_id: str
    sequence: int
    evidence_digest: str
    evidence_type: str
    producer_id: str
    run_id: str
    admission_reference: str
    provenance_reference: str
    evidence_contract_version: str
    admission_contract_version: str
    ledger_contract_version: str
    policy_version: str
    recorded_at: str
    previous_entry_digest: str | None
    entry_digest: str
    supersedes_evidence_id: str | None


@dataclass(frozen=True, slots=True)
class EvidencePackageManifest:
    format_version: str
    package_id: str
    ledger_id: str
    evidence_ids: tuple[str, ...]
    run_ids: tuple[str, ...]
    admission_references: tuple[str, ...]
    sequence_start: int
    sequence_end: int
    entry_count: int
    hash_algorithm: str
    ledger_head_digest: str
    content_digest: str
    selection: Mapping[str, Any]
    metadata: Mapping[str, str]


@dataclass(frozen=True, slots=True)
class EvidencePackage:
    manifest: EvidencePackageManifest
    records: tuple[PackagedEvidenceRecord, ...]
    package_digest: str


@dataclass(frozen=True, slots=True)
class PackageVerificationRequest:
    package: EvidencePackage | bytes | str | Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class PackageVerificationResult:
    status: PackageStatus
    reason_code: PackageReasonCode
    package_id: str | None = None
    affected_evidence_id: str | None = None
    diagnostic: str | None = None

    @property
    def verified(self) -> bool:
        return self.status is PackageStatus.VALID and self.reason_code is PackageReasonCode.PACKAGE_VALID


@dataclass(frozen=True, slots=True)
class EvidencePackageBuildResult:
    status: PackageStatus
    reason_code: PackageReasonCode
    package: EvidencePackage | None = None
    diagnostic: str | None = None

    @property
    def built(self) -> bool:
        return self.status is PackageStatus.VALID and self.package is not None
