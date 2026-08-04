from abc import ABC, abstractmethod

from src.evaluator import evaluate_response
from src.models import Assertion, EvaluationResult


class EvaluationEngine(ABC):
    """Base interface for AI Test Lab evaluation engines."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the engine name."""
        raise NotImplementedError


class AssertionEvaluationEngine(EvaluationEngine):
    """Built-in deterministic assertion evaluation engine."""

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

