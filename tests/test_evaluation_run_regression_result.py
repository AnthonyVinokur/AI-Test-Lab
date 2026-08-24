from dataclasses import FrozenInstanceError

import pytest

from src.evaluation_run_regression_enforcement import (
    EvaluationRunRegressionEnforcement,
    EvaluationRunRegressionEnforcementDecision,
)
from src.evaluation_run_regression_exit_code import (
    EvaluationRunRegressionExitCode,
)
from src.evaluation_run_regression_result import (
    EvaluationRunRegressionResult,
    build_evaluation_run_regression_result,
)


def test_allow_produces_zero_exit_code_result() -> None:
    enforcement = EvaluationRunRegressionEnforcement(
        decision=EvaluationRunRegressionEnforcementDecision.ALLOW,
    )

    result = build_evaluation_run_regression_result(enforcement)

    assert result == EvaluationRunRegressionResult(
        enforcement=enforcement,
        exit_code=EvaluationRunRegressionExitCode(code=0),
    )


def test_block_produces_one_exit_code_result() -> None:
    enforcement = EvaluationRunRegressionEnforcement(
        decision=EvaluationRunRegressionEnforcementDecision.BLOCK,
    )

    result = build_evaluation_run_regression_result(enforcement)

    assert result == EvaluationRunRegressionResult(
        enforcement=enforcement,
        exit_code=EvaluationRunRegressionExitCode(code=1),
    )


def test_same_enforcement_produces_same_result() -> None:
    enforcement = EvaluationRunRegressionEnforcement(
        decision=EvaluationRunRegressionEnforcementDecision.BLOCK,
    )

    first = build_evaluation_run_regression_result(enforcement)
    second = build_evaluation_run_regression_result(enforcement)

    assert first == second


def test_result_preserves_enforcement() -> None:
    enforcement = EvaluationRunRegressionEnforcement(
        decision=EvaluationRunRegressionEnforcementDecision.ALLOW,
    )

    result = build_evaluation_run_regression_result(enforcement)

    assert result.enforcement is enforcement


def test_result_is_immutable() -> None:
    enforcement = EvaluationRunRegressionEnforcement(
        decision=EvaluationRunRegressionEnforcementDecision.ALLOW,
    )
    result = build_evaluation_run_regression_result(enforcement)

    with pytest.raises(FrozenInstanceError):
        result.exit_code = EvaluationRunRegressionExitCode(
            code=1,
        )  # type: ignore[misc]
