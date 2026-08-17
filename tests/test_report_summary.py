import json
from copy import deepcopy
from pathlib import Path

import pytest

from src.report_summary import summarize_report


FIXTURE = Path("tests/fixtures/report-v1.0.json")


def load_report() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_summarize_report_exposes_small_public_consumer_view():
    report = load_report()

    result = summarize_report(report)

    assert result.schema_version == "1.0"
    assert result.generated_at == "2026-08-14T20:00:00-04:00"
    assert result.overall_status == "passed"
    assert result.total == 1
    assert result.passed == 1
    assert result.failed == 0
    assert result.pass_rate_percent == 100.0
    assert result.profiles == ("fast-ci",)
    assert result.failed_test_ids == ()
    assert result.failed_metrics == ()

    # Engine execution failure is observable without changing the test verdict.
    assert len(result.engine_failures) == 1
    assert result.engine_failures[0].test_id == "greeting-001"
    assert result.engine_failures[0].engine == "deepeval"
    assert result.engine_failures[0].error == "Evaluation engine failed."


def test_summarize_report_collects_failed_tests_and_failed_metrics():
    report = deepcopy(load_report())
    report["summary"]["passed"] = 0
    report["summary"]["failed"] = 1
    report["summary"]["pass_rate_percent"] = 0.0

    test_result = report["results"][0]
    test_result["passed"] = False
    test_result["status"] = "fail"
    test_result["evaluation_results"][0]["passed"] = False
    test_result["evaluation_results"][0]["score"] = 0.25

    result = summarize_report(report)

    assert result.overall_status == "failed"
    assert result.failed_test_ids == ("greeting-001",)
    assert len(result.failed_metrics) == 1

    metric = result.failed_metrics[0]
    assert metric.test_id == "greeting-001"
    assert metric.engine == "builtin"
    assert metric.metric_name == "contains"
    assert metric.score == 0.25
    assert metric.threshold == 1.0


def test_summarize_report_prefers_error_status_when_report_contains_errors():
    report = deepcopy(load_report())
    report["summary"]["errors"] = 1

    result = summarize_report(report)

    assert result.overall_status == "error"


def test_summarize_report_marks_zero_test_report_empty():
    report = deepcopy(load_report())
    report["summary"].update(
        {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "errors": 0,
            "pass_rate_percent": 0.0,
        }
    )
    report["results"] = []

    result = summarize_report(report)

    assert result.overall_status == "empty"


def test_summarize_report_rejects_non_object_summary():
    report = load_report()
    report["summary"] = []

    with pytest.raises(TypeError, match="summary must be an object"):
        summarize_report(report)


def test_to_dict_is_json_serializable():
    result = summarize_report(load_report())

    encoded = json.dumps(result.to_dict())

    assert '"schema_version": "1.0"' in encoded
    assert '"profile' in encoded
