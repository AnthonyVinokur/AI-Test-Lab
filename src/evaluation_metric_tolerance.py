from dataclasses import dataclass
from enum import Enum
from math import isclose

from src.evaluation_metric_movement import (
    EvaluationMetricMovement,
    MetricMovement,
)


class MetricToleranceStatus(str, Enum):
    NOT_APPLICABLE = "not_applicable"
    WITHIN_TOLERANCE = "within_tolerance"
    EXCEEDS_TOLERANCE = "exceeds_tolerance"


@dataclass(frozen=True)
class EvaluationMetricTolerance:
    magnitude: float
    tolerance: float
    status: MetricToleranceStatus


def evaluate_metric_tolerance(
    movement: EvaluationMetricMovement,
    tolerance: float,
) -> EvaluationMetricTolerance:
    if not isinstance(movement, EvaluationMetricMovement):
        raise TypeError("movement must be an EvaluationMetricMovement")

    if isinstance(tolerance, bool) or not isinstance(tolerance, (int, float)):
        raise TypeError("tolerance must be a numeric value")

    tolerance = float(tolerance)

    if not 0.0 <= tolerance <= 1.0:
        raise ValueError("tolerance must be between 0.0 and 1.0")

    if movement.movement is not MetricMovement.REGRESSION:
        return EvaluationMetricTolerance(
            magnitude=movement.magnitude,
            tolerance=tolerance,
            status=MetricToleranceStatus.NOT_APPLICABLE,
        )

    within_tolerance = (
        movement.magnitude < tolerance
        or isclose(
            movement.magnitude,
            tolerance,
            rel_tol=0.0,
            abs_tol=1e-12,
        )
    )

    status = (
        MetricToleranceStatus.WITHIN_TOLERANCE
        if within_tolerance
        else MetricToleranceStatus.EXCEEDS_TOLERANCE
    )

    return EvaluationMetricTolerance(
        magnitude=movement.magnitude,
        tolerance=tolerance,
        status=status,
    )