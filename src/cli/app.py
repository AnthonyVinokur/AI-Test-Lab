from __future__ import annotations

from pydantic import ValidationError

from src.evaluation_run_identity import (
    create_evaluation_run_identity,
)

from src.evaluation_run_regression_entry_point import (
    execute_evaluation_run_regression,
)

from src.cli.arguments import parse_args
from src.cli.execution import load_test_cases
from src.cli.output import (
            print_evaluation_profiles,
            print_results,
        )
from src.dataset_loader import DatasetNotActiveError, EmptyDatasetError
from src.datasets import (
    DatasetNotFoundError,
    DatasetVersionNotFoundError,
    JsonDatasetRepository,
    validate_dataset,
)
from src.evaluation_config import EvaluationConfigError, load_evaluation_profile, create_pipeline_from_profile, \
    list_profiles
from src.evaluation_pipeline import EvaluationPipeline
from src.html_reporter import HtmlReporter
from src.json_reporter import JsonReporter
from src.multi_model_runner import MultiModelRunner

from src.cli.regression_output import (
    write_cli_regression_result,
)

from src.evaluation_run_regression_result import (
    build_evaluation_run_regression_result,
)

from src.evaluation_run_regression_result_writer import (
    EvaluationRunRegressionResultWriteError,
)

from src.cli.diagnostics import (
    print_input_error,
    print_regression_artifact_error,
    print_regression_execution_error,
)

from src.cli.exit_codes import CliExitCode


INPUT_EXCEPTIONS = (
    DatasetNotFoundError,
    DatasetVersionNotFoundError,
    DatasetNotActiveError,
    EmptyDatasetError,
    FileNotFoundError,
    ValidationError,
    EvaluationConfigError,
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

    regression_requested = (
        args.regression_result_output is not None
    )

    if regression_requested:
        if args.dataset is None:
            print_input_error(
                "regression execution requires a managed --dataset."
            )
            return CliExitCode.INPUT_ERROR

        if args.dataset_version is None:
            print_input_error(
                "regression execution requires an explicit "
                "--dataset-version."
            )
            return CliExitCode.INPUT_ERROR

        if len(args.models) != 1:
            print_input_error(
                "regression execution requires exactly one model."
            )
            return CliExitCode.INPUT_ERROR
    try:
        if args.validate_dataset:
            return print_dataset_validation(args)

        if args.list_evaluation_profiles:
            print_evaluation_profiles(list_profiles())
            return 0

        if args.evaluation_profile is not None:
            profile = load_evaluation_profile(
                args.evaluation_profile
            )

            pipeline = create_pipeline_from_profile(profile)

            enabled_engines = [
                engine.name
                for engine in profile.engines
                if engine.enabled
            ]

            print(
                f"Loaded evaluation profile "
                f"'{profile.name}' version {profile.version}."
            )
            print(
                "Enabled evaluation engines: "
                f"{', '.join(enabled_engines)}"
            )

        else:
            pipeline = EvaluationPipeline()

        test_cases = load_test_cases(args)



    except INPUT_EXCEPTIONS as error:

        print_input_error(error)

        return CliExitCode.INPUT_ERROR

    # This block must be outside the profile if/else.
    runner = MultiModelRunner(
        model_names=args.models,
        evaluation_pipeline=pipeline,
    )

    results = runner.run_tests(test_cases)

    JsonReporter(args.report).write(results)
    HtmlReporter(args.html_report).write(results)

    regression_result = None

    if regression_requested:
        candidate_identity = create_evaluation_run_identity(
            model=args.models[0],
            evaluation_profile=(
                args.evaluation_profile
                if args.evaluation_profile is not None
                else "default"
            ),
            dataset=args.dataset,
        )

        try:
            regression_execution = execute_evaluation_run_regression(
                candidate_results=results,
                baseline_report_path=args.regression_baseline_report,
                baseline_provenance_path=args.regression_baseline_provenance,
                candidate_identity=candidate_identity,
                candidate_dataset_version=str(args.dataset_version),
                report_schema_version="1.0",
            )


        except Exception as error:
            print_regression_execution_error(error)
            return CliExitCode.INFRASTRUCTURE_ERROR

        regression_result = build_evaluation_run_regression_result(
            regression_execution.enforcement
        )

        try:
            write_cli_regression_result(
                regression_result,
                args.regression_result_output,
            )
        except EvaluationRunRegressionResultWriteError as error:
            print_regression_artifact_error(error)
            return CliExitCode.INFRASTRUCTURE_ERROR

    (
        _,
        _,
        unexpected_failures,
        errors,
    ) = print_results(results)

    print(f"\nJSON report: {args.report}")
    print(f"HTML report: {args.html_report}")

    if regression_result is not None:
        return regression_result.exit_code.code

    if unexpected_failures > 0 or errors > 0:
        return CliExitCode.FAILURE

    return CliExitCode.SUCCESS

if __name__ == "__main__":
    raise SystemExit(main())
