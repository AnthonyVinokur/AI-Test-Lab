from dataclasses import dataclass
from enum import Enum


class MetricDirection(str, Enum):
    HIGHER_IS_BETTER = "higher_is_better"
    LOWER_IS_BETTER = "lower_is_better"


@dataclass(frozen=True)
class EvaluationMetricDirection:
    metric_name: str
    direction: MetricDirection

    def __post_init__(self) -> None:
        if not isinstance(self.metric_name, str):
            raise TypeError("metric_name must be a string")

        if not self.metric_name.strip():
            raise ValueError("metric_name must not be empty")

        if not isinstance(self.direction, MetricDirection):
            raise TypeError("direction must be a MetricDirection")


_DEFAULT_METRIC_DIRECTIONS: tuple[EvaluationMetricDirection, ...] = (
    EvaluationMetricDirection(
        metric_name="answer_relevancy",
        direction=MetricDirection.HIGHER_IS_BETTER,
    ),
    EvaluationMetricDirection(
        metric_name="faithfulness",
        direction=MetricDirection.HIGHER_IS_BETTER,
    ),
)


def metric_direction_catalog(
    metric_directions: tuple[EvaluationMetricDirection, ...] = _DEFAULT_METRIC_DIRECTIONS,
) -> tuple[EvaluationMetricDirection, ...]:
    if not isinstance(metric_directions, tuple):
        raise TypeError("metric_directions must be a tuple")

    seen_metric_names: set[str] = set()

    for metric_direction in metric_directions:
        if not isinstance(metric_direction, EvaluationMetricDirection):
            raise TypeError(
                "metric_directions must contain EvaluationMetricDirection objects"
            )

        if metric_direction.metric_name in seen_metric_names:
            raise ValueError(
                f"duplicate metric direction definition: "
                f"{metric_direction.metric_name}"
            )

        seen_metric_names.add(metric_direction.metric_name)

    return tuple(
        sorted(
            metric_directions,
            key=lambda item: item.metric_name,
        )
    )


def direction_for_metric(
    metric_name: str,
    metric_directions: tuple[EvaluationMetricDirection, ...] = _DEFAULT_METRIC_DIRECTIONS,
) -> MetricDirection:
    if not isinstance(metric_name, str):
        raise TypeError("metric_name must be a string")

    if not metric_name.strip():
        raise ValueError("metric_name must not be empty")

    catalog = metric_direction_catalog(metric_directions)

    for metric_direction in catalog:
        if metric_direction.metric_name == metric_name:
            return metric_direction.direction

    raise ValueError(f"unknown metric direction: {metric_name}")

