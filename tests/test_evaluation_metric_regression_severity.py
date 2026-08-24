import pytest

from src.evaluation_metric_regression_severity import (
    EvaluationMetricRegressionSeverity,
    MetricRegressionSeverity,
    classify_metric_regression_severity,
)
from src.evaluation_metric_tolerance import (
    EvaluationMetricTolerance,
    MetricToleranceStatus,
)


def make_tolerance_result(
        *,
        magnitude: float,
        tolerance: float,
        status: MetricToleranceStatus,
) -> EvaluationMetricTolerance:
    return EvaluationMetricTolerance(
        magnitude=magnitude,
        tolerance=tolerance,
        status=status,
    )


def test_non_applicable_tolerance_produces_non_applicable_severity():
    tolerance_result = make_tolerance_result(
        magnitude=0.0,
        tolerance=0.01,
        status=MetricToleranceStatus.NOT_APPLICABLE,
    )

    result = classify_metric_regression_severity(tolerance_result)

    assert result == EvaluationMetricRegressionSeverity(
        magnitude=0.0,
        tolerance=0.01,
        ratio=None,
        severity=MetricRegressionSeverity.NOT_APPLICABLE,
    )


def test_within_tolerance_regression_is_acceptable():
    tolerance_result = make_tolerance_result(
        magnitude=0.005,
        tolerance=0.01,
        status=MetricToleranceStatus.WITHIN_TOLERANCE,
    )

    result = classify_metric_regression_severity(tolerance_result)

    assert result.severity is MetricRegressionSeverity.ACCEPTABLE
    assert result.ratio == pytest.approx(0.5)


def test_exact_tolerance_boundary_is_acceptable():
    tolerance_result = make_tolerance_result(
        magnitude=0.01,
        tolerance=0.01,
        status=MetricToleranceStatus.WITHIN_TOLERANCE,
    )

    result = classify_metric_regression_severity(tolerance_result)

    assert result.severity is MetricRegressionSeverity.ACCEPTABLE
    assert result.ratio == pytest.approx(1.0)


def test_regression_up_to_two_times_tolerance_is_minor():
    tolerance_result = make_tolerance_result(
        magnitude=0.02,
        tolerance=0.01,
        status=MetricToleranceStatus.EXCEEDS_TOLERANCE,
    )

    result = classify_metric_regression_severity(tolerance_result)

    assert result.severity is MetricRegressionSeverity.MINOR
    assert result.ratio == pytest.approx(2.0)


def test_regression_above_two_times_tolerance_is_major():
    tolerance_result = make_tolerance_result(
        magnitude=0.03,
        tolerance=0.01,
        status=MetricToleranceStatus.EXCEEDS_TOLERANCE,
    )

    result = classify_metric_regression_severity(tolerance_result)

    assert result.severity is MetricRegressionSeverity.MAJOR
    assert result.ratio == pytest.approx(3.0)


def test_regression_at_five_times_tolerance_is_major():
    tolerance_result = make_tolerance_result(
        magnitude=0.05,
        tolerance=0.01,
        status=MetricToleranceStatus.EXCEEDS_TOLERANCE,
    )

    result = classify_metric_regression_severity(tolerance_result)

    assert result.severity is MetricRegressionSeverity.MAJOR
    assert result.ratio == pytest.approx(5.0)


def test_regression_above_five_times_tolerance_is_critical():
    tolerance_result = make_tolerance_result(
        magnitude=0.06,
        tolerance=0.01,
        status=MetricToleranceStatus.EXCEEDS_TOLERANCE,
    )

    result = classify_metric_regression_severity(tolerance_result)

    assert result.severity is MetricRegressionSeverity.CRITICAL
    assert result.ratio == pytest.approx(6.0)


def test_exceeded_zero_tolerance_is_critical():
    tolerance_result = make_tolerance_result(
        magnitude=0.001,
        tolerance=0.0,
        status=MetricToleranceStatus.EXCEEDS_TOLERANCE,
    )

    result = classify_metric_regression_severity(tolerance_result)

    assert result.severity is MetricRegressionSeverity.CRITICAL
    assert result.ratio is None


def test_invalid_tolerance_result_type_is_rejected():
    with pytest.raises(
            TypeError,
            match="tolerance_result must be an EvaluationMetricTolerance",
    ):
        classify_metric_regression_severity("invalid")
