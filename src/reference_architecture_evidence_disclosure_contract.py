from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum

from src.reference_architecture_evidence_package_contract import EvidencePackage


DISCLOSURE_CONTRACT_VERSION = "1.0"
DISCLOSURE_SCHEMA_VERSION = "1.0"
DISCLOSURE_HASH_ALGORITHM = "sha256"
_ID = re.compile(r"[^\s\x00-\x1f\x7f]{1,256}")
_DIGEST = re.compile(r"[0-9a-f]{64}")


class DisclosureDecision(str, Enum):
    RELEASED = "RELEASED"
    DENIED = "DENIED"
    INVALID_REQUEST = "INVALID_REQUEST"
    AUTHORIZATION_MISMATCH = "AUTHORIZATION_MISMATCH"
    SCOPE_EXCEEDED = "SCOPE_EXCEEDED"
    LIFECYCLE_RESTRICTED = "LIFECYCLE_RESTRICTED"
    UNSUPPORTED_VERSION = "UNSUPPORTED_VERSION"
    INTEGRITY_FAILURE = "INTEGRITY_FAILURE"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class DisclosureReasonCode(str, Enum):
    RELEASE_CREATED = "release_created"
    MALFORMED_REQUEST = "malformed_request"
    AUTHORIZATION_DENIED = "authorization_denied"
    AUTHORIZATION_BINDING_MISMATCH = "authorization_binding_mismatch"
    AUTHORIZATION_EXPIRED = "authorization_expired"
    AUTHORIZATION_REVOKED = "authorization_revoked"
    SCOPE_EXCEEDED = "scope_exceeded"
    PROTECTED_FIELD_REQUESTED = "protected_field_requested"
    LIFECYCLE_RESTRICTED = "lifecycle_restricted"
    UNSUPPORTED_VERSION = "unsupported_version"
    UNSUPPORTED_FORMAT = "unsupported_format"
    UNSUPPORTED_ALGORITHM = "unsupported_algorithm"
    PACKAGE_INTEGRITY_FAILURE = "package_integrity_failure"
    RELEASE_INTEGRITY_FAILURE = "release_integrity_failure"
    REPLAY_DETECTED = "replay_detected"
    INTERNAL_DISCLOSURE_ERROR = "internal_disclosure_error"


def identifier(value: object, name: str) -> str:
    if type(value) is not str or _ID.fullmatch(value) is None:
        raise ValueError(f"{name} must be a visible identifier of 1-256 characters.")
    return value


def digest(value: object, name: str) -> str:
    if type(value) is not str or _DIGEST.fullmatch(value) is None:
        raise ValueError(f"{name} must be a lowercase SHA-256 digest.")
    return value


def utc(value: object, name: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware.")
    return value.astimezone(timezone.utc)


@dataclass(frozen=True, slots=True)
class DisclosureRequest:
    request_id: str
    requester_id: str
    recipient_id: str
    purpose: str
    environment: str
    package: EvidencePackage
    requested_record_ids: tuple[str, ...]
    requested_fields: tuple[str, ...]
    output_format: str
    authorization_id: str
    requested_at: datetime
    contract_version: str = DISCLOSURE_CONTRACT_VERSION

    def __post_init__(self) -> None:
        for value, name in ((self.request_id, "request_id"), (self.requester_id, "requester_id"),
                            (self.recipient_id, "recipient_id"), (self.purpose, "purpose"),
                            (self.environment, "environment"), (self.authorization_id, "authorization_id"),
                            (self.contract_version, "contract_version")):
            identifier(value, name)
        if not isinstance(self.package, EvidencePackage): raise ValueError("package must be an EvidencePackage.")
        if not self.requested_record_ids or len(set(self.requested_record_ids)) != len(self.requested_record_ids):
            raise ValueError("requested_record_ids must be a non-empty duplicate-free tuple.")
        for value in self.requested_record_ids: digest(value, "requested record id")
        if not self.requested_fields or len(set(self.requested_fields)) != len(self.requested_fields):
            raise ValueError("requested_fields must be a non-empty duplicate-free tuple.")
        for value in self.requested_fields: identifier(value, "requested field")
        if self.output_format != "json": raise ValueError("output_format is unsupported.")
        object.__setattr__(self, "requested_at", utc(self.requested_at, "requested_at"))


@dataclass(frozen=True, slots=True)
class DisclosureAuthorization:
    authorization_id: str
    decision_id: str
    granted: bool
    requester_id: str
    recipient_id: str
    package_id: str
    package_digest: str
    purpose: str
    environment: str
    authorized_record_ids: frozenset[str]
    authorized_fields: frozenset[str]
    issued_at: datetime
    expires_at: datetime
    revoked: bool = False
    one_time: bool = False

    def __post_init__(self) -> None:
        for value, name in ((self.authorization_id, "authorization_id"), (self.decision_id, "decision_id"),
                            (self.requester_id, "requester_id"), (self.recipient_id, "recipient_id"),
                            (self.purpose, "purpose"), (self.environment, "environment")):
            identifier(value, name)
        digest(self.package_id, "package_id"); digest(self.package_digest, "package_digest")
        if type(self.granted) is not bool or type(self.revoked) is not bool or type(self.one_time) is not bool:
            raise ValueError("authorization flags must be booleans.")
        if not self.authorized_record_ids or not self.authorized_fields: raise ValueError("authorization scope is empty.")
        for value in self.authorized_record_ids: digest(value, "authorized record id")
        for value in self.authorized_fields: identifier(value, "authorized field")
        object.__setattr__(self, "issued_at", utc(self.issued_at, "issued_at"))
        object.__setattr__(self, "expires_at", utc(self.expires_at, "expires_at"))
        if self.expires_at <= self.issued_at: raise ValueError("authorization expiry must follow issue time.")


@dataclass(frozen=True, slots=True)
class PublicEvidenceRecord:
    evidence_id: str
    fields: tuple[tuple[str, str | int | None], ...]


@dataclass(frozen=True, slots=True)
class DisclosureManifest:
    schema_version: str
    release_id: str
    source_package_id: str
    source_package_digest: str
    authorization_decision_id: str
    disclosure_request_id: str
    requester_id: str
    recipient_id: str
    purpose: str
    environment: str
    disclosed_record_ids: tuple[str, ...]
    disclosed_fields: tuple[str, ...]
    released_at: str
    content_digest: str
    serialization_algorithm: str
    digest_algorithm: str


@dataclass(frozen=True, slots=True)
class DisclosureReceipt:
    receipt_version: str
    release_id: str
    source_package_id: str
    authorization_decision_id: str
    disclosure_request_id: str
    recipient_id: str
    purpose: str
    released_at: str
    content_digest: str
    manifest_digest: str
    receipt_digest: str
    statement: str = "This receipt proves what was released; it does not certify correctness, safety, compliance, or production approval."


@dataclass(frozen=True, slots=True)
class EvidenceDisclosureRelease:
    manifest: DisclosureManifest
    records: tuple[PublicEvidenceRecord, ...]
    receipt: DisclosureReceipt


@dataclass(frozen=True, slots=True)
class DisclosureOutcome:
    decision: DisclosureDecision
    reason_code: DisclosureReasonCode
    release: EvidenceDisclosureRelease | None = None

    @property
    def released(self) -> bool:
        return self.decision is DisclosureDecision.RELEASED and self.release is not None


@dataclass(frozen=True, slots=True)
class DisclosureVerificationResult:
    verified: bool
    decision: DisclosureDecision
    reason_code: DisclosureReasonCode
    release_id: str | None = None
