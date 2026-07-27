from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pydantic import ValidationError

from src.dataset_loader import DatasetNotActiveError, EmptyDatasetError, load_dataset_tests
from src.datasets import DatasetNotFoundError, DatasetVersionNotFoundError
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AI Test Lab")
    parser.add_argument("--models", nargs="+", default=["llama3.1:latest"], help="One or more Ollama model names")
    source_group = parser.add_mutually_exclusive_group()
    source_group.add_argument("--prompts", type=Path, default=None, help="Path to prompt JSON. Defaults to prompts/prompts.json when --dataset is omitted.")
    source_group.add_argument("--dataset", help="ID of an active managed dataset")
    parser.add_argument("--dataset-storage", type=Path, default=DEFAULT_DATASET_STORAGE, help="Directory containing managed dataset JSON files")
    parser.add_argument("--dataset-version", type=int, default=None, help="Specific dataset version; latest is used by default")
    parser.add_argument("--report", type=Path, default=DEFAULT_JSON_REPORT, help="Path to JSON report")
    parser.add_argument("--html-report", type=Path, default=DEFAULT_HTML_REPORT, help="Path to HTML report")
    args = parser.parse_args()
    if args.dataset_version is not None and args.dataset is None:
        parser.error("--dataset-version requires --dataset")
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


def print_results(results: list) -> tuple[int, int, int]:
    passed = failed = errors = 0
    print("\n========== RESULTS ==========\n")
    for result in results:
        print(f"{result.test_id:<20}{result.status.value:<8}{result.reason}\n{'':20}Response: {result.actual_response}")
        print(f"{'':20}Model: {result.model}")
        print(f"{'':20}Prompt tokens: {result.prompt_tokens}")
        print(f"{'':20}Output tokens: {result.output_tokens}")
        print(f"{'':20}Response time: {result.response_time_seconds:.3f} s")
        print(f"{'':20}Prompt latency: {result.prompt_latency_seconds:.3f} s")
        print(f"{'':20}Generation latency: {result.generation_latency_seconds:.3f} s")
        print(f"{'':20}Generation speed: {result.generation_tokens_per_second:.2f} tok/s")
        print(f"{'':20}Model load time: {result.model_load_seconds:.3f} s")
        print()
        if result.status == EvaluationStatus.PASS: passed += 1
        elif result.status == EvaluationStatus.FAIL: failed += 1
        else: errors += 1
    print("=============================")
    print(f"Passed : {passed}")
    print(f"Failed : {failed}")
    print(f"Errors : {errors}")
    print(f"Total  : {len(results)}")
    return passed, failed, errors


def main() -> int:
    args = parse_args()
    try:
        test_cases = load_test_cases(args)
    except (DatasetNotFoundError, DatasetVersionNotFoundError, DatasetNotActiveError, EmptyDatasetError, FileNotFoundError, ValidationError, ValueError) as error:
        print(f"Input error: {error}", file=sys.stderr)
        return 2
    runner = MultiModelRunner(model_names=args.models, evaluator=evaluate_response)
    results = runner.run_tests(test_cases)
    JsonReporter(args.report).write(results)
    HtmlReporter(args.html_report).write(results)
    _, failed, errors = print_results(results)
    print(f"\nJSON report: {args.report}")
    print(f"HTML report: {args.html_report}")
    return 0 if failed == 0 and errors == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
