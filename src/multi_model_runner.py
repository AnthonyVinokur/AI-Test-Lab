from collections.abc import Callable

from src.models import Assertion, EvaluationResult, PromptTest, TestResult
from src.ollama_client import OllamaClient
from src.runner import TestRunner


Evaluator = Callable[[str, Assertion], EvaluationResult]


class MultiModelRunner:
    """Runs the same prompt test suite against multiple Ollama models."""

    def __init__(
        self,
        model_names: list[str],
        evaluator: Evaluator,
    ) -> None:
        if not model_names:
            raise ValueError("At least one model name is required.")

        self._model_names = model_names
        self._evaluator = evaluator

    def run_tests(
        self,
        test_cases: list[PromptTest],
    ) -> list[TestResult]:
        all_results: list[TestResult] = []

        for model_name in self._model_names:
            client = OllamaClient(model=model_name)
            runner = TestRunner(
                client=client,
                evaluator=self._evaluator,
            )

            model_results = runner.run_tests(test_cases)
            all_results.extend(model_results)

        return all_results