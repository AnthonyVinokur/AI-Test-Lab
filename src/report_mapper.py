from __future__ import annotations

from typing import Any

from src.evaluation_models import EngineExecutionResult, MetricResult
from src.models import ModelSummary, TestResult

from src.report_schema import (
    ReportEngineExecutionResultV1,
    ReportMetricResultV1,
    ReportMetricRuntimeOptionsV1,
    ReportModelSummaryV1,
    ReportTestResultV1,
)

# Public report data is an explicit allow-list. Nested dictionaries must be
# filtered too; otherwise internal runtime options could bypass the DTO
# boundary even when the top-level schema rejects unknown fields.
PUBLIC_RUNTIME_OPTION_KEYS = frozenset(
    {
        "include_reason",
    }
)

PUBLIC_ENGINE_ERROR_MESSAGE = "Evaluation engine failed."


def map_runtime_options(
    runtime_options: dict[str, Any],
) -> ReportMetricRuntimeOptionsV1:
    return ReportMetricRuntimeOptionsV1(
        include_reason=runtime_options.get("include_reason"),
    )


def map_public_engine_error(error: str | None) -> str | None:
    """Normalize internal engine errors before they cross the public boundary."""
    if error is None:
        return None

    return PUBLIC_ENGINE_ERROR_MESSAGE


def map_metric_result(result: MetricResult) -> ReportMetricResultV1:
    return ReportMetricResultV1(
        engine=result.engine,
        metric_name=result.metric_name,
        score=result.score,
        threshold=result.threshold,
        passed=result.passed,
        reason=result.reason,
        runtime_options=map_runtime_options(result.runtime_options),
        profile_name=result.profile_name,
        profile_version=result.profile_version,
        evaluator_model=result.evaluator_model,
    )


def map_engine_result(
    result: EngineExecutionResult,
) -> ReportEngineExecutionResultV1:
    return ReportEngineExecutionResultV1(
        engine=result.engine,
        succeeded=result.succeeded,
        error=map_public_engine_error(result.error),
    )


def map_test_result(result: TestResult) -> ReportTestResultV1:
    return ReportTestResultV1(
        test_id=result.test_id,
        name=result.name,
        category=result.category,
        prompt=result.prompt,
        provider=result.provider,
        model=result.model,
        estimated_cost_usd=result.estimated_cost_usd,
        actual_response=result.actual_response,
        passed=result.passed,
        status=result.status.value,
        expected_to_fail=result.expected_to_fail,
        assertion_type=result.assertion_type.value,
        expected=result.expected,
        reason=result.reason,
        evaluation_results=[
            map_metric_result(metric_result)
            for metric_result in result.evaluation_results
        ],
        engine_results=[
            map_engine_result(engine_result)
            for engine_result in result.engine_results
        ],
        response_time_seconds=result.response_time_seconds,
        prompt_tokens=result.prompt_tokens,
        output_tokens=result.output_tokens,
        prompt_latency_seconds=result.prompt_latency_seconds,
        generation_latency_seconds=result.generation_latency_seconds,
        model_load_seconds=result.model_load_seconds,
        prompt_tokens_per_second=result.prompt_tokens_per_second,
        generation_tokens_per_second=result.generation_tokens_per_second,
    )


def map_model_summary(summary: ModelSummary) -> ReportModelSummaryV1:
    return ReportModelSummaryV1(
        provider=summary.provider,
        model=summary.model,
        total_estimated_cost_usd=summary.total_estimated_cost_usd,
        average_estimated_cost_usd=summary.average_estimated_cost_usd,
        passed=summary.passed,
        expected_failures=summary.expected_failures,
        unexpected_failures=summary.unexpected_failures,
        unexpected_passes=summary.unexpected_passes,
        errors=summary.errors,
        total=summary.total,
        pass_rate_percent=summary.pass_rate_percent,
        average_response_time_seconds=summary.average_response_time_seconds,
        average_prompt_latency_seconds=summary.average_prompt_latency_seconds,
        average_generation_latency_seconds=summary.average_generation_latency_seconds,
        average_model_load_seconds=summary.average_model_load_seconds,
        average_prompt_tokens=summary.average_prompt_tokens,
        average_output_tokens=summary.average_output_tokens,
        average_prompt_tokens_per_second=summary.average_prompt_tokens_per_second,
        average_generation_tokens_per_second=summary.average_generation_tokens_per_second,
    )
