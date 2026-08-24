from src.evaluation_run_regression_result import EvaluationRunRegressionResult


def serialize_evaluation_run_regression_result(
    result: EvaluationRunRegressionResult,
) -> dict[str, object]:
    return {
        "enforcement": result.enforcement.decision.value,
        "exit_code": result.exit_code.code,
    }

