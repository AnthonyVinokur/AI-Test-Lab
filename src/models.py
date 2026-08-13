
from enum import StrEnum


from pydantic import BaseModel, Field

from src.evaluation_models import EngineExecutionResult, MetricResult


class OllamaMetrics(BaseModel):
    prompt_tokens: int = Field(default=0, ge=0)
    response_tokens: int = Field(default=0, ge=0)

    prompt_latency_seconds: float = Field(default=0.0, ge=0.0)
    generation_latency_seconds: float = Field(default=0.0, ge=0.0)
    total_latency_seconds: float = Field(default=0.0, ge=0.0)
    model_load_seconds: float = Field(default=0.0, ge=0.0)

    prompt_tokens_per_second: float = Field(default=0.0, ge=0.0)
    generation_tokens_per_second: float = Field(default=0.0, ge=0.0)


class OllamaResponse(BaseModel):
    text: str
    model: str
    metrics: OllamaMetrics


class AssertionType(StrEnum):
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    EQUALS = "equals"
    ICONTAINS = "icontains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    REGEX = "regex"


class EvaluationStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    XFAIL = "XFAIL"
    XPASS = "XPASS"
    ERROR = "ERROR"


class Assertion(BaseModel):
    type: AssertionType
    expected: str = Field(min_length=1)


class PromptTest(BaseModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    category: str = Field(min_length=1)
    prompt: str = Field(min_length=1)
    assertion: Assertion
    expected_to_fail: bool = False
    xfail_reason: str | None = None


class ModelResponse(BaseModel):
    """Response returned by any supported LLM provider."""

    provider: str = Field(default="unknown", min_length=1)
    content: str
    model: str

    estimated_cost_usd: float = Field(default=0.0, ge=0.0)

    response_time_seconds: float = Field(default=0.0, ge=0.0)

    prompt_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)

    prompt_latency_seconds: float = Field(default=0.0, ge=0.0)
    generation_latency_seconds: float = Field(default=0.0, ge=0.0)
    model_load_seconds: float = Field(default=0.0, ge=0.0)

    prompt_tokens_per_second: float = Field(default=0.0, ge=0.0)
    generation_tokens_per_second: float = Field(default=0.0, ge=0.0)

class EvaluationResult(BaseModel):
    passed: bool
    status: EvaluationStatus
    assertion_type: AssertionType
    expected: str
    reason: str

    evaluation_results: list[MetricResult] = Field(
        default_factory=list
    )

    engine_results: list[EngineExecutionResult] = Field(
        default_factory=list
    )


class TestResult(BaseModel):
    test_id: str
    name: str
    category: str
    prompt: str

    provider: str = Field(default="unknown", min_length=1)
    model: str

    estimated_cost_usd: float = Field(default=0.0, ge=0.0)

    actual_response: str

    passed: bool
    status: EvaluationStatus

    expected_to_fail: bool = False

    assertion_type: AssertionType
    expected: str
    reason: str

    evaluation_results: list[MetricResult] = Field(
        default_factory=list
    )

    engine_results: list[EngineExecutionResult] = Field(
        default_factory=list
    )

    response_time_seconds: float = Field(default=0.0, ge=0.0)

    prompt_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)

    prompt_latency_seconds: float = Field(default=0.0, ge=0.0)
    generation_latency_seconds: float = Field(default=0.0, ge=0.0)
    model_load_seconds: float = Field(default=0.0, ge=0.0)

    prompt_tokens_per_second: float = Field(default=0.0, ge=0.0)
    generation_tokens_per_second: float = Field(default=0.0, ge=0.0)



class ModelSummary(BaseModel):
    """Aggregated evaluation and performance results for one model."""
    provider: str = Field(default="unknown", min_length=1)
    model: str

    total_estimated_cost_usd: float = Field(default=0.0, ge=0.0)
    average_estimated_cost_usd: float = Field(default=0.0, ge=0.0)
    passed: int = Field(default=0, ge=0)
    expected_failures: int = Field(default=0, ge=0)
    unexpected_failures: int = Field(default=0, ge=0)
    unexpected_passes: int = Field(default=0, ge=0)
    errors: int = Field(default=0, ge=0)
    total: int = Field(default=0, ge=0)



    pass_rate_percent: float = Field(default=0.0, ge=0.0, le=100.0)

    average_response_time_seconds: float = Field(default=0.0, ge=0.0)
    average_prompt_latency_seconds: float = Field(default=0.0, ge=0.0)
    average_generation_latency_seconds: float = Field(default=0.0, ge=0.0)
    average_model_load_seconds: float = Field(default=0.0, ge=0.0)

    average_prompt_tokens: float = Field(default=0.0, ge=0.0)
    average_output_tokens: float = Field(default=0.0, ge=0.0)

    average_prompt_tokens_per_second: float = Field(default=0.0, ge=0.0)
    average_generation_tokens_per_second: float = Field(
        default=0.0,
        ge=0.0,
    )