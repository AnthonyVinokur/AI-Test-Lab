import json
from dataclasses import replace

import pytest

from src.report_summary import EngineFailureSummary, ReportSummary
from src.report_summary import ReportSummary
from src.report_decision import DecisionStatus, decide_report


def make_summary(**overrides) -> ReportSummary:
    summary = ReportSummary(
        schema_version="1.0",
        generated_at="2026-08-17T11:00:00-04:00",
        overall_status="passed",
        total=1,
        passed=1,
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


def test_decide_report_maps_passed_summary_to_pass():
    result = decide_report(make_summary())

    assert result.status == DecisionStatus.PASS
    assert result.schema_version == "1.0"
    assert result.total == 1
    assert result.passed == 1
    assert result.failed == 0
    assert result.errors == 0


def test_decide_report_maps_failed_summary_to_fail():
    summary = make_summary(
        overall_status="failed",
        passed=0,
        failed=1,
        pass_rate_percent=0.0,
    )

    result = decide_report(summary)

    assert result.status == DecisionStatus.FAIL


def test_decide_report_maps_error_summary_to_error():
    summary = make_summary(
        overall_status="error",
        errors=1,
    )

    result = decide_report(summary)

    assert result.status == DecisionStatus.ERROR


def test_decide_report_maps_empty_summary_to_no_data():
    summary = make_summary(
        overall_status="empty",
        total=0,
        passed=0,
        pass_rate_percent=0.0,
    )

    result = decide_report(summary)

    assert result.status == DecisionStatus.NO_DATA


def test_decide_report_rejects_unknown_summary_status():
    summary = make_summary(overall_status="unexpected")

    with pytest.raises(
        ValueError,
        match="unsupported report summary status",
    ):
        decide_report(summary)


def test_decision_does_not_override_passed_summary_for_engine_failures():
    summary = make_summary(
        overall_status="passed",
        engine_failures=(
            EngineFailureSummary(
                test_id="greeting-001",
                engine="deepeval",
                error="Evaluation engine failed.",
            ),
        ),
    )

    result = decide_report(summary)

    assert result.status == DecisionStatus.PASS


def test_report_decision_to_dict_is_json_serializable():
    result = decide_report(make_summary())

    encoded = json.dumps(result.to_dict())

    assert '"status": "pass"' in encoded
    assert '"schema_version": "1.0"' in encoded