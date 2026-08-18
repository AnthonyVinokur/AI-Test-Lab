from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.report_contract_validator import (
    ReportContractValidationError,
    supported_report_schema_versions,
    validate_report_payload,
)


FIXTURE_PATH = (
    Path(__file__).parent
    / "fixtures"
    / "report-v1.0.json"
)


def _canonical_report() -> dict:
    return json.loads(
        FIXTURE_PATH.read_text(encoding="utf-8")
    )


def test_public_report_v1_is_the_only_supported_contract() -> None:
    assert supported_report_schema_versions() == ("1.0",)


def test_public_report_v1_rejects_unknown_root_field() -> None:
    report = _canonical_report()
    report["future_public_field"] = "not-v1"

    with pytest.raises(
        ReportContractValidationError,
        match="additionalProperties",
    ):
        validate_report_payload(report)


def test_public_report_v1_rejects_unknown_result_field() -> None:
    report = _canonical_report()
    report["results"][0]["internal_governance_score"] = 0.97

    with pytest.raises(
        ReportContractValidationError,
        match="additionalProperties",
    ):
        validate_report_payload(report)


def test_public_report_v1_rejects_removed_required_field() -> None:
    report = _canonical_report()
    del report["summary"]

    with pytest.raises(
        ReportContractValidationError,
        match="required",
    ):
        validate_report_payload(report)


def test_public_report_v1_rejects_renamed_required_field() -> None:
    report = _canonical_report()
    report["generatedAt"] = report.pop("generated_at")

    with pytest.raises(
        ReportContractValidationError,
    ):
        validate_report_payload(report)


def test_public_report_v1_rejects_changed_field_type() -> None:
    report = _canonical_report()
    report["models"] = "llama3.1"

    with pytest.raises(
        ReportContractValidationError,
        match="type",
    ):
        validate_report_payload(report)


def test_public_report_rejects_unpublished_future_version() -> None:
    report = _canonical_report()
    report["schema_version"] = "1.1"

    with pytest.raises(
        ReportContractValidationError,
        match="Unsupported public report schema version",
    ):
        validate_report_payload(report)