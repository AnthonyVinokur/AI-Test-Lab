from __future__ import annotations

from src.report_capabilities import (
    capability_schema_versions,
    report_capabilities,
    report_supports_capability,
    supports_capability,
)


def test_every_advertised_capability_is_supported_by_version_api() -> None:
    for schema_version in capability_schema_versions():
        for capability in report_capabilities(schema_version):
            assert report_supports_capability(
                schema_version,
                capability,
            ) is True


def test_every_advertised_capability_is_consumable_from_report() -> None:
    for schema_version in capability_schema_versions():
        report = {
            "schema_version": schema_version,
        }

        for capability in report_capabilities(schema_version):
            assert supports_capability(
                report,
                capability,
            ) is True


def test_public_capability_catalog_contains_unique_non_empty_strings() -> None:
    for schema_version in capability_schema_versions():
        capabilities = report_capabilities(schema_version)

        assert capabilities
        assert len(capabilities) == len(set(capabilities))

        for capability in capabilities:
            assert isinstance(capability, str)
            assert capability.strip()


def test_report_cannot_self_declare_private_capability() -> None:
    report = {
        "schema_version": "1.0",
        "capabilities": (
            "report",
            "summary",
            "decision",
            "assessment",
            "internal_scoring_engine",
        ),
    }

    assert supports_capability(
        report,
        "internal_scoring_engine",
    ) is False


def test_report_supplied_capability_metadata_cannot_remove_public_capability() -> None:
    report = {
        "schema_version": "1.0",
        "capabilities": (),
    }

    assert supports_capability(report, "summary") is True
