from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any, Mapping

from src.reference_architecture_transparency_contract import TransparencyEntry


class TransparencyDocumentError(ValueError):
    pass


_FIELDS = frozenset(TransparencyEntry.__dataclass_fields__)


def canonical_transparency_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def canonical_transparency_timestamp(value: datetime) -> str:
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")


def transparency_entry_document(entry: TransparencyEntry) -> dict[str, Any]:
    document = asdict(entry)
    document["recorded_at"] = canonical_transparency_timestamp(entry.recorded_at)
    return document


def serialize_transparency_entry(entry: TransparencyEntry) -> bytes:
    if not isinstance(entry, TransparencyEntry):
        raise TransparencyDocumentError("Transparency entry is invalid.")
    return canonical_transparency_json_bytes(transparency_entry_document(entry))


def transparency_entry_digest(entry: TransparencyEntry) -> str:
    return sha256(serialize_transparency_entry(entry)).hexdigest()


def translate_untrusted_transparency_entry(value: bytes | str | Mapping[str, Any]) -> TransparencyEntry:
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
        timestamp = document["recorded_at"]
        if type(timestamp) is not str or len(timestamp) != 20 or not timestamp.endswith("Z"):
            raise ValueError
        recorded_at = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        entry = TransparencyEntry(**{**document, "recorded_at": recorded_at})
        if raw is not None and raw != canonical_transparency_json_bytes(document):
            raise ValueError
        return entry
    except Exception as error:
        raise TransparencyDocumentError("Transparency entry document is invalid.") from error
