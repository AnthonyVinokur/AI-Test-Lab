from dataclasses import dataclass
from enum import Enum

from src.evaluation_metric_direction import MetricDirection


class MetricMovement(str, Enum):
    IMPROVEMENT = "improvement"
    REGRESSION = "regression"
    UNCHANGED = "unchanged"


@dataclass(frozen=True)
class EvaluationMetricMovement:
    baseline_score: float
    candidate_score: float
    delta: float
    magnitude: float
    direction: MetricDirection
    movement: MetricMovement


def classify_metric_movement(
    baseline_score: float,
    candidate_score: float,
    direction: MetricDirection,
) -> EvaluationMetricMovement:
    _validate_score("baseline_score", baseline_score)
    _validate_score("candidate_score", candidate_score)

    if not isinstance(direction, MetricDirection):
        raise TypeError("direction must be a MetricDirection")

    delta = candidate_score - baseline_score
    magnitude = abs(delta)

    if delta == 0:
        movement = MetricMovement.UNCHANGED
    elif direction == MetricDirection.HIGHER_IS_BETTER:
        movement = (
            MetricMovement.IMPROVEMENT
            if delta > 0
            else MetricMovement.REGRESSION
        )
    else:
        movement = (
            MetricMovement.IMPROVEMENT
            if delta < 0
            else MetricMovement.REGRESSION
        )

    return EvaluationMetricMovement(
        baseline_score=baseline_score,
        candidate_score=candidate_score,
        delta=delta,
        magnitude=magnitude,
        direction=direction,
        movement=movement,
    )


def _validate_score(name: str, score: float) -> None:
    if isinstance(score, bool) or not isinstance(score, (int, float)):
        raise TypeError(f"{name} must be numeric")

    if not 0.0 <= score <= 1.0:
        raise ValueError(f"{name} must be between 0.0 and 1.0")
