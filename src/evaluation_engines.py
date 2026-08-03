from abc import ABC, abstractmethod

from src.evaluator import evaluate_response
from src.models import Assertion, EvaluationResult


class EvaluationEngine(ABC):
    """Base interface for all AI Test Lab evaluation engines."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the unique human-readable engine name."""

    # @abstractmethod
    # def evaluate(
    #     self,
    #     actual_response: str,
    #     assertion: Assertion,
    # ) -> EvaluationResult:
    #     """Evaluate a model response against a test assertion."""


class AssertionEvaluationEngine(EvaluationEngine):
    """
    Built-in deterministic evaluation engine.

    Supports AI Test Lab assertion types such as contains, equals,
    starts_with, ends_with, case-insensitive contains, and regex.
    """

    @property
    def name(self) -> str:
        return "builtin"

    def evaluate(
        self,
        actual_response: str,
        assertion: Assertion,
    ) -> EvaluationResult:
        return evaluate_response(
            actual_response=actual_response,
            assertion=assertion,
        )