from __future__ import annotations

import sys


def print_input_error(error: object) -> None:
    print(f"Input error: {error}", file=sys.stderr)


def print_regression_execution_error(error: object) -> None:
    print(
        f"Regression execution error: {error}",
        file=sys.stderr,
    )


def print_regression_artifact_error(error: object) -> None:
    print(
        f"Regression artifact error: {error}",
        file=sys.stderr,
    )
