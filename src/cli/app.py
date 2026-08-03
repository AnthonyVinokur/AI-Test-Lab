from __future__ import annotations

import sys

from pydantic import ValidationError

from src.cli.arguments import parse_args
from src.cli.execution import load_test_cases
from src.cli.output import print_results
from src.dataset_loader import DatasetNotActiveError, EmptyDatasetError
from src.datasets import (
    DatasetNotFoundError,
    DatasetVersionNotFoundError,
    JsonDatasetRepository,
    validate_dataset,
)
from src.evaluation_factory import create_engine
from src.html_reporter import HtmlReporter
from src.json_reporter import JsonReporter
from src.multi_model_runner import MultiModelRunner
from src.evaluation_engines import AssertionEvaluationEngine


INPUT_EXCEPTIONS = (
    DatasetNotFoundError,
    DatasetVersionNotFoundError,
    DatasetNotActiveError,
    EmptyDatasetError,
    FileNotFoundError,
    ValidationError,
    ValueError,
)


def print_dataset_validation(args) -> int:
    """Validate a managed dataset and print all discovered issues."""

    repository = JsonDatasetRepository(args.dataset_storage)
    dataset = repository.get(args.validate_dataset)

    if args.dataset_version is not None:
        selected_version = next(
            (
                version
                for version in dataset.versions
                if version.version == args.dataset_version
            ),
            None,
        )

        if selected_version is None:
            raise DatasetVersionNotFoundError(args.dataset_version)

        dataset = dataset.model_copy(
            update={
                "manifest": dataset.manifest.model_copy(
                    update={
                        "latest_version": selected_version.version,
                    }
                ),
                "versions": [selected_version],
            }
        )

    result = validate_dataset(dataset)

    print(
        f"Dataset {result.dataset_id}: "
        f"{len(result.errors)} error(s), "
        f"{len(result.warnings)} warning(s)"
    )

    for issue in result.issues:
        location_parts: list[str] = []

        if issue.version is not None:
            location_parts.append(f"version={issue.version}")

        if issue.entry_id is not None:
            location_parts.append(f"entry={issue.entry_id}")

        location = (
            f" ({', '.join(location_parts)})"
            if location_parts
            else ""
        )

        print(
            f"[{issue.severity.value.upper()}] "
            f"{issue.code}: "
            f"{issue.message}"
            f"{location}"
        )

    if result.is_valid:
        print("\nDataset validation passed.")
        return 0

    print("\nDataset validation failed.")
    return 1


def main(argv: list[str] | None = None) -> int:
    """Run AI Test Lab from the command line."""

    args = parse_args(argv)

    try:
        if args.validate_dataset:
            return print_dataset_validation(args)

        test_cases = load_test_cases(args)

    except INPUT_EXCEPTIONS as error:
        print(f"Input error: {error}", file=sys.stderr)
        return 2



    # runner = MultiModelRunner(
    #     model_names=args.models,
    #     evaluation_engine=AssertionEvaluationEngine(),
    # )
    from src.evaluation_factory import create_engine

    runner = MultiModelRunner(
        model_names=args.models,
        evaluation_engine=create_engine(args.engine),
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

if __name__ == "__main__":
    raise SystemExit(main())