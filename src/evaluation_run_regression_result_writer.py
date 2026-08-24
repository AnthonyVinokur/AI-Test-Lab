from pathlib import Path

from src.evaluation_run_regression_result import EvaluationRunRegressionResult
from src.evaluation_run_regression_result_json import (
    encode_evaluation_run_regression_result_json,
)


def write_evaluation_run_regression_result_json(
    result: EvaluationRunRegressionResult,
    path: str | Path,
) -> None:
    output_path = Path(path)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_text(
        encode_evaluation_run_regression_result_json(result),
        encoding="utf-8",
    )
