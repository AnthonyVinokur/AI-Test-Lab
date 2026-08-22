from __future__ import annotations

import pytest

from src.report_contract_fingerprint import (
    public_report_contract_fingerprint,
)
from src.report_contract_verification import (
    ReportContractCompatibility,
    verify_public_report_contract_compatibility,
)


def test_matching_contract_is_exact() -> None:
    fingerprint = public_report_contract_fingerprint("1.0")

    result = verify_public_report_contract_compatibility(
        expected_schema_version="1.0",
        published_schema_version="1.0",
        published_fingerprint=fingerprint,
    )

    assert result is ReportContractCompatibility.EXACT


def test_wrong_fingerprint_is_incompatible() -> None:
    result = verify_public_report_contract_compatibility(
        expected_schema_version="1.0",
        published_schema_version="1.0",
        published_fingerprint="sha256:" + "0" * 64,
    )

    assert result is ReportContractCompatibility.INCOMPATIBLE


def test_unknown_published_schema_is_incompatible() -> None:
    result = verify_public_report_contract_compatibility(
        expected_schema_version="1.0",
        published_schema_version="9.0",
        published_fingerprint="sha256:" + "0" * 64,
    )

    assert result is ReportContractCompatibility.INCOMPATIBLE


def test_unknown_expected_schema_is_rejected() -> None:
    fingerprint = public_report_contract_fingerprint("1.0")

    with pytest.raises(
        ValueError,
        match="Unsupported expected public report schema version",
    ):
        verify_public_report_contract_compatibility(
            expected_schema_version="9.0",
            published_schema_version="1.0",
            published_fingerprint=fingerprint,
        )


def test_malformed_published_fingerprint_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="Malformed public report contract fingerprint",
    ):
        verify_public_report_contract_compatibility(
            expected_schema_version="1.0",
            published_schema_version="1.0",
            published_fingerprint="invalid",
        )


def test_no_cross_version_compatibility_is_assumed() -> None:
    fingerprint = public_report_contract_fingerprint("1.0")

    result = verify_public_report_contract_compatibility(
        expected_schema_version="1.0",
        published_schema_version="1.0",
        published_fingerprint=fingerprint,
    )

    assert result is not ReportContractCompatibility.COMPATIBLE
