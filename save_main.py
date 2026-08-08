from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

from pydantic import ValidationError

from src.dataset_loader import DatasetNotActiveError, EmptyDatasetError, load_dataset_tests
from src.datasets import (
    DatasetNotFoundError,
    DatasetVersionNotFoundError, JsonDatasetRepository, DatasetService, DatasetStatus,DatasetVersion
)
from src.evaluator import evaluate_response
from src.html_reporter import HtmlReporter
from src.json_reporter import JsonReporter
from src.models import EvaluationStatus
from src.multi_model_runner import MultiModelRunner
from src.prompt_loader import load_prompt_tests

DEFAULT_PROMPTS = Path("prompts/prompts.json")
DEFAULT_DATASET_STORAGE = Path("datasets")
DEFAULT_JSON_REPORT = Path("results/latest_results.json")
DEFAULT_HTML_REPORT = Path("results/latest_report.html")

def print_dataset_info(
    dataset_id: str,
    storage_dir: Path,
    version: int | None = None,
) -> int:
    service = DatasetService(JsonDatasetRepository(storage_dir))

    dataset = service.get_dataset(dataset_id)

    if version is None:
        selected = dataset.latest()
    else:
        loaded = service.get_dataset(dataset_id, version)

        if not hasattr(loaded, "entries"):
            raise TypeError("Expected DatasetVersion")

        selected = loaded

    enabled = sum(entry.enabled for entry in selected.entries)
    disabled = len(selected.entries) - enabled

    categories = Counter(
        entry.category
        for entry in selected.entries
    )

    tags = sorted(
        {
            tag
            for entry in selected.entries
            for tag in entry.tags
        }
    )

    average_prompt_length = (
        sum(len(entry.input) for entry in selected.entries)
        / len(selected.entries)
        if selected.entries
        else 0
    )

    print("\nDataset Information")
    print("===================")
    print(f"Name             : {dataset.manifest.name}")
    print(f"ID               : {dataset.manifest.id}")
    print(f"Status           : {dataset.manifest.status.value.upper()}")
    print(f"Latest version   : {dataset.manifest.latest_version}")
    print(f"Viewing version  : {selected.version}")
    print(f"Description      : {dataset.manifest.description or 'None'}")

    print("\nStatistics")
    print("----------")
    print(f"Entries          : {len(selected.entries)}")
    print(f"Enabled          : {enabled}")
    print(f"Disabled         : {disabled}")
    print(f"Average prompt   : {average_prompt_length:.1f} characters")

    print("\nCategories")
    print("----------")

    if categories:
        for category, count in sorted(categories.items()):
            print(f"{category:<20} {count}")
    else:
        print("None")

    print("\nTags")
    print("----")

    if tags:
        for tag in tags:
            print(tag)
    else:
        print("None")

    print("\nChecksum")
    print("--------")
    print(selected.checksum)

    return 0
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AI Test Lab")

    parser.add_argument("--models", nargs="+", default=["llama3.1:latest"], help="One or more Ollama model names")

    source_group = parser.add_mutually_exclusive_group()

    source_group.add_argument("--prompts", type=Path, default=None,
                              help="Path to prompt JSON. Defaults to prompts/prompts.json when --dataset is omitted.")

    source_group.add_argument("--dataset", help="ID of an active managed dataset")

    parser.add_argument("--dataset-storage", type=Path, default=DEFAULT_DATASET_STORAGE,
                        help="Directory containing managed dataset JSON files")

    parser.add_argument("--report", type=Path, default=DEFAULT_JSON_REPORT, help="Path to JSON report")
    parser.add_argument("--html-report", type=Path, default=DEFAULT_HTML_REPORT, help="Path to HTML report")



    parser.add_argument(
        "--dataset-version",
        type=int,
        default=None,
        help="Specific dataset version; latest is used by default",
    )

    parser.add_argument(
        "--list-datasets",
        action="store_true",
        help="List available managed datasets and exit",
    )
    parser.add_argument(
        "--dataset-info",
        help="Show information about a managed dataset and exit",
    )

    args = parser.parse_args()

    if (
            args.dataset_version is not None
            and args.dataset is None
            and args.dataset_info is None
    ):
        parser.error(
            "--dataset-version requires --dataset or --dataset-info"
        )
    return args


def load_test_cases(args: argparse.Namespace) -> list:
    if args.dataset:
        test_cases = load_dataset_tests(args.dataset, storage_dir=args.dataset_storage, version=args.dataset_version)
        selected_version = str(args.dataset_version) if args.dataset_version is not None else "latest"
        print(f"Loaded {len(test_cases)} test(s) from dataset {args.dataset}, version {selected_version}.")
        return test_cases
    prompt_path = args.prompts or DEFAULT_PROMPTS
    test_cases = load_prompt_tests(prompt_path)
    print(f"Loaded {len(test_cases)} test(s) from prompt file {prompt_path}.")
    return test_cases

def list_available_datasets(storage_dir: Path) -> int:
    service = DatasetService(JsonDatasetRepository(storage_dir))
    datasets = service.list_datasets()

    print("\nAvailable datasets")
    print("==================")

    if not datasets:
        print("No datasets found.")
        return 0

    for dataset in datasets:
        status_marker = {
            DatasetStatus.ACTIVE: "[ACTIVE]",
            DatasetStatus.DRAFT: "[DRAFT]",
            DatasetStatus.ARCHIVED: "[ARCHIVED]",
        }[dataset.status]

        print(
            f"{status_marker:<12} "
            f"{dataset.name} "
            f"(id={dataset.id}, version={dataset.latest_version})"
        )

        if dataset.description:
            print(f"{'':12} {dataset.description}")

        if dataset.tags:
            print(f"{'':12} Tags: {', '.join(dataset.tags)}")

    print(f"\nTotal datasets: {len(datasets)}")
    return 0


def print_results(results: list) -> tuple[int, int, int, int]:
    passed = 0
    expected_failures = 0
    unexpected_failures = 0
    errors = 0

    print("\n========== RESULTS ==========\n")

    for result in results:
        print(
            f"{result.test_id:<20}"
            f"{result.status.value:<8}"
            f"{result.reason}\n"
            f"{'':20}Response: {result.actual_response}"
        )
        print(f"{'':20}Model: {result.model}")
        print(f"{'':20}Prompt tokens: {result.prompt_tokens}")
        print(f"{'':20}Output tokens: {result.output_tokens}")
        print(f"{'':20}Response time: {result.response_time_seconds:.3f} s")
        print(f"{'':20}Prompt latency: {result.prompt_latency_seconds:.3f} s")
        print(
            f"{'':20}Generation latency: "
            f"{result.generation_latency_seconds:.3f} s"
        )
        print(
            f"{'':20}Generation speed: "
            f"{result.generation_tokens_per_second:.2f} tok/s"
        )
        print(f"{'':20}Model load time: {result.model_load_seconds:.3f} s")
        print()

        if result.status == EvaluationStatus.PASS:
            passed += 1
        elif result.status == EvaluationStatus.XFAIL:
            expected_failures += 1
        elif result.status == EvaluationStatus.FAIL:
            unexpected_failures += 1
        elif result.status == EvaluationStatus.ERROR:
            errors += 1

    total = len(results)

    print("=============================")
    print(f"Passed              : {passed}")
    print(f"Expected failures   : {expected_failures}")
    print(f"Unexpected failures : {unexpected_failures}")
    print(f"Errors              : {errors}")
    print(f"Total               : {total}")

    return passed, expected_failures, unexpected_failures, errors


def main() -> int:

    args = parse_args()

    if args.list_datasets:
        return list_available_datasets(args.dataset_storage)

    if args.dataset_info:
        return print_dataset_info(
            args.dataset_info,
            args.dataset_storage,
            args.dataset_version,
        )

    try:
        test_cases = load_test_cases(args)

    except (
    DatasetNotFoundError, DatasetVersionNotFoundError, DatasetNotActiveError, EmptyDatasetError, FileNotFoundError,
    ValidationError, ValueError) as error:
        print(f"Input error: {error}", file=sys.stderr)
        return 2
    runner = MultiModelRunner(model_names=args.models, evaluator=evaluate_response)
    results = runner.run_tests(test_cases)
    JsonReporter(args.report).write(results)
    HtmlReporter(args.html_report).write(results)

    (
        _,
        expected_failures,
        unexpected_failures,
        errors,
    ) = print_results(results)

    print(f"\nJSON report: {args.report}")
    print(f"HTML report: {args.html_report}")

    return 0 if unexpected_failures == 0 and errors == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
