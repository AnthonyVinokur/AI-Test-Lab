import json

from src.json_reporter import JsonReporter
from src.models import (
    AssertionType,
    EvaluationStatus,
    TestResult as ResultModel,
)
from src.evaluation_models import (
    EngineExecutionResult,
    MetricResult,
)

import pytest

from src.report_contract_validator import (
    ReportContractValidationError,
)


def test_json_reporter_does_not_write_when_contract_validation_fails(
    tmp_path,
    monkeypatch,
) -> None:
    report_path = tmp_path / "results.json"
    reporter = JsonReporter(report_path)

    def reject_report(_payload) -> None:
        raise ReportContractValidationError(
            "Public report contract rejected."
        )

    monkeypatch.setattr(
        "src.json_reporter.validate_report_payload",
        reject_report,
    )

    with pytest.raises(
        ReportContractValidationError,
        match="contract rejected",
    ):
        reporter.write([])

    assert not report_path.exists()

def test_json_reporter_creates_report(tmp_path) -> None:
    results = [
        ResultModel(
            test_id="greeting-001",
            name="Basic greeting test",
            category="functional",
            prompt="Say hello.",
            provider="ollama",
            model="llama3.1",
            estimated_cost_usd=0.0,
            actual_response="Hello!",
            passed=True,
            status=EvaluationStatus.PASS,
            assertion_type=AssertionType.CONTAINS,
            expected="Hello",
            reason="The response contains the expected text.",
            evaluation_results=[
                MetricResult(
                    engine="builtin",
                    metric_name="contains",
                    score=1.0,
                    threshold=1.0,
                    passed=True,
                    reason="The response contains the expected text.",
                    runtime_options={
                        "include_reason": True,
                    },
                    profile_name="fast-ci",
                    profile_version="1.0",
                    evaluator_model="test-judge",
                )
            ],
            engine_results=[
                EngineExecutionResult(
                    engine="deepeval",
                    succeeded=False,
                    error="judge unavailable",
                )
            ],
            response_time_seconds=0.25,
        )
    ]

    report_path = tmp_path / "results.json"
    reporter = JsonReporter(report_path)

    reporter.write(results)

    assert report_path.exists()

    report_data = json.loads(
        report_path.read_text(encoding="utf-8")
    )

    assert "generated_at" in report_data
    assert report_data["schema_version"] == "1.0"
    assert report_data["models"] == ["llama3.1"]
    assert report_data["summary"] == {
        "passed": 1,
        "failed": 0,
        "expected_failures": 0,
        "unexpected_passes": 0,
        "errors": 0,
        "total": 1,
        "pass_rate_percent": 100.0,
        "total_estimated_cost_usd": 0.0,
    }
    assert report_data["highlights"] == {
        "highest_scoring_model": "llama3.1",
        "fastest_model": "llama3.1",
    }
    assert len(report_data["model_comparison"]) == 1
    model_summary = report_data["model_comparison"][0]
    assert model_summary["model"] == "llama3.1"
    assert model_summary["passed"] == 1
    assert model_summary["expected_failures"] == 0
    assert model_summary["unexpected_failures"] == 0
    assert model_summary["errors"] == 0
    assert model_summary["total"] == 1
    assert model_summary["pass_rate_percent"] == 100.0
    assert model_summary["average_response_time_seconds"] == 0.25
    assert len(report_data["results"]) == 1
    assert report_data["results"][0]["test_id"] == "greeting-001"
    result = report_data["results"][0]
    evaluation = result["evaluation_results"][0]
    assert evaluation["engine"] == "builtin"
    assert evaluation["metric_name"] == "contains"
    assert evaluation["score"] == 1.0
    assert evaluation["threshold"] == 1.0
    assert evaluation["passed"] is True
    assert evaluation["reason"] == "The response contains the expected text."
    assert evaluation["runtime_options"] == {
        "include_reason": True,
    }
    assert evaluation["profile_name"] == "fast-ci"
    assert evaluation["profile_version"] == "1.0"
    assert evaluation["evaluator_model"] == "test-judge"
    assert report_data["summary"]["total_estimated_cost_usd"] == 0.0
    assert model_summary["provider"] == "ollama"
    assert model_summary["total_estimated_cost_usd"] == 0.0
    assert model_summary["average_estimated_cost_usd"] == 0.0
    assert result["provider"] == "ollama"
    assert result["estimated_cost_usd"] == 0.0
    engine_result = result["engine_results"][0]
    assert engine_result == {
        "engine": "deepeval",
        "succeeded": False,
        "error": "Evaluation engine failed.",
    }

def test_json_reporter_filters_private_runtime_options(
    tmp_path,
) -> None:
    result = ResultModel(
        test_id="boundary-001",
        name="Public boundary test",
        category="security",
        prompt="Test public serialization.",
        provider="ollama",
        model="llama3.1",
        estimated_cost_usd=0.0,
        actual_response="Safe response.",
        passed=True,
        status=EvaluationStatus.PASS,
        assertion_type=AssertionType.CONTAINS,
        expected="Safe",
        reason="Passed.",
        evaluation_results=[
            MetricResult(
                engine="builtin",
                metric_name="contains",
                score=1.0,
                threshold=1.0,
                passed=True,
                runtime_options={
                    "include_reason": True,
                    "governance_weight": 0.91,
                    "internal_scoring_strategy": "proprietary-v4",
                    "private_evidence_id": "EV-99182",
                },
            )
        ],
        response_time_seconds=0.1,
    )

    report_path = tmp_path / "results.json"

    JsonReporter(report_path).write([result])

    report_data = json.loads(
        report_path.read_text(encoding="utf-8")
    )

    runtime_options = (
        report_data["results"][0]
        ["evaluation_results"][0]
        ["runtime_options"]
    )

    assert runtime_options == {
        "include_reason": True,
    }

    serialized_report = json.dumps(report_data)

    assert "governance_weight" not in serialized_report
    assert "internal_scoring_strategy" not in serialized_report
    assert "private_evidence_id" not in serialized_report


def test_json_reporter_redacts_internal_engine_error(
    tmp_path,
) -> None:
    result = ResultModel(
        test_id="boundary-002",
        name="Engine error boundary test",
        category="security",
        prompt="Test engine error redaction.",
        provider="ollama",
        model="llama3.1",
        estimated_cost_usd=0.0,
        actual_response="Response.",
        passed=False,
        status=EvaluationStatus.ERROR,
        assertion_type=AssertionType.CONTAINS,
        expected="Safe",
        reason="Engine failed.",
        engine_results=[
            EngineExecutionResult(
                engine="private-engine",
                succeeded=False,
                error=(
                    "Internal evaluator failed at "
                    "C:\\private\\governance\\scorer.py"
                ),
            )
        ],
        response_time_seconds=0.1,
    )

    report_path = tmp_path / "results.json"

    JsonReporter(report_path).write([result])

    report_data = json.loads(
        report_path.read_text(encoding="utf-8")
    )

    engine_result = (
        report_data["results"][0]
        ["engine_results"][0]
    )

    assert engine_result["error"] == (
        "Evaluation engine failed."
    )

    serialized_report = json.dumps(report_data)

    assert "scorer.py" not in serialized_report
    assert "private\\governance" not in serialized_report
