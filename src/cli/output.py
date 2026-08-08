from __future__ import annotations

from collections.abc import Sequence

from src.models import EvaluationStatus, TestResult


def print_evaluation_profiles(
    profile_names: Sequence[str],
) -> None:
    """Print available built-in evaluation profiles."""

    print("Available evaluation profiles:")

    for profile_name in profile_names:
        print(f"  {profile_name}")



def print_results(
    results: Sequence[TestResult],
) -> tuple[int, int, int, int]:
    """Print detailed results and return status counts."""

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

        match result.status:
            case EvaluationStatus.PASS:
                passed += 1
            case EvaluationStatus.XFAIL:
                expected_failures += 1
            case EvaluationStatus.FAIL:
                unexpected_failures += 1
            case EvaluationStatus.ERROR:
                errors += 1

    print("=============================")
    print(f"Passed              : {passed}")
    print(f"Expected failures   : {expected_failures}")
    print(f"Unexpected failures : {unexpected_failures}")
    print(f"Errors              : {errors}")
    print(f"Total               : {len(results)}")

    return (
        passed,
        expected_failures,
        unexpected_failures,
        errors,
    )