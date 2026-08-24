from dataclasses import FrozenInstanceError

import pytest

from src.evaluation_metric_regression_gate import MetricRegressionGateDecision
from src.evaluation_run_regression_gate import (
    EvaluationRunRegressionGateDecision,
    evaluate_run_regression_gate,
)


def test_all_pass_decisions_produce_pass():
    result = evaluate_run_regression_gate(
        (
            MetricRegressionGateDecision.PASS,
            MetricRegressionGateDecision.PASS,
        )
    )

    assert result.decision == EvaluationRunRegressionGateDecision.PASS
    assert result.total_metrics == 2
    assert result.passed_metrics == 2
    assert result.failed_metrics == 0
    assert result.not_applicable_metrics == 0


def test_any_fail_decision_produces_fail():
    result = evaluate_run_regression_gate(
        (
            MetricRegressionGateDecision.PASS,
            MetricRegressionGateDecision.FAIL,
            MetricRegressionGateDecision.PASS,
        )
    )

    assert result.decision == EvaluationRunRegressionGateDecision.FAIL
    assert result.total_metrics == 3
    assert result.passed_metrics == 2
    assert result.failed_metrics == 1
    assert result.not_applicable_metrics == 0


def test_pass_and_not_applicable_produce_pass():
    result = evaluate_run_regression_gate(
        (
            MetricRegressionGateDecision.NOT_APPLICABLE,
            MetricRegressionGateDecision.PASS,
        )
    )

    assert result.decision == EvaluationRunRegressionGateDecision.PASS
    assert result.total_metrics == 2
    assert result.passed_metrics == 1
    assert result.failed_metrics == 0
    assert result.not_applicable_metrics == 1


def test_all_not_applicable_produce_not_applicable():
    result = evaluate_run_regression_gate(
        (
            MetricRegressionGateDecision.NOT_APPLICABLE,
            MetricRegressionGateDecision.NOT_APPLICABLE,
        )
    )

    assert (
        result.decision
        == EvaluationRunRegressionGateDecision.NOT_APPLICABLE
    )
    assert result.total_metrics == 2
    assert result.passed_metrics == 0
    assert result.failed_metrics == 0
    assert result.not_applicable_metrics == 2


def test_empty_decisions_produce_not_applicable():
    result = evaluate_run_regression_gate(())

    assert (
        result.decision
        == EvaluationRunRegressionGateDecision.NOT_APPLICABLE
    )
    assert result.total_metrics == 0
    assert result.passed_metrics == 0
    assert result.failed_metrics == 0
    assert result.not_applicable_metrics == 0


def test_result_is_immutable():
    result = evaluate_run_regression_gate(
        (MetricRegressionGateDecision.PASS,)
    )

    with pytest.raises(FrozenInstanceError):
        result.decision = EvaluationRunRegressionGateDecision.FAIL
