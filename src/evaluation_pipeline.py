from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol

from src.evaluation_engines import AssertionEvaluationEngine
from src.evaluation_models import EvaluationRequest, MetricResult
from src.models import Assertion, EvaluationResult


class ExternalEvaluationEngine(Protocol):
    """Interface required from semantic evaluation engines."""

    @property
    def name(self) -> str:
        ...

    def evaluate(
        self,
        request: EvaluationRequest,
    ) -> list[MetricResult]:
        ...


class EvaluationPipeline:
    def __init__(
        self,
        *,
        assertion_engine: AssertionEvaluationEngine | None = None,
        external_engines: Iterable[ExternalEvaluationEngine] | None = None,
    ) -> None:
        self.assertion_engine = (
            assertion_engine or AssertionEvaluationEngine()
        )
        self.external_engines = tuple(external_engines or ())

    def evaluate(
        self,
        *,
        prompt: str,
        actual_response: str,
        assertion: Assertion,
        metrics: tuple[str, ...] = (),
        threshold: float = 0.7,
        expected_output: str | None = None,
        retrieval_context: tuple[str, ...] = (),

    ) -> EvaluationResult:

        """
        Evaluate a response using assertions and optional external metrics.
        """
        assertion_result = self.assertion_engine.evaluate(
            actual_response=actual_response,
            assertion=assertion,
        )

        metric_results = list(assertion_result.evaluation_results)

        if metrics:
            request = EvaluationRequest(
                input=prompt,
                actual_output=actual_response,
                metrics=metrics,
                threshold=threshold,
                expected_output=expected_output,
                retrieval_context=retrieval_context,
            )

            metric_results.extend(
                self._evaluate_external_engines(request)
            )

        return EvaluationResult(
            passed=assertion_result.passed,
            status=assertion_result.status,
            assertion_type=assertion_result.assertion_type,
            expected=assertion_result.expected,
            reason=assertion_result.reason,
            evaluation_results=metric_results,
        )

    def _evaluate_external_engines(
            self,
            request: EvaluationRequest,
    ) -> list[MetricResult]:
        """Run every configured external evaluation engine."""
        results: list[MetricResult] = []

        for engine in self.external_engines:
            results.extend(engine.evaluate(request))

        return results