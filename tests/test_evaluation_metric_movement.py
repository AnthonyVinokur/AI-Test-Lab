import pytest

from src.evaluation_metric_direction import MetricDirection
from src.evaluation_metric_movement import (
    MetricMovement,
    classify_metric_movement,
)


def test_higher_is_better_increase_is_improvement():
    result = classify_metric_movement(
        baseline_score=0.80,
        candidate_score=0.90,
        direction=MetricDirection.HIGHER_IS_BETTER,
    )

    assert result.movement == MetricMovement.IMPROVEMENT
    assert result.delta == pytest.approx(0.10)
    assert result.magnitude == pytest.approx(0.10)


def test_higher_is_better_decrease_is_regression():
    result = classify_metric_movement(
        baseline_score=0.90,
        candidate_score=0.80,
        direction=MetricDirection.HIGHER_IS_BETTER,
    )

    assert result.movement == MetricMovement.REGRESSION
    assert result.delta == pytest.approx(-0.10)
    assert result.magnitude == pytest.approx(0.10)


def test_higher_is_better_equal_is_unchanged():
    result = classify_metric_movement(
        baseline_score=0.85,
        candidate_score=0.85,
        direction=MetricDirection.HIGHER_IS_BETTER,
    )

    assert result.movement == MetricMovement.UNCHANGED
    assert result.delta == 0.0
    assert result.magnitude == 0.0


def test_lower_is_better_decrease_is_improvement():
    result = classify_metric_movement(
        baseline_score=0.80,
        candidate_score=0.60,
        direction=MetricDirection.LOWER_IS_BETTER,
    )

    assert result.movement == MetricMovement.IMPROVEMENT
    assert result.delta == pytest.approx(-0.20)
    assert result.magnitude == pytest.approx(0.20)


def test_lower_is_better_increase_is_regression():
    result = classify_metric_movement(
        baseline_score=0.60,
        candidate_score=0.80,
        direction=MetricDirection.LOWER_IS_BETTER,
    )

    assert result.movement == MetricMovement.REGRESSION
    assert result.delta == pytest.approx(0.20)
    assert result.magnitude == pytest.approx(0.20)


def test_lower_is_better_equal_is_unchanged():
    result = classify_metric_movement(
        baseline_score=0.70,
        candidate_score=0.70,
        direction=MetricDirection.LOWER_IS_BETTER,
    )

    assert result.movement == MetricMovement.UNCHANGED


@pytest.mark.parametrize("score", [-0.01, 1.01])
def test_baseline_score_out_of_range_is_rejected(score):
    with pytest.raises(ValueError):
        classify_metric_movement(
            baseline_score=score,
            candidate_score=0.50,
            direction=MetricDirection.HIGHER_IS_BETTER,
        )


@pytest.mark.parametrize("score", [-0.01, 1.01])
def test_candidate_score_out_of_range_is_rejected(score):
    with pytest.raises(ValueError):
        classify_metric_movement(
            baseline_score=0.50,
            candidate_score=score,
            direction=MetricDirection.HIGHER_IS_BETTER,
        )


@pytest.mark.parametrize("score", ["0.5", None, True])
def test_invalid_baseline_score_type_is_rejected(score):
    with pytest.raises(TypeError):
        classify_metric_movement(
            baseline_score=score,
            candidate_score=0.50,
            direction=MetricDirection.HIGHER_IS_BETTER,
        )


@pytest.mark.parametrize("score", ["0.5", None, False])
def test_invalid_candidate_score_type_is_rejected(score):
    with pytest.raises(TypeError):
        classify_metric_movement(
            baseline_score=0.50,
            candidate_score=score,
            direction=MetricDirection.HIGHER_IS_BETTER,
        )


def test_invalid_direction_type_is_rejected():
    with pytest.raises(TypeError):
        classify_metric_movement(
            baseline_score=0.50,
            candidate_score=0.60,
            direction="higher_is_better",
        )


def test_boundary_scores_are_supported():
    result = classify_metric_movement(
        baseline_score=0.0,
        candidate_score=1.0,
        direction=MetricDirection.HIGHER_IS_BETTER,
    )

    assert result.movement == MetricMovement.IMPROVEMENT
    assert result.delta == 1.0
    assert result.magnitude == 1.0
