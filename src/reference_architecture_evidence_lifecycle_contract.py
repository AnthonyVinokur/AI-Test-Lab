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


class LifecycleEventType(str, Enum):
    ISSUED = "issued"
    SUSPENDED = "suspended"
    REINSTATED = "reinstated"
    REVOKED = "revoked"
    EXPIRED = "expired"
    SUPERSEDED = "superseded"


class LifecycleReasonCategory(str, Enum):
    RELEASE_ISSUED = "release_issued"
    ADMINISTRATIVE_REVIEW = "administrative_review"
    REVIEW_COMPLETED = "review_completed"
    AUTHORIZATION_WITHDRAWN = "authorization_withdrawn"
    VALIDITY_PERIOD_ENDED = "validity_period_ended"
    REPLACEMENT_AVAILABLE = "replacement_available"
    SECURITY_EVENT = "security_event"


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


@dataclass(frozen=True, slots=True)
class LifecycleEvent:
    receipt_id: str
    release_manifest_digest: str
    evidence_package_id: str
    event_type: LifecycleEventType
    effective_at: datetime
    issuer_id: str
    authority_id: str
    environment: str
    reason_category: LifecycleReasonCategory
    previous_event_id: str | None
    replacement_receipt_id: str | None
    replacement_package_id: str | None
    event_digest: str
    contract_version: str = LIFECYCLE_CONTRACT_VERSION
    serialization_algorithm: str = LIFECYCLE_SERIALIZATION_ALGORITHM
    digest_algorithm: str = LIFECYCLE_DIGEST_ALGORITHM

    def __post_init__(self) -> None:
        for value, name in (
            (self.receipt_id, "receipt_id"),
            (self.release_manifest_digest, "release_manifest_digest"),
            (self.evidence_package_id, "evidence_package_id"),
            (self.event_digest, "event_digest"),
        ):
            lifecycle_digest(value, name)
        for value, name in (
            (self.issuer_id, "issuer_id"),
            (self.authority_id, "authority_id"),
            (self.environment, "environment"),
        ):
            lifecycle_identifier(value, name)
        if not isinstance(self.event_type, LifecycleEventType):
            raise ValueError("event_type is unsupported.")
        if not isinstance(self.reason_category, LifecycleReasonCategory):
            raise ValueError("reason_category is unsupported.")
        object.__setattr__(self, "effective_at", lifecycle_utc(self.effective_at, "effective_at"))
        if self.previous_event_id is not None:
            lifecycle_digest(self.previous_event_id, "previous_event_id")
        if self.replacement_receipt_id is not None:
            lifecycle_digest(self.replacement_receipt_id, "replacement_receipt_id")
        if self.replacement_package_id is not None:
            lifecycle_digest(self.replacement_package_id, "replacement_package_id")
        replacements = self.replacement_receipt_id is not None or self.replacement_package_id is not None
        if replacements != (self.event_type is LifecycleEventType.SUPERSEDED):
            raise ValueError("replacement references are required only for supersession events.")
        if self.event_type is LifecycleEventType.SUPERSEDED and (
            self.replacement_receipt_id is None or self.replacement_package_id is None
        ):
            raise ValueError("supersession requires both replacement references.")
        if self.contract_version != LIFECYCLE_CONTRACT_VERSION:
            raise ValueError("contract_version is unsupported.")
        if self.serialization_algorithm != LIFECYCLE_SERIALIZATION_ALGORITHM:
            raise ValueError("serialization_algorithm is unsupported.")
        if self.digest_algorithm != LIFECYCLE_DIGEST_ALGORITHM:
            raise ValueError("digest_algorithm is unsupported.")
