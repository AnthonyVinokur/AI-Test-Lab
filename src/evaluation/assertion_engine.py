from src.evaluation_engines import EvaluationEngine
from src.evaluator import evaluate_response
from src.models import Assertion, EvaluationResult


class AssertionEvaluationEngine(EvaluationEngine):
    """
    Built-in deterministic assertion evaluation engine.

    Supports assertion types such as:

    - contains
    - not_contains
    - equals
    - starts_with
    - ends_with
    - case-insensitive contains
    - regular expressions
    """

    @property
    def name(self) -> str:
        return "builtin"

    def evaluate(
        self,
        actual_response: str,
        assertion: Assertion,
    ) -> EvaluationResult:
        """
        Evaluate a model response against a deterministic assertion.

        Args:
            actual_response:
                Text returned by the model.

            assertion:
                Assertion configuration describing the expected behavior.

        Returns:
            The normalized AI Test Lab evaluation result.
        """
        return evaluate_response(
            actual_response=actual_response,
            assertion=assertion,
        )