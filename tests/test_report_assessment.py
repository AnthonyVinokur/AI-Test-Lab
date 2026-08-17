import json
from dataclasses import replace

import pytest

from src.report_assessment import FindingLevel, assess_report
from src.report_decision import DecisionStatus
from src.report_summary import (
    EngineFailureSummary,
    MetricFailureSummary,
    ReportSummary,
)


def make_summary(**overrides) -> ReportSummary:
    summary = ReportSummary(
        schema_version="1.0",
        generated_at="2026-08-17T13:00:00-04:00",
        overall_status="passed",
        total=2,
        passed=2,
        failed=0,
        expected_failures=0,
        unexpected_passes=0,
        errors=0,
        pass_rate_percent=100.0,
        profiles=("fast-ci",),
        failed_test_ids=(),
        failed_metrics=(),
        engine_failures=(),
    )
    return replace(summary, **overrides)


def test_assess_report_builds_passing_public_assessment():
    result = assess_report(make_summary())

    assert result.status == DecisionStatus.PASS
    assert result.summary == "Assessment passed: 2 of 2 evaluated test(s) passed."
    assert result.findings[0].code == "report_passed"
    assert result.findings[0].level == FindingLevel.INFO


def test_assess_report_explains_failed_tests():
    result = assess_report(
        make_summary(
            overall_status="failed",
            passed=1,
            failed=1,
            pass_rate_percent=50.0,
            failed_test_ids=("python-001",),
        )
    )

    assert result.status == DecisionStatus.FAIL
    assert [finding.code for finding in result.findings] == [
        "report_failed",
        "failed_test",
    ]
    assert result.findings[1].test_id == "python-001"


def test_assess_report_explains_failed_public_metrics():
    result = assess_report(
        make_summary(
            overall_status="failed",
            passed=1,
            failed=1,
            pass_rate_percent=50.0,
            failed_metrics=(
                MetricFailureSummary(
                    test_id="rag-004",
                    engine="deepeval",
                    metric_name="faithfulness",
                    score=0.61,
                    threshold=0.8,
                ),
            ),
        )
    )

    metric_finding = result.findings[1]
    assert metric_finding.code == "failed_metric"
    assert metric_finding.metric_name == "faithfulness"
    assert metric_finding.score == 0.61
    assert metric_finding.threshold == 0.8


def test_engine_failure_is_warning_and_does_not_override_pass_decision():
    result = assess_report(
        make_summary(
            engine_failures=(
                EngineFailureSummary(
                    test_id="greeting-001",
                    engine="deepeval",
                    error="Evaluation engine failed.",
                ),
            ),
        )
    )

    assert result.status == DecisionStatus.PASS
    assert result.findings[1].code == "engine_failure"
    assert result.findings[1].level == FindingLevel.WARNING


def test_assess_report_explains_error_status():
    result = assess_report(
        make_summary(
            overall_status="error",
            errors=1,
        )
    )

    assert result.status == DecisionStatus.ERROR
    assert result.findings[0].code == "report_error"
    assert result.findings[0].level == FindingLevel.ERROR


def test_assess_report_explains_no_data_status():
    result = assess_report(
        make_summary(
            overall_status="empty",
            total=0,
            passed=0,
            pass_rate_percent=0.0,
        )
    )

    assert result.status == DecisionStatus.NO_DATA
    assert result.findings[0].code == "no_data"
    assert result.findings[0].level == FindingLevel.WARNING


def test_findings_have_deterministic_order():
    result = assess_report(
        make_summary(
            overall_status="failed",
            passed=0,
            failed=2,
            pass_rate_percent=0.0,
            failed_test_ids=("z-test", "a-test"),
            engine_failures=(
                EngineFailureSummary(
                    test_id="z-test",
                    engine="judge",
                    error=None,
                ),
                EngineFailureSummary(
                    test_id="a-test",
                    engine="deepeval",
                    error=None,
                ),
            ),
        )
    )

    assert [
        (finding.code, finding.test_id, finding.engine)
        for finding in result.findings
    ] == [
        ("report_failed", None, None),
        ("failed_test", "a-test", None),
        ("failed_test", "z-test", None),
        ("engine_failure", "a-test", "deepeval"),
        ("engine_failure", "z-test", "judge"),
    ]


def test_assessment_to_dict_is_json_serializable_and_public_only():
    result = assess_report(make_summary())

    payload = result.to_dict()
    encoded = json.dumps(payload)

    assert '"status": "pass"' in encoded
    assert set(payload) == {
        "status",
        "schema_version",
        "generated_at",
        "total",
        "passed",
        "failed",
        "errors",
        "summary",
        "findings",
    }


def test_assess_report_rejects_unknown_summary_status():
    with pytest.raises(ValueError, match="unsupported report summary status"):
        assess_report(make_summary(overall_status="unexpected"))
