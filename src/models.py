
from enum import StrEnum

from pydantic import BaseModel, Field

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

# class AssertionType(StrEnum):
#     CONTAINS = "contains"
#     NOT_CONTAINS = "not_contains"
#     EQUALS = "equals"

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

class ModelResponse(BaseModel):
    """Response returned by any supported LLM provider."""

    content: str
    model: str

    response_time_seconds: float = Field(default=0.0, ge=0.0)

    prompt_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)

    prompt_latency_seconds: float = Field(
        default=0.0,
        ge=0.0,
    )
    generation_latency_seconds: float = Field(
        default=0.0,
        ge=0.0,
    )
    model_load_seconds: float = Field(
        default=0.0,
        ge=0.0,
    )

    prompt_tokens_per_second: float = Field(
        default=0.0,
        ge=0.0,
    )
    generation_tokens_per_second: float = Field(
        default=0.0,
        ge=0.0,
    )


class EvaluationResult(BaseModel):
    passed: bool
    status: EvaluationStatus
    assertion_type: AssertionType
    expected: str
    reason: str


class TestResult(BaseModel):
    test_id: str
    name: str
    category: str
    prompt: str

    model: str
    actual_response: str

    passed: bool
    status: EvaluationStatus

    assertion_type: AssertionType
    expected: str
    reason: str

    response_time_seconds: float = Field(default=0.0, ge=0.0)

    prompt_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)

    prompt_latency_seconds: float = Field(default=0.0, ge=0.0)
    generation_latency_seconds: float = Field(default=0.0, ge=0.0)
    model_load_seconds: float = Field(default=0.0, ge=0.0)

    prompt_tokens_per_second: float = Field(default=0.0, ge=0.0)
    generation_tokens_per_second: float = Field(default=0.0, ge=0.0)