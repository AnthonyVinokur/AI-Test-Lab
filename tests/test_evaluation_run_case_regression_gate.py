from dataclasses import FrozenInstanceError

import pytest

from src.evaluation_run_case_regression_gate import (
    EvaluationRunCaseRegressionGateDecision,
    evaluate_run_case_regression_gate,
)
from src.evaluation_run_regression_comparison import (
    EvaluationRunRegressionComparison,
)


def make_comparison(
    *,
    compared_count: int,
    unchanged_count: int = 0,
    improved_count: int = 0,
    regressed_count: int = 0,
) -> EvaluationRunRegressionComparison:
    return EvaluationRunRegressionComparison(
        baseline_run_id="run-001",
        candidate_run_id="run-002",
        compared_count=compared_count,
        unchanged_count=unchanged_count,
        improved_count=improved_count,
        regressed_count=regressed_count,
        case_comparisons=(),
    )


def test_no_regressed_cases_produce_pass():
    comparison = make_comparison(
        compared_count=2,
        unchanged_count=1,
        improved_count=1,
    )

    result = evaluate_run_case_regression_gate(comparison)

    assert (
        result.decision
        == EvaluationRunCaseRegressionGateDecision.PASS
    )
    assert result.compared_count == 2
    assert result.unchanged_count == 1
    assert result.improved_count == 1
    assert result.regressed_count == 0


def test_any_regressed_case_produces_fail():
    comparison = make_comparison(
        compared_count=3,
        unchanged_count=1,
        improved_count=1,
        regressed_count=1,
    )

    result = evaluate_run_case_regression_gate(comparison)

    assert (
        result.decision
        == EvaluationRunCaseRegressionGateDecision.FAIL
    )
    assert result.compared_count == 3
    assert result.unchanged_count == 1
    assert result.improved_count == 1
    assert result.regressed_count == 1


def test_empty_comparison_is_not_applicable():
    comparison = make_comparison(compared_count=0)

    result = evaluate_run_case_regression_gate(comparison)

    assert (
        result.decision
        == EvaluationRunCaseRegressionGateDecision.NOT_APPLICABLE
    )
    assert result.compared_count == 0
    assert result.unchanged_count == 0
    assert result.improved_count == 0
    assert result.regressed_count == 0


def test_same_comparison_produces_same_gate():
    comparison = make_comparison(
        compared_count=1,
        regressed_count=1,
    )

    first = evaluate_run_case_regression_gate(comparison)
    second = evaluate_run_case_regression_gate(comparison)

    assert first == second


def test_gate_is_immutable():
    comparison = make_comparison(
        compared_count=1,
        unchanged_count=1,
    )
    result = evaluate_run_case_regression_gate(comparison)

    with pytest.raises(FrozenInstanceError):
        result.decision = (
            EvaluationRunCaseRegressionGateDecision.FAIL
        )


def test_non_comparison_input_is_rejected():
    with pytest.raises(
        TypeError,
        match=(
            "comparison must be an "
            "EvaluationRunRegressionComparison"
        ),
    ):
        evaluate_run_case_regression_gate(
            object(),  # type: ignore[arg-type]
        )
