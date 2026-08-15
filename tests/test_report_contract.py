from src.report_schema import ReportV1
import json
from pathlib import Path

import copy

import pytest
from pydantic import ValidationError

def test_report_v1_contract_top_level_fields_are_frozen() -> None:
    schema = ReportV1.model_json_schema()

    assert set(schema["properties"]) == {
        "schema_version",
        "generated_at",
        "models",
        "summary",
        "highlights",
        "model_comparison",
        "results",
    }

def test_report_v1_required_fields_are_frozen() -> None:
    schema = ReportV1.model_json_schema()

    assert set(schema["required"]) == {
        "generated_at",
        "models",
        "summary",
        "highlights",
        "model_comparison",
        "results",
    }


def test_report_v1_schema_version_is_frozen() -> None:
    schema = ReportV1.model_json_schema()

    schema_version = schema["properties"]["schema_version"]

    assert schema_version["const"] == "1.0"
    assert schema_version["default"] == "1.0"

def test_report_v1_result_fields_are_frozen() -> None:
    schema = ReportV1.model_json_schema()

    result_schema_ref = schema["properties"]["results"]["items"]["$ref"]
    result_schema_name = result_schema_ref.rsplit("/", 1)[-1]
    result_schema = schema["$defs"][result_schema_name]

    assert set(result_schema["properties"]) == {
        "test_id",
        "name",
        "category",
        "prompt",
        "provider",
        "model",
        "estimated_cost_usd",
        "actual_response",
        "passed",
        "status",
        "expected_to_fail",
        "assertion_type",
        "expected",
        "reason",
        "evaluation_results",
        "engine_results",
        "response_time_seconds",
        "prompt_tokens",
        "output_tokens",
        "prompt_latency_seconds",
        "generation_latency_seconds",
        "model_load_seconds",
        "prompt_tokens_per_second",
        "generation_tokens_per_second",
    }

def test_report_v1_metric_result_fields_are_frozen() -> None:
    schema = ReportV1.model_json_schema()

    metric_schema = schema["$defs"]["ReportMetricResultV1"]

    assert set(metric_schema["properties"]) == {
        "engine",
        "metric_name",
        "score",
        "threshold",
        "passed",
        "reason",
        "runtime_options",
        "profile_name",
        "profile_version",
        "evaluator_model",
    }


def test_report_v1_engine_result_fields_are_frozen() -> None:
    schema = ReportV1.model_json_schema()

    engine_schema = schema["$defs"]["ReportEngineExecutionResultV1"]

    assert set(engine_schema["properties"]) == {
        "engine",
        "succeeded",
        "error",
    }

def test_report_v1_fixture_validates_against_public_contract() -> None:
    fixture_path = (
        Path(__file__).parent
        / "fixtures"
        / "report-v1.0.json"
    )

    fixture_data = json.loads(
        fixture_path.read_text(encoding="utf-8")
    )

    report = ReportV1.model_validate(fixture_data)

    assert report.schema_version == "1.0"
    assert report.results[0].test_id == "greeting-001"

def test_report_v1_rejects_unknown_top_level_field() -> None:
    fixture_path = (
        Path(__file__).parent
        / "fixtures"
        / "report-v1.0.json"
    )

    fixture_data = json.loads(
        fixture_path.read_text(encoding="utf-8")
    )

    invalid_report = copy.deepcopy(fixture_data)
    invalid_report["internal_governance_score"] = 0.91

    with pytest.raises(ValidationError):
        ReportV1.model_validate(invalid_report)


def test_report_v1_rejects_wrong_schema_version() -> None:
    fixture_path = (
        Path(__file__).parent
        / "fixtures"
        / "report-v1.0.json"
    )

    fixture_data = json.loads(
        fixture_path.read_text(encoding="utf-8")
    )

    invalid_report = copy.deepcopy(fixture_data)
    invalid_report["schema_version"] = "2.0"

    with pytest.raises(ValidationError):
        ReportV1.model_validate(invalid_report)


def test_report_v1_rejects_missing_required_result_field() -> None:
    fixture_path = (
        Path(__file__).parent
        / "fixtures"
        / "report-v1.0.json"
    )

    fixture_data = json.loads(
        fixture_path.read_text(encoding="utf-8")
    )

    invalid_report = copy.deepcopy(fixture_data)
    del invalid_report["results"][0]["test_id"]

    with pytest.raises(ValidationError):
        ReportV1.model_validate(invalid_report)

def test_canonical_report_v1_json_schema_is_in_sync() -> None:
    schema_path = (
        Path(__file__).parent.parent
        / "schemas"
        / "report-v1.0.schema.json"
    )

    stored_schema = json.loads(
        schema_path.read_text(encoding="utf-8")
    )

    assert stored_schema == ReportV1.model_json_schema()