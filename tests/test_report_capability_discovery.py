from __future__ import annotations

from src.report_capabilities import (
    capability_schema_versions,
    report_capabilities,
    report_supports_capability,
)
from src.report_contract_validator import (
    supported_report_schema_versions,
)


def test_capability_versions_match_supported_schema_versions() -> None:
    for schema_version in supported_report_schema_versions():
        assert report_capabilities(schema_version)


def test_unsupported_schema_version_has_no_capabilities() -> None:
    assert report_capabilities("9.0") == ()


def test_unsupported_schema_version_supports_no_capability() -> None:
    assert report_supports_capability("9.0", "summary") is False


def test_public_report_v1_declares_supported_capabilities() -> None:
    assert report_capabilities("1.0") == (
        "report",
        "summary",
        "decision",
        "assessment",
    )


def test_public_report_v1_supports_known_capability() -> None:
    assert report_supports_capability("1.0", "summary") is True


def test_public_report_v1_rejects_unknown_capability() -> None:
    assert report_supports_capability(
        "1.0",
        "internal_scoring_engine",
    ) is False


def test_capability_catalog_matches_supported_schema_catalog() -> None:
    assert capability_schema_versions() == supported_report_schema_versions()