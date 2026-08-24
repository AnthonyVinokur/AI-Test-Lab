from dataclasses import FrozenInstanceError

import pytest

from src.evaluation_run_regression_enforcement import (
    EvaluationRunRegressionEnforcement,
    EvaluationRunRegressionEnforcementDecision,
)
from src.evaluation_run_regression_exit_code import (
    EvaluationRunRegressionExitCode,
    map_evaluation_run_regression_exit_code,
)


def test_allow_maps_to_zero() -> None:
    enforcement = EvaluationRunRegressionEnforcement(
        decision=EvaluationRunRegressionEnforcementDecision.ALLOW,
    )

    result = map_evaluation_run_regression_exit_code(enforcement)

    assert result == EvaluationRunRegressionExitCode(code=0)


def test_block_maps_to_one() -> None:
    enforcement = EvaluationRunRegressionEnforcement(
        decision=EvaluationRunRegressionEnforcementDecision.BLOCK,
    )

    result = map_evaluation_run_regression_exit_code(enforcement)

    assert result == EvaluationRunRegressionExitCode(code=1)


def test_same_enforcement_produces_same_exit_code() -> None:
    enforcement = EvaluationRunRegressionEnforcement(
        decision=EvaluationRunRegressionEnforcementDecision.BLOCK,
    )

    first = map_evaluation_run_regression_exit_code(enforcement)
    second = map_evaluation_run_regression_exit_code(enforcement)

    assert first == second


def test_exit_code_result_is_immutable() -> None:
    result = EvaluationRunRegressionExitCode(code=0)

    with pytest.raises(FrozenInstanceError):
        result.code = 1  # type: ignore[misc]


def test_mapping_does_not_raise_system_exit() -> None:
    enforcement = EvaluationRunRegressionEnforcement(
        decision=EvaluationRunRegressionEnforcementDecision.BLOCK,
    )

    result = map_evaluation_run_regression_exit_code(enforcement)

    assert result.code == 1
