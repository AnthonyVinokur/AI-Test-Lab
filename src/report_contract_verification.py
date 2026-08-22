from __future__ import annotations

import hmac
import re
from enum import Enum
from pathlib import Path

from src.report_contract_fingerprint import (
    public_report_contract_fingerprint,
)
from src.report_contract_validator import (
    is_report_schema_version_supported,
)
from src.report_reader import load_report


_FINGERPRINT_PATTERN = re.compile(r"sha256:[0-9a-f]{64}")


class ReportContractCompatibility(str, Enum):
    """Compatibility relationship between public report contracts."""

    EXACT = "exact"
    COMPATIBLE = "compatible"
    INCOMPATIBLE = "incompatible"


_COMPATIBLE_REPORT_CONTRACTS: dict[str, frozenset[str]] = {
    "1.0": frozenset(),
}


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


def verify_public_report_contract_compatibility(
    expected_schema_version: str,
    published_schema_version: str,
    published_fingerprint: str,
) -> ReportContractCompatibility:
    """Determine whether a published public report contract is acceptable."""

    if not is_report_schema_version_supported(expected_schema_version):
        raise ValueError(
            "Unsupported expected public report schema version: "
            f"{expected_schema_version}"
        )

    if not is_report_schema_version_supported(published_schema_version):
        return ReportContractCompatibility.INCOMPATIBLE

    if not verify_public_report_contract_fingerprint(
        published_schema_version,
        published_fingerprint,
    ):
        return ReportContractCompatibility.INCOMPATIBLE

    if expected_schema_version == published_schema_version:
        return ReportContractCompatibility.EXACT

    compatible_versions = _COMPATIBLE_REPORT_CONTRACTS.get(
        expected_schema_version,
        frozenset(),
    )

    if published_schema_version in compatible_versions:
        return ReportContractCompatibility.COMPATIBLE

    return ReportContractCompatibility.INCOMPATIBLE


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
