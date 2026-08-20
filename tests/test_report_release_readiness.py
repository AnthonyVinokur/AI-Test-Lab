import json
from pathlib import Path

import pytest

from src.report_contract_validator import ReportContractValidationError
from src.report_reader import ReportReadError
from src.report_release_validator import validate_report_for_release

from src.report_release_validator import (
    ReportReleaseValidationError,
    validate_report_for_release,
)

FIXTURE = Path("tests/fixtures/report-v1.0.json")


def test_valid_public_report_is_release_ready():
    validate_report_for_release(FIXTURE)


def test_unsupported_schema_version_is_not_release_ready(tmp_path):
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    payload["schema_version"] = "9.0"

    report_path = tmp_path / "unsupported-report.json"
    report_path.write_text(
        json.dumps(payload),
        encoding="utf-8",
    )

    with pytest.raises(ReportReleaseValidationError):
        validate_report_for_release(report_path)


def test_internal_field_is_not_release_ready(tmp_path):
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    payload["secret_internal_score"] = 99

    report_path = tmp_path / "internal-field-report.json"
    report_path.write_text(
        json.dumps(payload),
        encoding="utf-8",
    )

    with pytest.raises(ReportReleaseValidationError):
        validate_report_for_release(report_path)


def test_nested_internal_field_is_not_release_ready(tmp_path):
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    payload["results"][0]["internal_evidence_trace"] = {
        "rule_id": "private-rule-17",
        "score_path": "internal-only",
    }

    report_path = tmp_path / "nested-internal-field-report.json"
    report_path.write_text(
        json.dumps(payload),
        encoding="utf-8",
    )

    with pytest.raises(ReportReleaseValidationError):
        validate_report_for_release(report_path)


def test_private_runtime_option_is_not_release_ready(tmp_path):
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))

    payload["results"][0]["evaluation_results"][0]["runtime_options"][
        "internal_scoring_strategy"
    ] = "proprietary-v7"

    report_path = tmp_path / "private-runtime-option-report.json"
    report_path.write_text(
        json.dumps(payload),
        encoding="utf-8",
    )

    with pytest.raises(ReportReleaseValidationError):
        validate_report_for_release(report_path)


def test_invalid_json_is_not_release_ready(tmp_path):
    report_path = tmp_path / "corrupt-report.json"
    report_path.write_text(
        "{not valid json",
        encoding="utf-8",
    )

    with pytest.raises(ReportReleaseValidationError):
        validate_report_for_release(report_path)

def test_release_error_preserves_original_cause(tmp_path):
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    payload["schema_version"] = "9.0"

    report_path = tmp_path / "unsupported-report.json"
    report_path.write_text(
        json.dumps(payload),
        encoding="utf-8",
    )

    with pytest.raises(ReportReleaseValidationError) as exc_info:
        validate_report_for_release(report_path)

    assert exc_info.value.__cause__ is not None
