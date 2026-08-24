from dataclasses import dataclass

from src.evaluation_run_regression_enforcement import (
    EvaluationRunRegressionEnforcement,
    EvaluationRunRegressionEnforcementDecision,
)


@dataclass(frozen=True)
class EvaluationRunRegressionExitCode:
    code: int


def map_evaluation_run_regression_exit_code(
    enforcement: EvaluationRunRegressionEnforcement,
) -> EvaluationRunRegressionExitCode:
    if enforcement.decision == EvaluationRunRegressionEnforcementDecision.BLOCK:
        code = 1
    else:
        code = 0

    return EvaluationRunRegressionExitCode(code=code)
