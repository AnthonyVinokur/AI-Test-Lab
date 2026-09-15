from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any, Mapping

from src.reference_architecture_evidence_lifecycle_contract import (
    LIFECYCLE_CONTRACT_VERSION,
    LIFECYCLE_DIGEST_ALGORITHM,
    LIFECYCLE_SERIALIZATION_ALGORITHM,
    LifecycleEvent,
    LifecycleEventType,
    LifecycleReasonCategory,
)


class LifecycleDocumentError(ValueError):
    pass


_FIELDS = frozenset(LifecycleEvent.__dataclass_fields__)


def canonical_lifecycle_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")


def lifecycle_sha256(value: Any) -> str:
    return sha256(canonical_lifecycle_json_bytes(value)).hexdigest()


def canonical_timestamp(value: datetime) -> str:
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")


def lifecycle_event_seed(event: LifecycleEvent) -> dict[str, Any]:
    document = asdict(event)
    document["event_type"] = event.event_type.value
    document["reason_category"] = event.reason_category.value
    document["effective_at"] = canonical_timestamp(event.effective_at)
    document.pop("event_digest")
    return document


def expected_event_digest(event: LifecycleEvent) -> str:
    return lifecycle_sha256(lifecycle_event_seed(event))


def lifecycle_event_document(event: LifecycleEvent) -> dict[str, Any]:
    document = lifecycle_event_seed(event)
    document["event_digest"] = event.event_digest
    return document


def serialize_lifecycle_event(event: LifecycleEvent) -> bytes:
    if not isinstance(event, LifecycleEvent) or event.event_digest != expected_event_digest(event):
        raise LifecycleDocumentError("Lifecycle event integrity could not be verified.")
    return canonical_lifecycle_json_bytes(lifecycle_event_document(event))


def build_lifecycle_event(**values: Any) -> LifecycleEvent:
    values = dict(values)
    values.setdefault("contract_version", LIFECYCLE_CONTRACT_VERSION)
    values.setdefault("serialization_algorithm", LIFECYCLE_SERIALIZATION_ALGORITHM)
    values.setdefault("digest_algorithm", LIFECYCLE_DIGEST_ALGORITHM)
    values["event_digest"] = "0" * 64
    draft = LifecycleEvent(**values)
    values["event_digest"] = expected_event_digest(draft)
    return LifecycleEvent(**values)


def translate_untrusted_lifecycle_event(value: bytes | str | Mapping[str, Any]) -> LifecycleEvent:
    try:
        raw: bytes | None = None
        if isinstance(value, Mapping):
            document = dict(value)
        else:
            raw = value.encode("utf-8") if isinstance(value, str) else value
            if not isinstance(raw, bytes):
                raise ValueError
            document = json.loads(raw.decode("utf-8"))
        if not isinstance(document, dict) or set(document) != _FIELDS:
            raise ValueError
        timestamp = document["effective_at"]
        if type(timestamp) is not str or len(timestamp) != 20 or not timestamp.endswith("Z"):
            raise ValueError
        effective_at = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        event = LifecycleEvent(
            **{**document, "effective_at": effective_at,
               "event_type": LifecycleEventType(document["event_type"]),
               "reason_category": LifecycleReasonCategory(document["reason_category"])}
        )
        if event.event_digest != expected_event_digest(event):
            raise ValueError
        if raw is not None and raw != canonical_lifecycle_json_bytes(document):
            raise ValueError
        return event
    except Exception as error:
        raise LifecycleDocumentError("Lifecycle event document is invalid.") from error
