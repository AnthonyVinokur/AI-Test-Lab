from __future__ import annotations

import argparse
from src.multi_model_runner import MultiModelRunner
from src.evaluator import evaluate_response
from src.json_reporter import JsonReporter
from src.models import EvaluationStatus
from src.prompt_loader import load_prompt_tests
from pathlib import Path

#version 1.0
from src.html_reporter import HtmlReporter


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AI Test Lab")

    # parser.add_argument(
    #     "--model",
    #     default="llama3.1:latest",
    #     help="Ollama model name",
    # )

    parser.add_argument(
        "--models",
        nargs="+",
        default=["llama3.1:latest"],
        help="One or more Ollama model names",
    )
    parser.add_argument(
        "--prompts",
        type=Path,
        default=Path("prompts/prompts.json"),
        help="Path to prompt definition file",
    )

    parser.add_argument(
        "--report",
        type=Path,
        default=Path("results/latest_results.json"),
        help="Path to the JSON report file",
    )

    return parser.parse_args()


def print_results(results: list) -> tuple[int, int, int]:
    passed = 0
    failed = 0
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
        print(
            f"{'':20}Response time: "
            f"{result.response_time_seconds:.3f} s"
        )
        print(
            f"{'':20}Prompt latency: "
            f"{result.prompt_latency_seconds:.3f} s"
        )
        print(
            f"{'':20}Generation latency: "
            f"{result.generation_latency_seconds:.3f} s"
        )
        print(
            f"{'':20}Generation speed: "
            f"{result.generation_tokens_per_second:.2f} tok/s"
        )
        print(
            f"{'':20}Model load time: "
            f"{result.model_load_seconds:.3f} s"
        )
        print()

        if result.status == EvaluationStatus.PASS:
            passed += 1
        elif result.status == EvaluationStatus.FAIL:
            failed += 1
        else:
            errors += 1

    print("=============================")
    print(f"Passed : {passed}")
    print(f"Failed : {failed}")
    print(f"Errors : {errors}")
    print(f"Total  : {len(results)}")

    return passed, failed, errors


def main() -> int:
    args = parse_args()

    test_cases = load_prompt_tests(args.prompts)

    # client = OllamaClient(model=args.model)
    # runner = TestRunner(client, evaluate_response)
    #
    # results = runner.run_tests(test_cases)
    runner = MultiModelRunner(
        model_names=args.models,
        evaluator=evaluate_response,
    )

    results = runner.run_tests(test_cases)

    json_reporter = JsonReporter(args.report)
    json_reporter.write(results)

    html_reporter = HtmlReporter(
        Path("results/latest_report.html")
    )
    html_reporter.write(results)

    _, failed, errors = print_results(results)

    print(f"\nJSON report: {args.report}")
    print("HTML report: results/latest_report.html")


    return 0 if failed == 0 and errors == 0 else 1
if __name__ == "__main__":
    raise SystemExit(main())