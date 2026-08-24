import json

from src.evaluation_run_regression_result import EvaluationRunRegressionResult
from src.evaluation_run_regression_result_serializer import (
    serialize_evaluation_run_regression_result,
)


def encode_evaluation_run_regression_result_json(
    result: EvaluationRunRegressionResult,
) -> str:
    serialized = serialize_evaluation_run_regression_result(result)

    return json.dumps(
        serialized,
        separators=(",", ":"),
    )
