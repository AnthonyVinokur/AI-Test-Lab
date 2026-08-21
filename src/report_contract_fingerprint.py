from __future__ import annotations

import hashlib
import json
from pathlib import Path

from src.report_contract_validator import (
    is_report_schema_version_supported,
    report_schema_filename,
)

PUBLIC_REPORT_FINGERPRINT_ALGORITHM = "sha256"


def public_report_contract_fingerprint(
    schema_version: str,
) -> str:
    """Return the deterministic fingerprint of a public report contract."""

    if not is_report_schema_version_supported(schema_version):
        raise ValueError(
            f"Unsupported public report schema version: {schema_version}"
        )

    schema_filename = report_schema_filename(schema_version)

    schema_path = (
        Path(__file__).resolve().parent.parent
        / "schemas"
        / schema_filename
    )

    schema = json.loads(
        schema_path.read_text(encoding="utf-8")
    )

    canonical_schema = json.dumps(
        schema,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )

    digest = hashlib.sha256(
        canonical_schema.encode("utf-8")
    ).hexdigest()

    return f"{PUBLIC_REPORT_FINGERPRINT_ALGORITHM}:{digest}"
