from dataclasses import dataclass
from enum import Enum

from src.evaluation_metric_tolerance import (
    EvaluationMetricTolerance,
    MetricToleranceStatus,
)


class MetricRegressionSeverity(str, Enum):
    NOT_APPLICABLE = "not_applicable"
    ACCEPTABLE = "acceptable"
    MINOR = "minor"
    MAJOR = "major"
    CRITICAL = "critical"


@dataclass(frozen=True)
class EvaluationMetricRegressionSeverity:
    magnitude: float
    tolerance: float
    ratio: float | None
    severity: MetricRegressionSeverity


def classify_metric_regression_severity(
    tolerance_result: EvaluationMetricTolerance,
) -> EvaluationMetricRegressionSeverity:
    if not isinstance(tolerance_result, EvaluationMetricTolerance):
        raise TypeError(
            "tolerance_result must be an EvaluationMetricTolerance"
        )

    if tolerance_result.status is MetricToleranceStatus.NOT_APPLICABLE:
        return EvaluationMetricRegressionSeverity(
            magnitude=tolerance_result.magnitude,
            tolerance=tolerance_result.tolerance,
            ratio=None,
            severity=MetricRegressionSeverity.NOT_APPLICABLE,
        )

    if tolerance_result.status is MetricToleranceStatus.WITHIN_TOLERANCE:
        ratio = (
            0.0
            if tolerance_result.tolerance == 0.0
            else tolerance_result.magnitude / tolerance_result.tolerance
        )

        return EvaluationMetricRegressionSeverity(
            magnitude=tolerance_result.magnitude,
            tolerance=tolerance_result.tolerance,
            ratio=ratio,
            severity=MetricRegressionSeverity.ACCEPTABLE,
        )

    if tolerance_result.tolerance == 0.0:
        return EvaluationMetricRegressionSeverity(
            magnitude=tolerance_result.magnitude,
            tolerance=tolerance_result.tolerance,
            ratio=None,
            severity=MetricRegressionSeverity.CRITICAL,
        )

    ratio = tolerance_result.magnitude / tolerance_result.tolerance

    if ratio <= 2.0:
        severity = MetricRegressionSeverity.MINOR
    elif ratio <= 5.0:
        severity = MetricRegressionSeverity.MAJOR
    else:
        severity = MetricRegressionSeverity.CRITICAL

    return EvaluationMetricRegressionSeverity(
        magnitude=tolerance_result.magnitude,
        tolerance=tolerance_result.tolerance,
        ratio=ratio,
        severity=severity,
    )
