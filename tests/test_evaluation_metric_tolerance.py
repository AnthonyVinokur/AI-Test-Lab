import pytest

from src.evaluation_metric_direction import MetricDirection
from src.evaluation_metric_movement import classify_metric_movement
from src.evaluation_metric_tolerance import (
    EvaluationMetricTolerance,
    MetricToleranceStatus,
    evaluate_metric_tolerance,
)


def make_movement(
    baseline: float,
    candidate: float,
    direction: MetricDirection = MetricDirection.HIGHER_IS_BETTER,
):
    return classify_metric_movement(
        baseline_score=baseline,
        candidate_score=candidate,
        direction=direction,
    )


def test_regression_below_tolerance_is_within_tolerance():
    movement = make_movement(0.90, 0.895)

    result = evaluate_metric_tolerance(movement, 0.01)

    assert result.status is MetricToleranceStatus.WITHIN_TOLERANCE


def test_regression_exactly_at_tolerance_is_within_tolerance():
    movement = make_movement(0.90, 0.89)

    result = evaluate_metric_tolerance(movement, 0.01)

    assert result.status is MetricToleranceStatus.WITHIN_TOLERANCE


def test_regression_above_tolerance_exceeds_tolerance():
    movement = make_movement(0.90, 0.85)

    result = evaluate_metric_tolerance(movement, 0.01)

    assert result.status is MetricToleranceStatus.EXCEEDS_TOLERANCE


def test_improvement_is_not_applicable():
    movement = make_movement(0.80, 0.90)

    result = evaluate_metric_tolerance(movement, 0.01)

    assert result.status is MetricToleranceStatus.NOT_APPLICABLE


def test_unchanged_is_not_applicable():
    movement = make_movement(0.80, 0.80)

    result = evaluate_metric_tolerance(movement, 0.01)

    assert result.status is MetricToleranceStatus.NOT_APPLICABLE


def test_lower_is_better_regression_uses_existing_movement_semantics():
    movement = make_movement(
        0.40,
        0.45,
        MetricDirection.LOWER_IS_BETTER,
    )

    result = evaluate_metric_tolerance(movement, 0.02)

    assert result.status is MetricToleranceStatus.EXCEEDS_TOLERANCE


def test_zero_tolerance_rejects_any_regression():
    movement = make_movement(0.90, 0.89)

    result = evaluate_metric_tolerance(movement, 0.0)

    assert result.status is MetricToleranceStatus.EXCEEDS_TOLERANCE


def test_zero_tolerance_is_valid():
    movement = make_movement(0.90, 0.90)

    result = evaluate_metric_tolerance(movement, 0.0)

    assert result.tolerance == 0.0


def test_one_tolerance_is_valid():
    movement = make_movement(1.0, 0.0)

    result = evaluate_metric_tolerance(movement, 1.0)

    assert result.status is MetricToleranceStatus.WITHIN_TOLERANCE


def test_negative_tolerance_is_rejected():
    movement = make_movement(0.90, 0.80)

    with pytest.raises(ValueError, match="between 0.0 and 1.0"):
        evaluate_metric_tolerance(movement, -0.01)


def test_tolerance_above_one_is_rejected():
    movement = make_movement(0.90, 0.80)

    with pytest.raises(ValueError, match="between 0.0 and 1.0"):
        evaluate_metric_tolerance(movement, 1.01)


@pytest.mark.parametrize(
    "invalid_tolerance",
    ["0.1", None, [], {}],
)
def test_non_numeric_tolerance_is_rejected(invalid_tolerance):
    movement = make_movement(0.90, 0.80)

    with pytest.raises(TypeError, match="numeric"):
        evaluate_metric_tolerance(movement, invalid_tolerance)


@pytest.mark.parametrize("invalid_tolerance", [True, False])
def test_boolean_tolerance_is_rejected(invalid_tolerance):
    movement = make_movement(0.90, 0.80)

    with pytest.raises(TypeError, match="numeric"):
        evaluate_metric_tolerance(movement, invalid_tolerance)


def test_invalid_movement_type_is_rejected():
    with pytest.raises(
        TypeError,
        match="EvaluationMetricMovement",
    ):
        evaluate_metric_tolerance("regression", 0.01)


def test_result_records_magnitude_and_tolerance():
    movement = make_movement(0.90, 0.85)

    result = evaluate_metric_tolerance(movement, 0.02)

    assert result.magnitude == pytest.approx(0.05)
    assert result.tolerance == 0.02


def test_result_is_immutable():
    movement = make_movement(0.90, 0.85)
    result = evaluate_metric_tolerance(movement, 0.02)

    with pytest.raises(Exception):
        result.tolerance = 0.50


def test_evaluation_is_deterministic():
    movement = make_movement(0.90, 0.85)

    first = evaluate_metric_tolerance(movement, 0.02)
    second = evaluate_metric_tolerance(movement, 0.02)

    assert first == second


def test_returns_evaluation_metric_tolerance_contract():
    movement = make_movement(0.90, 0.85)

    result = evaluate_metric_tolerance(movement, 0.02)

    assert isinstance(result, EvaluationMetricTolerance)