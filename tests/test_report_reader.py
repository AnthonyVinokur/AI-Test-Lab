from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.report_contract_validator import ReportContractValidationError
from src.report_reader import (
    ReportReadError,
    load_report,
)
from src.report_schema import ReportV1


_FIXTURE_PATH = (
    Path(__file__).parent
    / "fixtures"
    / "report-v1.0.json"
)


def test_load_report_v1_fixture() -> None:
    report = load_report(_FIXTURE_PATH)

    assert isinstance(report, ReportV1)
    assert report.schema_version == "1.0"
    assert report.summary.total == 1
    assert report.summary.passed == 1
    assert report.results[0].test_id == "greeting-001"


def test_load_report_rejects_invalid_json(
    tmp_path: Path,
) -> None:
    report_path = tmp_path / "invalid.json"
    report_path.write_text(
        "{not valid json",
        encoding="utf-8",
    )

    with pytest.raises(
        ReportReadError,
        match="Invalid report JSON",
    ):
        load_report(report_path)


def test_load_report_rejects_non_object_json(
    tmp_path: Path,
) -> None:
    report_path = tmp_path / "report.json"
    report_path.write_text(
        "[]",
        encoding="utf-8",
    )

    with pytest.raises(
        ReportReadError,
        match="Report JSON root must be an object",
    ):
        load_report(report_path)


def test_load_report_rejects_missing_schema_version(
    tmp_path: Path,
) -> None:
    payload = json.loads(
        _FIXTURE_PATH.read_text(encoding="utf-8")
    )
    payload.pop("schema_version")

    report_path = tmp_path / "report.json"
    report_path.write_text(
        json.dumps(payload),
        encoding="utf-8",
    )

    with pytest.raises(
        ReportContractValidationError,
        match="schema_version",
    ):
        load_report(report_path)


def test_load_report_rejects_unsupported_schema_version(
    tmp_path: Path,
) -> None:
    payload = json.loads(
        _FIXTURE_PATH.read_text(encoding="utf-8")
    )
    payload["schema_version"] = "9.0"

    report_path = tmp_path / "report.json"
    report_path.write_text(
        json.dumps(payload),
        encoding="utf-8",
    )

    with pytest.raises(
        ReportContractValidationError,
        match="Unsupported public report schema version",
    ):
        load_report(report_path)


def test_load_report_rejects_contract_violation(
    tmp_path: Path,
) -> None:
    payload = json.loads(
        _FIXTURE_PATH.read_text(encoding="utf-8")
    )
    payload["summary"]["total"] = -1

    report_path = tmp_path / "report.json"
    report_path.write_text(
        json.dumps(payload),
        encoding="utf-8",
    )

    with pytest.raises(
        ReportContractValidationError,
        match="contract validation failed",
    ):
        load_report(report_path)