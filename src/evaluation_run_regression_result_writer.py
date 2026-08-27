from pathlib import Path

from src.evaluation_run_regression_result import EvaluationRunRegressionResult
from src.evaluation_run_regression_result_json import (
    encode_evaluation_run_regression_result_json,
)


class EvaluationRunRegressionResultWriteError(RuntimeError):
    """Raised when a regression result artifact cannot be persisted."""


def write_evaluation_run_regression_result_json(
    result: EvaluationRunRegressionResult,
    path: str | Path,
) -> None:
    output_path = Path(path)

    try:
        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        output_path.write_text(
            encode_evaluation_run_regression_result_json(result),
            encoding="utf-8",
        )

    except OSError as error:
        raise EvaluationRunRegressionResultWriteError(
            f"failed to write regression result artifact "
            f"to '{output_path}': {error}"
        ) from error
