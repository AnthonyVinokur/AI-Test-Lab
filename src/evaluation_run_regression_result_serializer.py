from src.evaluation_run_regression_public_contract import (
    EvaluationRunRegressionResultV1,
)
from src.evaluation_run_regression_result import EvaluationRunRegressionResult
from src.public_contract import serialize_public_contract


def serialize_evaluation_run_regression_result(
    result: EvaluationRunRegressionResult,
) -> dict[str, object]:
    public_result = EvaluationRunRegressionResultV1(
        enforcement=result.enforcement.decision.value,
        exit_code=result.exit_code.code,
    )

    return serialize_public_contract(public_result)
