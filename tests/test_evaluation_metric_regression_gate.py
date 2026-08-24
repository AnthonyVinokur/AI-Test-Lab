from dataclasses import FrozenInstanceError

import pytest

from src.evaluation_metric_regression_gate import (
    EvaluationMetricRegressionGate,
    MetricRegressionGateDecision,
    evaluate_metric_regression_gate,
)
from src.evaluation_metric_regression_severity import (
    EvaluationMetricRegressionSeverity,
    MetricRegressionSeverity,
)


def make_severity(
    severity: MetricRegressionSeverity,
) -> EvaluationMetricRegressionSeverity:
    return EvaluationMetricRegressionSeverity(
        magnitude=0.01,
        tolerance=0.01,
        ratio=1.0,
        severity=severity,
    )


def test_not_applicable_returns_not_applicable():
    result = evaluate_metric_regression_gate(
        make_severity(MetricRegressionSeverity.NOT_APPLICABLE),
        max_allowed_severity=MetricRegressionSeverity.MINOR,
    )

    assert result.decision is MetricRegressionGateDecision.NOT_APPLICABLE


def test_acceptable_passes_when_acceptable_is_allowed():
    result = evaluate_metric_regression_gate(
        make_severity(MetricRegressionSeverity.ACCEPTABLE),
        max_allowed_severity=MetricRegressionSeverity.ACCEPTABLE,
    )

    assert result.decision is MetricRegressionGateDecision.PASS


def test_minor_passes_when_minor_is_allowed():
    result = evaluate_metric_regression_gate(
        make_severity(MetricRegressionSeverity.MINOR),
        max_allowed_severity=MetricRegressionSeverity.MINOR,
    )

    assert result.decision is MetricRegressionGateDecision.PASS


def test_major_fails_when_only_minor_is_allowed():
    result = evaluate_metric_regression_gate(
        make_severity(MetricRegressionSeverity.MAJOR),
        max_allowed_severity=MetricRegressionSeverity.MINOR,
    )

    assert result.decision is MetricRegressionGateDecision.FAIL


def test_critical_fails_when_only_minor_is_allowed():
    result = evaluate_metric_regression_gate(
        make_severity(MetricRegressionSeverity.CRITICAL),
        max_allowed_severity=MetricRegressionSeverity.MINOR,
    )

    assert result.decision is MetricRegressionGateDecision.FAIL


def test_minor_fails_when_only_acceptable_is_allowed():
    result = evaluate_metric_regression_gate(
        make_severity(MetricRegressionSeverity.MINOR),
        max_allowed_severity=MetricRegressionSeverity.ACCEPTABLE,
    )

    assert result.decision is MetricRegressionGateDecision.FAIL


def test_major_passes_when_major_is_allowed():
    result = evaluate_metric_regression_gate(
        make_severity(MetricRegressionSeverity.MAJOR),
        max_allowed_severity=MetricRegressionSeverity.MAJOR,
    )

    assert result.decision is MetricRegressionGateDecision.PASS


def test_critical_fails_when_major_is_allowed():
    result = evaluate_metric_regression_gate(
        make_severity(MetricRegressionSeverity.CRITICAL),
        max_allowed_severity=MetricRegressionSeverity.MAJOR,
    )

    assert result.decision is MetricRegressionGateDecision.FAIL


def test_not_applicable_cannot_be_used_as_max_allowed_severity():
    with pytest.raises(
        ValueError,
        match="max_allowed_severity cannot be NOT_APPLICABLE",
    ):
        evaluate_metric_regression_gate(
            make_severity(MetricRegressionSeverity.MINOR),
            max_allowed_severity=MetricRegressionSeverity.NOT_APPLICABLE,
        )


def test_gate_result_is_immutable():
    result = EvaluationMetricRegressionGate(
        severity=MetricRegressionSeverity.MINOR,
        max_allowed_severity=MetricRegressionSeverity.MINOR,
        decision=MetricRegressionGateDecision.PASS,
    )

    with pytest.raises(FrozenInstanceError):
        result.decision = MetricRegressionGateDecision.FAIL