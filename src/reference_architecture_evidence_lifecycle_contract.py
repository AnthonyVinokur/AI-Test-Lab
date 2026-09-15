from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum


LIFECYCLE_CONTRACT_VERSION = "1.0"
LIFECYCLE_DIGEST_ALGORITHM = "sha256"
LIFECYCLE_SERIALIZATION_ALGORITHM = "canonical-json-rfc8259"
_ID = re.compile(r"[^\s\x00-\x1f\x7f]{1,256}")
_DIGEST = re.compile(r"[0-9a-f]{64}")


class LifecycleStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    REVOKED = "revoked"
    EXPIRED = "expired"
    SUPERSEDED = "superseded"
    UNKNOWN = "unknown"


def lifecycle_identifier(value: object, name: str) -> str:
    if type(value) is not str or _ID.fullmatch(value) is None:
        raise ValueError(f"{name} must be a visible identifier of 1-256 characters.")
    return value


def lifecycle_digest(value: object, name: str) -> str:
    if type(value) is not str or _DIGEST.fullmatch(value) is None:
        raise ValueError(f"{name} must be a lowercase SHA-256 digest.")
    return value


def lifecycle_utc(value: object, name: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware.")
    return value.astimezone(timezone.utc)


@dataclass(frozen=True, slots=True)
class LifecycleStatusContract:
    receipt_id: str
    release_manifest_digest: str
    evidence_package_id: str
    status: LifecycleStatus
    effective_at: datetime
    observed_at: datetime
    latest_event_id: str
    contract_version: str = LIFECYCLE_CONTRACT_VERSION

    def __post_init__(self) -> None:
        lifecycle_digest(self.receipt_id, "receipt_id")
        lifecycle_digest(self.release_manifest_digest, "release_manifest_digest")
        lifecycle_digest(self.evidence_package_id, "evidence_package_id")
        lifecycle_digest(self.latest_event_id, "latest_event_id")
        if not isinstance(self.status, LifecycleStatus):
            raise ValueError("status is unsupported.")
        object.__setattr__(self, "effective_at", lifecycle_utc(self.effective_at, "effective_at"))
        object.__setattr__(self, "observed_at", lifecycle_utc(self.observed_at, "observed_at"))
        if self.effective_at > self.observed_at:
            raise ValueError("effective_at cannot follow observed_at.")
        if self.contract_version != LIFECYCLE_CONTRACT_VERSION:
            raise ValueError("contract_version is unsupported.")

