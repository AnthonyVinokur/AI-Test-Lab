from __future__ import annotations

import pytest

from src.report_capabilities import supports_capability


@pytest.mark.parametrize(
    "capability",
    [
        "report",
        "summary",
        "decision",
        "assessment",
    ],
)
def test_supported_report_can_consume_known_capability(
    capability: str,
) -> None:
    report = {
        "schema_version": "1.0",
    }

    assert supports_capability(report, capability) is True


def test_unsupported_report_version_supports_no_capability() -> None:
    report = {
        "schema_version": "9.0",
    }

    assert supports_capability(report, "summary") is False


def test_unknown_capability_is_not_exposed() -> None:
    report = {
        "schema_version": "1.0",
    }

    assert supports_capability(
        report,
        "internal_scoring_engine",
    ) is False


def test_missing_schema_version_is_rejected() -> None:
    report = {}

    with pytest.raises(
        ValueError,
        match="schema_version",
    ):
        supports_capability(report, "summary")


def test_non_string_schema_version_is_rejected() -> None:
    report = {
        "schema_version": 1,
    }

    with pytest.raises(
        ValueError,
        match="schema_version",
    ):
        supports_capability(report, "summary")


def test_non_string_capability_is_rejected() -> None:
    report = {
        "schema_version": "1.0",
    }

    with pytest.raises(
        ValueError,
        match="capability",
    ):
        supports_capability(report, 123)  # type: ignore[arg-type]