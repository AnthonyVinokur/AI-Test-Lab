from src.evaluation_engines import AssertionEvaluationEngine
from src.models import (
    Assertion,
    AssertionType,
    EvaluationStatus,
    PromptTest,
)
from src.runner import TestRunner as Runner
from tests.fakes import FakeModelClient


def test_runner_executes_prompt_and_returns_test_result() -> None:
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

    runner = Runner(
        client=client,
        evaluation_engine=AssertionEvaluationEngine(),
    )

    result = runner.run_test(test_case)

    assert result.test_id == "FUNC-001"
    assert result.status == EvaluationStatus.PASS
    assert result.passed is True

    assert result.provider == "fake"
    assert result.model == "fake-model"
    assert (
        result.actual_response
        == "Python is a programming language."
    )

    assert len(result.evaluation_results) == 1

    metric_result = result.evaluation_results[0]

    assert metric_result.engine == "builtin"
    assert metric_result.metric_name == "contains"
    assert metric_result.passed is True
    assert metric_result.score == 1.0