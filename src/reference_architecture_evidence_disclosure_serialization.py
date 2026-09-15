from __future__ import annotations

import json
from dataclasses import asdict
from hashlib import sha256
from typing import Any, Mapping

from src.reference_architecture_evidence_disclosure_contract import EvidenceDisclosureRelease


def canonical_disclosure_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def disclosure_digest(value: Any) -> str:
    return sha256(canonical_disclosure_json_bytes(value)).hexdigest()


def disclosure_release_document(release: EvidenceDisclosureRelease) -> dict[str, Any]:
    if not isinstance(release, EvidenceDisclosureRelease): raise TypeError("release must be an EvidenceDisclosureRelease.")
    return asdict(release)


def serialize_disclosure_release(release: EvidenceDisclosureRelease) -> bytes:
    return canonical_disclosure_json_bytes(disclosure_release_document(release))


def parse_disclosure_document(value: bytes | str | Mapping[str, Any]) -> tuple[dict[str, Any], bytes | None]:
    if isinstance(value, Mapping): return dict(value), None
    raw = value.encode("utf-8") if isinstance(value, str) else value
    if not isinstance(raw, bytes): raise ValueError
    decoded = json.loads(raw.decode("utf-8"))
    if not isinstance(decoded, dict): raise ValueError
    return decoded, raw
