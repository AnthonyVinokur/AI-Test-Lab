from collections.abc import Callable
from typing import Protocol
from time import perf_counter
from src.result_classifier import classify_status

from src.models import (
    Assertion,
    EvaluationResult,
    ModelResponse,
    PromptTest,
    TestResult, EvaluationStatus,
)
from src.result_classifier import classify_status


class ModelClient(Protocol):
    """Interface required from any LLM provider client."""

    def generate(self, prompt: str) -> ModelResponse:
        ...


Evaluator = Callable[[str, Assertion], EvaluationResult]


class TestRunner:
    """Coordinates model execution and response evaluation."""

    def __init__(
            self,
            client: ModelClient,
            evaluator: Evaluator,
    ) -> None:

        self.client = client
        self.evaluator = evaluator

    def run_tests(
            self,
            test_cases: list[PromptTest],
    ) -> list[TestResult]:
        return [
            self.run_test(test_case)
            for test_case in test_cases
        ]

    def run_test(self, test_case: PromptTest) -> TestResult:
        start_time = perf_counter()

        model_response = self.client.generate(test_case.prompt)

        response_time_seconds = perf_counter() - start_time

        evaluation = self.evaluator(
            model_response.content,
            test_case.assertion,
        )

        final_status = classify_status(
            prompt_test=test_case,
            assertion_passed=evaluation.passed,
        )

        reason = evaluation.reason

        return TestResult(
            test_id=test_case.id,
            name=test_case.name,
            category=test_case.category,
            prompt=test_case.prompt,
            model=model_response.model,
            actual_response=model_response.content,

            passed=final_status in {
                EvaluationStatus.PASS,
                EvaluationStatus.XFAIL,
            },
            status=final_status,
            expected_to_fail=test_case.expected_to_fail,

            assertion_type=evaluation.assertion_type,
            expected=evaluation.expected,
            reason=reason,

            response_time_seconds=response_time_seconds,

            prompt_tokens=model_response.prompt_tokens,
            output_tokens=model_response.output_tokens,
            prompt_latency_seconds=model_response.prompt_latency_seconds,
            generation_latency_seconds=model_response.generation_latency_seconds,
            model_load_seconds=model_response.model_load_seconds,
            prompt_tokens_per_second=model_response.prompt_tokens_per_second,
            generation_tokens_per_second=model_response.generation_tokens_per_second,
        )