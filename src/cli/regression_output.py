from pathlib import Path

from src.evaluation_run_regression_result import EvaluationRunRegressionResult
from src.evaluation_run_regression_result_writer import (
    write_evaluation_run_regression_result_json,
)


def write_cli_regression_result(
    result: EvaluationRunRegressionResult,
    output_path: str | Path,
) -> None:
    """Persist an approved regression result for a CLI caller."""

    write_evaluation_run_regression_result_json(
        result,
        output_path,
    )
