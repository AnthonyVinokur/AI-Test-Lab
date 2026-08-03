from src.evaluation_engines import EvaluationEngine
from src.models import (
    Assertion,
    EvaluationResult,
    EvaluationStatus,
)


class DeepEvalEngine(EvaluationEngine):
    """Placeholder adapter for future DeepEval integration."""

    @property
    def name(self) -> str:
        return "deepeval"

    def evaluate(
        self,
        actual_response: str,
        assertion: Assertion,
    ) -> EvaluationResult:
        return EvaluationResult(
            passed=True,
            status=EvaluationStatus.PASS,
            assertion_type="deepeval",
            expected="N/A",
            reason="DeepEval placeholder",
        )