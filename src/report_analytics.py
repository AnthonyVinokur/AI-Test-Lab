from collections import defaultdict
from collections.abc import Iterable

from src.models import EvaluationStatus, ModelSummary, TestResult


def build_model_summaries(
    results: list[TestResult],
) -> list[ModelSummary]:
    """Group test results by model and calculate summary metrics."""

    grouped_results: dict[str, list[TestResult]] = defaultdict(list)

    for result in results:
        grouped_results[result.model].append(result)

    summaries = [
        _build_single_model_summary(
            model=model,
            results=model_results,
        )
        for model, model_results in grouped_results.items()
    ]

    return sorted(
        summaries,
        key=lambda summary: (
            -summary.pass_rate_percent,
            summary.average_response_time_seconds,
            summary.model,
        ),
    )


def get_fastest_model(
    summaries: list[ModelSummary],
) -> ModelSummary | None:
    """Return the model with the lowest average response time."""

    if not summaries:
        return None

    return min(
        summaries,
        key=lambda summary: summary.average_response_time_seconds,
    )


def get_highest_scoring_model(
    summaries: list[ModelSummary],
) -> ModelSummary | None:
    """Return the model with the highest pass rate.

    Average response time is used as a tie-breaker.
    """

    if not summaries:
        return None

    return max(
        summaries,
        key=lambda summary: (
            summary.pass_rate_percent,
            -summary.average_response_time_seconds,
        ),
    )


def _build_single_model_summary(
    model: str,
    results: list[TestResult],
) -> ModelSummary:
    total = len(results)

    passed = sum(
        result.status == EvaluationStatus.PASS
        for result in results
    )
    failed = sum(
        result.status == EvaluationStatus.FAIL
        for result in results
    )
    errors = sum(
        result.status == EvaluationStatus.ERROR
        for result in results
    )

    pass_rate_percent = (
        passed / total * 100
        if total
        else 0.0
    )

    return ModelSummary(
        model=model,
        passed=passed,
        failed=failed,
        errors=errors,
        total=total,
        pass_rate_percent=round(pass_rate_percent, 2),
        average_response_time_seconds=_average(
            result.response_time_seconds
            for result in results
        ),
        average_prompt_latency_seconds=_average(
            result.prompt_latency_seconds
            for result in results
        ),
        average_generation_latency_seconds=_average(
            result.generation_latency_seconds
            for result in results
        ),
        average_model_load_seconds=_average(
            result.model_load_seconds
            for result in results
        ),
        average_prompt_tokens=_average(
            result.prompt_tokens
            for result in results
        ),
        average_output_tokens=_average(
            result.output_tokens
            for result in results
        ),
        average_prompt_tokens_per_second=_average(
            result.prompt_tokens_per_second
            for result in results
        ),
        average_generation_tokens_per_second=_average(
            result.generation_tokens_per_second
            for result in results
        ),

        provider=results[0].provider,
        total_estimated_cost_usd=round(
            sum(result.estimated_cost_usd for result in results),
            6,
        ),
        average_estimated_cost_usd=round(
            sum(result.estimated_cost_usd for result in results)
            / len(results),
            6,
        ),
    )


def _average(values: Iterable[int | float]) -> float:
    collected_values = list(values)

    if not collected_values:
        return 0.0

    return round(
        sum(collected_values) / len(collected_values),
        3,
    )