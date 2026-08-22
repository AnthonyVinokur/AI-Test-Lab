from __future__ import annotations

import hmac
import re

from src.report_contract_fingerprint import (
    public_report_contract_fingerprint,
)
from src.report_contract_validator import (
    is_report_schema_version_supported,
)

from pathlib import Path

from src.report_reader import load_report

_FINGERPRINT_PATTERN = re.compile(r"sha256:[0-9a-f]{64}")


def verify_public_report_contract_fingerprint(
    schema_version: str,
    fingerprint: str,
) -> bool:
    """Verify a supplied fingerprint against the supported public contract."""

    if not is_report_schema_version_supported(schema_version):
        raise ValueError(
            f"Unsupported public report schema version: {schema_version}"
        )

    if not isinstance(fingerprint, str) or not _FINGERPRINT_PATTERN.fullmatch(
        fingerprint
    ):
        raise ValueError(
            "Malformed public report contract fingerprint."
        )

    expected = public_report_contract_fingerprint(schema_version)

    return hmac.compare_digest(
        expected,
        fingerprint,
    )

def verify_public_report_contract_for_report(
    path: str | Path,
    fingerprint: str,
) -> bool:
    """Verify the contract fingerprint for a published public report."""

    report = load_report(path)

    return verify_public_report_contract_fingerprint(
        report.schema_version,
        fingerprint,
    )
