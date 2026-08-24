from dataclasses import dataclass

from src.evaluation_run_regression_enforcement import (
    EvaluationRunRegressionEnforcement,
)
from src.evaluation_run_regression_exit_code import (
    EvaluationRunRegressionExitCode,
    map_evaluation_run_regression_exit_code,
)


@dataclass(frozen=True)
class EvaluationRunRegressionResult:
    enforcement: EvaluationRunRegressionEnforcement
    exit_code: EvaluationRunRegressionExitCode


def build_evaluation_run_regression_result(
    enforcement: EvaluationRunRegressionEnforcement,
) -> EvaluationRunRegressionResult:
    exit_code = map_evaluation_run_regression_exit_code(enforcement)

    return EvaluationRunRegressionResult(
        enforcement=enforcement,
        exit_code=exit_code,
    )
