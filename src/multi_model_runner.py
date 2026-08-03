
from src.evaluation_engines import EvaluationEngine
from src.models import PromptTest, TestResult
from src.ollama_client import OllamaClient
from src.runner import TestRunner


class MultiModelRunner:
    """Runs the same test suite against multiple Ollama models."""

    def __init__(
        self,
        model_names: list[str],
        evaluation_engine: EvaluationEngine,
    ) -> None:
        if not model_names:
            raise ValueError("At least one model name is required.")

        self._model_names = model_names
        self._evaluation_engine = evaluation_engine

    def run_tests(
        self,
        test_cases: list[PromptTest],
    ) -> list[TestResult]:
        all_results: list[TestResult] = []

        for model_name in self._model_names:
            client = OllamaClient(model=model_name)

            runner = TestRunner(
                client=client,
                evaluation_engine=self._evaluation_engine,
            )

            all_results.extend(runner.run_tests(test_cases))

        return all_results