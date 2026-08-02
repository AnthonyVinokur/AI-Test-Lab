from __future__ import annotations

import sys

from pydantic import ValidationError

from src.cli.arguments import parse_args
from src.cli.execution import load_test_cases
from src.cli.output import print_results
from src.dataset_loader import DatasetNotActiveError, EmptyDatasetError
from src.datasets import DatasetNotFoundError, DatasetVersionNotFoundError
from src.evaluator import evaluate_response
from src.html_reporter import HtmlReporter
from src.json_reporter import JsonReporter
from src.multi_model_runner import MultiModelRunner


INPUT_EXCEPTIONS = (
    DatasetNotFoundError,
    DatasetVersionNotFoundError,
    DatasetNotActiveError,
    EmptyDatasetError,
    FileNotFoundError,
    ValidationError,
    ValueError,
)


def main(argv: list[str] | None = None) -> int:
    """Run AI Test Lab from the command line."""

    args = parse_args(argv)

    try:
        test_cases = load_test_cases(args)
    except INPUT_EXCEPTIONS as error:
        print(f"Input error: {error}", file=sys.stderr)
        return 2

    runner = MultiModelRunner(
        model_names=args.models,
        evaluator=evaluate_response,
    )

    results = runner.run_tests(test_cases)

    JsonReporter(args.report).write(results)
    HtmlReporter(args.html_report).write(results)

    (
        _,
        _,
        unexpected_failures,
        errors,
    ) = print_results(results)

    print(f"\nJSON report: {args.report}")
    print(f"HTML report: {args.html_report}")

    if unexpected_failures > 0 or errors > 0:
        return 1

    return 0