from src.evaluation_engines import EvaluationEngine
from src.models import EvaluationResult, EvaluationStatus


from __future__ import annotations

from src.evaluation_engines import EvaluationEngine
from src.models import (

    EvaluationStatus,
    ModelResponse,
    PromptTest,
)


class DeepEvalEngine(EvaluationEngine):
    """Placeholder adapter for the future DeepEval integration."""

    def evaluate(
        self,
        test: PromptTest,
        response: ModelResponse,
    ) -> EvaluationResult:
        """Return a placeholder passing result.

        The real DeepEval metrics will be integrated in a later sprint.
        """
        return EvaluationResult(
            passed=True,
            status=EvaluationStatus.PASS,
            assertion_type="deepeval",
            expected="N/A",
            reason="DeepEval placeholder",
        )