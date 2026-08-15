import copy
import json
from pathlib import Path

import pytest

from src.report_contract_validator import (
    ReportContractValidationError,
    validate_report_v1_payload,
)


def _load_fixture() -> dict:
    fixture_path = (
        Path(__file__).parent
        / "fixtures"
        / "report-v1.0.json"
    )

    return json.loads(
        fixture_path.read_text(encoding="utf-8")
    )


def test_report_v1_validator_accepts_canonical_fixture() -> None:
    report = _load_fixture()

    validate_report_v1_payload(report)


def test_report_v1_validator_rejects_missing_required_field() -> None:
    report = copy.deepcopy(_load_fixture())
    del report["results"][0]["test_id"]

    with pytest.raises(
        ReportContractValidationError,
        match="required",
    ):
        validate_report_v1_payload(report)


def test_report_v1_validator_rejects_wrong_schema_version() -> None:
    report = copy.deepcopy(_load_fixture())
    report["schema_version"] = "2.0"

    with pytest.raises(
        ReportContractValidationError,
        match="const",
    ):
        validate_report_v1_payload(report)


def test_report_v1_validator_rejects_unknown_public_field() -> None:
    report = copy.deepcopy(_load_fixture())
    report["internal_governance_score"] = 0.91

    with pytest.raises(
        ReportContractValidationError,
        match="additionalProperties",
    ):
        validate_report_v1_payload(report)


def test_report_v1_validator_rejects_wrong_field_type() -> None:
    report = copy.deepcopy(_load_fixture())
    report["summary"]["total"] = "1"

    with pytest.raises(
        ReportContractValidationError,
        match="type",
    ):
        validate_report_v1_payload(report)