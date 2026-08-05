from abc import ABC, abstractmethod

from src.evaluator import evaluate_response
from src.models import Assertion, EvaluationResult
from src.evaluation_models import MetricResult


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
        evaluation = evaluate_response(
            actual_response=actual_response,
            assertion=assertion,
        )

        return EvaluationResult(
            passed=evaluation.passed,
            status=evaluation.status,
            assertion_type=evaluation.assertion_type,
            expected=evaluation.expected,
            reason=evaluation.reason,
            evaluation_results=[
                MetricResult(
                    engine=self.name,
                    metric_name=assertion.type.value,
                    score=1.0 if evaluation.passed else 0.0,
                    threshold=1.0,
                    passed=evaluation.passed,
                    reason=evaluation.reason,
                )
            ],
        )
