from __future__ import annotations

import json
from dataclasses import asdict
from hashlib import sha256
from typing import Any, Mapping

from src.reference_architecture_evidence_package_contract import EvidencePackage


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def sha256_digest(value: Any) -> str:
    return sha256(canonical_json_bytes(value)).hexdigest()


def evidence_package_document(package: EvidencePackage, *, include_package_digest: bool = True) -> dict[str, Any]:
    if not isinstance(package, EvidencePackage):
        raise TypeError("package must be an EvidencePackage.")
    document = asdict(package)
    if not include_package_digest:
        document.pop("package_digest")
    return document


def serialize_evidence_package(package: EvidencePackage) -> bytes:
    return canonical_json_bytes(evidence_package_document(package))


def parse_json_object(document: bytes | str | Mapping[str, Any]) -> tuple[dict[str, Any], bytes | None]:
    if isinstance(document, Mapping):
        return dict(document), None
    raw = document.encode("utf-8") if isinstance(document, str) else document
    if not isinstance(raw, bytes):
        raise ValueError("Package input must be UTF-8 JSON or an object.")
    value = json.loads(raw.decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Package JSON must contain an object.")
    return value, raw
