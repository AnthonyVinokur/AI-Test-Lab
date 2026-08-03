from unittest.mock import Mock

from src.models import (
    Assertion,
    AssertionType,
   # EvaluationResult,
    EvaluationStatus,
    ModelResponse,
    PromptTest,
)


from src.evaluation_engines import AssertionEvaluationEngine
from src.runner import TestRunner as Runner
from tests.fakes import FakeModelClient
from src.evaluation_engines import EvaluationEngine

class FakeEvaluationEngine(EvaluationEngine):
    @property
    def name(self) -> str:
        return "fake"

    # def evaluate(
    #     self,
    #     actual_response: str,
    #     assertion: Assertion,
    # ) -> EvaluationResult:
    #     return EvaluationResult(
    #         passed=True,
    #         status=EvaluationStatus.PASS,
    #         assertion_type=AssertionType.CONTAINS,
    #         expected=assertion.expected,
    #         reason="Fake evaluation passed.",
    #     )

def test_runner_executes_prompt_and_returns_test_result():
    client = FakeModelClient(
        response_text="Python is a programming language."
    )

    test_case = PromptTest(
        id="FUNC-001",
        name="Python response",
        category="functional",
        prompt="What is Python?",
        assertion=Assertion(
            type=AssertionType.CONTAINS,
            expected="Python",
        ),
    )

    evaluation_engine = AssertionEvaluationEngine()

    runner = Runner(
        client=client,
        evaluation_engine=evaluation_engine,
    )

    result = runner.run_test(test_case)

    assert result.test_id == "FUNC-001"
    assert result.status == EvaluationStatus.PASS
    assert result.passed is True
    assert result.model == "fake-model"
    assert result.actual_response == "Python is a programming language."
