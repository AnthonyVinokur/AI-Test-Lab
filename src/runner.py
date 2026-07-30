
from typing import Protocol
from collections.abc import Callable

from src.models import (
    Assertion,
    EvaluationResult,
    ModelResponse,
    PromptTest,
    TestResult, EvaluationStatus,
)


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
        model_response = self.client.generate(test_case.prompt)

        evaluation = self.evaluator(
            model_response.content,
            test_case.assertion,
                )
        status = evaluation.status
        reason = evaluation.reason

        if test_case.expected_to_fail:
            if evaluation.status == EvaluationStatus.FAIL:
                status = EvaluationStatus.XFAIL
                reason = f"Expected failure: {evaluation.reason}"

            elif evaluation.status == EvaluationStatus.PASS:
                status = EvaluationStatus.XPASS
                reason = (
                    "Unexpected pass: the test was marked as expected "
                    "to fail, but the assertion passed."
                )


        return TestResult(
            test_id=test_case.id,
            name=test_case.name,
            category=test_case.category,
            prompt=test_case.prompt,

            provider=model_response.provider,
            model=model_response.model,
            estimated_cost_usd=model_response.estimated_cost_usd,

            actual_response=model_response.content,
            status=status,
            expected_to_fail=test_case.expected_to_fail,
            passed=evaluation.passed,
            assertion_type=evaluation.assertion_type,
            expected=evaluation.expected,
            reason=reason,

            response_time_seconds=(
                model_response.response_time_seconds
            ),
            prompt_tokens=model_response.prompt_tokens,
            output_tokens=model_response.output_tokens,

            prompt_latency_seconds=(
                model_response.prompt_latency_seconds
            ),
            generation_latency_seconds=(
                model_response.generation_latency_seconds
            ),
            model_load_seconds=(
                model_response.model_load_seconds
            ),
            prompt_tokens_per_second=(
                model_response.prompt_tokens_per_second
            ),
            generation_tokens_per_second=(
                model_response.generation_tokens_per_second
            ),
        )