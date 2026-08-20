from __future__ import annotations

import pytest

from src.report_capabilities import (
    capability_schema_versions,
    supports_report_schema,
    supports_schema_version,
)


def test_known_schema_version_is_supported() -> None:
    assert supports_schema_version("1.0") is True


def test_unknown_schema_version_is_not_supported() -> None:
    assert supports_schema_version("2.0") is False


def test_every_advertised_schema_version_is_supported() -> None:
    for schema_version in capability_schema_versions():
        assert supports_schema_version(schema_version) is True


def test_report_with_supported_schema_is_compatible() -> None:
    report = {
        "schema_version": "1.0",
    }

    assert supports_report_schema(report) is True


def test_report_with_unknown_schema_is_not_compatible() -> None:
    report = {
        "schema_version": "999.0",
    }

    assert supports_report_schema(report) is False


def test_report_schema_version_must_be_string() -> None:
    report = {
        "schema_version": 1,
    }

    with pytest.raises(
        ValueError,
        match="Public report schema_version must be a string.",
    ):
        supports_report_schema(report)