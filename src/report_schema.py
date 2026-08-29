from __future__ import annotations

from typing import Literal

from pydantic import Field, BaseModel, ConfigDict

from src.public_contract import PublicContractModel


class PublicReportModel(PublicContractModel):
    """Base model for the public report contract."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class ReportMetricRuntimeOptionsV1(PublicReportModel):
    include_reason: bool | None = None


class ReportMetricResultV1(PublicReportModel):
    engine: str
    metric_name: str
    score: float
    threshold: float
    passed: bool
    reason: str | None = None
    runtime_options: ReportMetricRuntimeOptionsV1 = Field(
        default_factory=ReportMetricRuntimeOptionsV1
    )
    profile_name: str | None = None
    profile_version: str | None = None
    evaluator_model: str | None = None


class ReportEngineExecutionResultV1(PublicReportModel):
    engine: str
    succeeded: bool
    error: str | None = None


class ReportTestResultV1(PublicReportModel):
    test_id: str
    name: str
    category: str
    prompt: str
    provider: str
    model: str
    estimated_cost_usd: float = Field(ge=0.0)
    actual_response: str
    passed: bool
    status: str
    expected_to_fail: bool
    assertion_type: str
    expected: str
    reason: str
    evaluation_results: list[ReportMetricResultV1] = Field(default_factory=list)
    engine_results: list[ReportEngineExecutionResultV1] = Field(default_factory=list)
    response_time_seconds: float = Field(ge=0.0)
    prompt_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    prompt_latency_seconds: float = Field(ge=0.0)
    generation_latency_seconds: float = Field(ge=0.0)
    model_load_seconds: float = Field(ge=0.0)
    prompt_tokens_per_second: float = Field(ge=0.0)
    generation_tokens_per_second: float = Field(ge=0.0)


class ReportModelSummaryV1(PublicReportModel):
    provider: str
    model: str
    total_estimated_cost_usd: float = Field(ge=0.0)
    average_estimated_cost_usd: float = Field(ge=0.0)
    passed: int = Field(ge=0)
    expected_failures: int = Field(ge=0)
    unexpected_failures: int = Field(ge=0)
    unexpected_passes: int = Field(ge=0)
    errors: int = Field(ge=0)
    total: int = Field(ge=0)
    pass_rate_percent: float = Field(ge=0.0, le=100.0)
    average_response_time_seconds: float = Field(ge=0.0)
    average_prompt_latency_seconds: float = Field(ge=0.0)
    average_generation_latency_seconds: float = Field(ge=0.0)
    average_model_load_seconds: float = Field(ge=0.0)
    average_prompt_tokens: float = Field(ge=0.0)
    average_output_tokens: float = Field(ge=0.0)
    average_prompt_tokens_per_second: float = Field(ge=0.0)
    average_generation_tokens_per_second: float = Field(ge=0.0)


class ReportSummaryV1(PublicReportModel):
    passed: int = Field(ge=0)
    failed: int = Field(ge=0)
    expected_failures: int = Field(ge=0)
    unexpected_passes: int = Field(ge=0)
    errors: int = Field(ge=0)
    total: int = Field(ge=0)
    pass_rate_percent: float = Field(ge=0.0, le=100.0)
    total_estimated_cost_usd: float = Field(ge=0.0)


class ReportHighlightsV1(PublicReportModel):
    highest_scoring_model: str | None = None
    fastest_model: str | None = None


class ReportV1(PublicReportModel):
    schema_version: Literal["1.0"] = "1.0"
    generated_at: str
    models: list[str]
    summary: ReportSummaryV1
    highlights: ReportHighlightsV1
    model_comparison: list[ReportModelSummaryV1]
    results: list[ReportTestResultV1]
