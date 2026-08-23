import pytest

from src.evaluation_metric_direction import (
    EvaluationMetricDirection,
    MetricDirection,
    direction_for_metric,
    metric_direction_catalog,
)


def test_higher_is_better_direction_is_supported() -> None:
    assert (
            EvaluationMetricDirection(
                metric_name="quality",
                direction=MetricDirection.HIGHER_IS_BETTER,
            ).direction
            is MetricDirection.HIGHER_IS_BETTER
    )


def test_lower_is_better_direction_is_supported() -> None:
    assert (
            EvaluationMetricDirection(
                metric_name="synthetic_latency",
                direction=MetricDirection.LOWER_IS_BETTER,
            ).direction
            is MetricDirection.LOWER_IS_BETTER
    )


def test_empty_metric_name_is_rejected() -> None:
    with pytest.raises(ValueError, match="metric_name must not be empty"):
        EvaluationMetricDirection(
            metric_name="",
            direction=MetricDirection.HIGHER_IS_BETTER,
        )


def test_whitespace_only_metric_name_is_rejected() -> None:
    with pytest.raises(ValueError, match="metric_name must not be empty"):
        EvaluationMetricDirection(
            metric_name="   ",
            direction=MetricDirection.HIGHER_IS_BETTER,
        )


def test_non_string_metric_name_is_rejected() -> None:
    with pytest.raises(TypeError, match="metric_name must be a string"):
        EvaluationMetricDirection(
            metric_name=123,  # type: ignore[arg-type]
            direction=MetricDirection.HIGHER_IS_BETTER,
        )


def test_invalid_direction_is_rejected() -> None:
    with pytest.raises(TypeError, match="direction must be a MetricDirection"):
        EvaluationMetricDirection(
            metric_name="quality",
            direction="higher_is_better",  # type: ignore[arg-type]
        )


def test_default_answer_relevancy_direction_is_higher_is_better() -> None:
    assert (
            direction_for_metric("answer_relevancy")
            is MetricDirection.HIGHER_IS_BETTER
    )


def test_default_faithfulness_direction_is_higher_is_better() -> None:
    assert (
            direction_for_metric("faithfulness")
            is MetricDirection.HIGHER_IS_BETTER
    )


def test_unknown_metric_is_rejected() -> None:
    with pytest.raises(ValueError, match="unknown metric direction: unknown"):
        direction_for_metric("unknown")


def test_empty_lookup_metric_name_is_rejected() -> None:
    with pytest.raises(ValueError, match="metric_name must not be empty"):
        direction_for_metric("")


def test_non_string_lookup_metric_name_is_rejected() -> None:
    with pytest.raises(TypeError, match="metric_name must be a string"):
        direction_for_metric(123)  # type: ignore[arg-type]


def test_catalog_is_sorted_deterministically() -> None:
    metric_directions = (
        EvaluationMetricDirection(
            metric_name="z_metric",
            direction=MetricDirection.LOWER_IS_BETTER,
        ),
        EvaluationMetricDirection(
            metric_name="a_metric",
            direction=MetricDirection.HIGHER_IS_BETTER,
        ),
    )

    catalog = metric_direction_catalog(metric_directions)

    assert tuple(item.metric_name for item in catalog) == (
        "a_metric",
        "z_metric",
    )


def test_catalog_input_order_does_not_affect_output_order() -> None:
    first = EvaluationMetricDirection(
        metric_name="a_metric",
        direction=MetricDirection.HIGHER_IS_BETTER,
    )
    second = EvaluationMetricDirection(
        metric_name="z_metric",
        direction=MetricDirection.LOWER_IS_BETTER,
    )

    assert metric_direction_catalog((first, second)) == metric_direction_catalog(
        (second, first)
    )


def test_duplicate_metric_direction_definitions_are_rejected() -> None:
    metric_directions = (
        EvaluationMetricDirection(
            metric_name="quality",
            direction=MetricDirection.HIGHER_IS_BETTER,
        ),
        EvaluationMetricDirection(
            metric_name="quality",
            direction=MetricDirection.LOWER_IS_BETTER,
        ),
    )

    with pytest.raises(
            ValueError,
            match="duplicate metric direction definition: quality",
    ):
        metric_direction_catalog(metric_directions)


def test_catalog_input_must_be_tuple() -> None:
    with pytest.raises(TypeError, match="metric_directions must be a tuple"):
        metric_direction_catalog([])  # type: ignore[arg-type]


def test_catalog_entries_must_be_metric_direction_objects() -> None:
    with pytest.raises(
            TypeError,
            match="metric_directions must contain EvaluationMetricDirection objects",
    ):
        metric_direction_catalog(("quality",))  # type: ignore[arg-type]


def test_custom_lower_is_better_metric_can_be_resolved() -> None:
    metric_directions = (
        EvaluationMetricDirection(
            metric_name="synthetic_latency",
            direction=MetricDirection.LOWER_IS_BETTER,
        ),
    )

    assert (
            direction_for_metric(
                "synthetic_latency",
                metric_directions,
            )
            is MetricDirection.LOWER_IS_BETTER
    )


def test_empty_catalog_is_valid() -> None:
    assert metric_direction_catalog(()) == ()
