import json

from src.json_reporter import JsonReporter
from src.models import (
    AssertionType,
    EvaluationStatus,
    TestResult as ResultModel,
)
from src.evaluation_models import MetricResult


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
    assert (
            evaluation["reason"]
            == "The response contains the expected text."
    )
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
