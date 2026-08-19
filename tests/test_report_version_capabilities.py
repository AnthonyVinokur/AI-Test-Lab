from __future__ import annotations

from src.report_contract_validator import (
    is_report_schema_version_supported,
    supported_report_schema_versions,
)


def test_public_report_v1_is_supported() -> None:
    assert is_report_schema_version_supported("1.0") is True


def test_unpublished_report_version_is_not_supported() -> None:
    assert is_report_schema_version_supported("1.1") is False


def test_unknown_report_version_is_not_supported() -> None:
    assert is_report_schema_version_supported("9.0") is False


def test_supported_version_query_matches_version_catalog() -> None:
    for schema_version in supported_report_schema_versions():
        assert is_report_schema_version_supported(schema_version) is True