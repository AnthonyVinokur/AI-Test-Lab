from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum


TRANSPARENCY_CONTRACT_VERSION = "1.0"
TRANSPARENCY_DIGEST_ALGORITHM = "sha256"
TRANSPARENCY_SERIALIZATION_ALGORITHM = "canonical-json-rfc8259"
_ID = re.compile(r"[^\s\x00-\x1f\x7f]{1,256}")
_DIGEST = re.compile(r"[0-9a-f]{64}")


def transparency_identifier(value: object, name: str) -> str:
    if type(value) is not str or _ID.fullmatch(value) is None:
        raise ValueError(f"{name} must be a visible identifier of 1-256 characters.")
    return value


def transparency_digest(value: object, name: str) -> str:
    if type(value) is not str or _DIGEST.fullmatch(value) is None:
        raise ValueError(f"{name} must be a lowercase SHA-256 digest.")
    return value


def transparency_utc(value: object, name: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware.")
    normalized = value.astimezone(timezone.utc)
    if normalized.microsecond:
        raise ValueError(f"{name} must use whole UTC seconds.")
    return normalized


class TransparencyOperation(str, Enum):
    APPEND = "append"
    CHECKPOINT = "checkpoint"


@dataclass(frozen=True, slots=True)
class TransparencyEntry:
    log_id: str
    receipt_id: str
    release_manifest_id: str
    evidence_package_id: str
    lifecycle_event_id: str
    lifecycle_event_digest: str
    lifecycle_chain_head: str
    lifecycle_chain_length: int
    environment: str
    recorded_at: datetime
    contract_version: str = TRANSPARENCY_CONTRACT_VERSION
    serialization_algorithm: str = TRANSPARENCY_SERIALIZATION_ALGORITHM
    digest_algorithm: str = TRANSPARENCY_DIGEST_ALGORITHM

    def __post_init__(self) -> None:
        transparency_identifier(self.log_id, "log_id")
        transparency_identifier(self.environment, "environment")
        for value, name in (
            (self.receipt_id, "receipt_id"),
            (self.release_manifest_id, "release_manifest_id"),
            (self.evidence_package_id, "evidence_package_id"),
            (self.lifecycle_event_id, "lifecycle_event_id"),
            (self.lifecycle_event_digest, "lifecycle_event_digest"),
            (self.lifecycle_chain_head, "lifecycle_chain_head"),
        ):
            transparency_digest(value, name)
        if type(self.lifecycle_chain_length) is not int or self.lifecycle_chain_length < 1:
            raise ValueError("lifecycle_chain_length must be a positive integer.")
        object.__setattr__(self, "recorded_at", transparency_utc(self.recorded_at, "recorded_at"))
        if self.contract_version != TRANSPARENCY_CONTRACT_VERSION:
            raise ValueError("contract_version is unsupported.")
        if self.serialization_algorithm != TRANSPARENCY_SERIALIZATION_ALGORITHM:
            raise ValueError("serialization_algorithm is unsupported.")
        if self.digest_algorithm != TRANSPARENCY_DIGEST_ALGORITHM:
            raise ValueError("digest_algorithm is unsupported.")
