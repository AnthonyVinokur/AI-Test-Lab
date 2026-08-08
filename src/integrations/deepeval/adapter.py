from __future__ import annotations

from collections.abc import Callable
from typing import Any

from src.evaluation_models import EvaluationRequest, MetricResult
from src.integrations.deepeval.exceptions import (
    DeepEvalDependencyError,
    DeepEvalExecutionError,
)
from src.integrations.deepeval.metrics import create_metric


MetricCreator = Callable[..., Any]


class DeepEvalEngine:
    """External evaluation engine backed by the DeepEval SDK."""

    def __init__(
        self,
        *,
        model: str | None = None,
        include_reason: bool = True,
        metric_creator: MetricCreator = create_metric,
    ) -> None:
        self.model = model
        self.include_reason = include_reason
        self._metric_creator = metric_creator

    @property
    def name(self) -> str:
        """Return the registry name used by AI Test Lab."""

        return "deepeval"

    def evaluate(
        self,
        request: EvaluationRequest,
    ) -> list[MetricResult]:
        """Run requested DeepEval metrics and normalize their results."""

        test_case = self._create_test_case(request)
        results: list[MetricResult] = []

        for metric_name in request.metrics:
            results.append(
                self._evaluate_metric(
                    metric_name=metric_name,
                    request=request,
                    test_case=test_case,
                )
            )

        return results

    def _create_test_case(
        self,
        request: EvaluationRequest,
    ) -> Any:
        """Convert an AI Test Lab request into a DeepEval test case."""

        try:
            from deepeval.test_case import LLMTestCase
        except ImportError as exc:
            raise DeepEvalDependencyError(
                "DeepEval is not installed. "
                "Install it with: pip install deepeval"
            ) from exc

        retrieval_context = (
            list(request.retrieval_context)
            if request.retrieval_context
            else None
        )

        return LLMTestCase(
            input=request.input,
            actual_output=request.actual_output,
            expected_output=request.expected_output,
            retrieval_context=retrieval_context,
            context=retrieval_context,
        )

    def _evaluate_metric(
        self,
        *,
        metric_name: str,
        request: EvaluationRequest,
        test_case: Any,
    ) -> MetricResult:
        """Execute one DeepEval metric."""

        try:
            metric = self._metric_creator(
                metric_name,
                threshold=request.threshold,
                model=self.model,
                include_reason=self.include_reason,
            )

            metric.measure(test_case)

            score = self._normalize_score(
                metric_name=metric_name,
                score=getattr(metric, "score", None),
            )

            passed = self._resolve_passed(
                metric_name=metric_name,
                metric=metric,
                score=score,
                threshold=request.threshold,
            )

            reason = getattr(metric, "reason", None)

            return MetricResult(
                metric_name=metric_name.strip().lower(),
                score=score,
                passed=passed,
                threshold=request.threshold,
                engine=self.name,
                reason=reason,
            )

        except (
            DeepEvalDependencyError,
            DeepEvalExecutionError,
        ):
            raise
        except Exception as exc:
            raise DeepEvalExecutionError(
                f"DeepEval metric '{metric_name}' failed: {exc}"
            ) from exc

    @staticmethod
    def _normalize_score(
        *,
        metric_name: str,
        score: object,
    ) -> float:
        """Validate and normalize a DeepEval score."""

        if score is None:
            raise DeepEvalExecutionError(
                f"DeepEval metric '{metric_name}' did not return a score."
            )

        try:
            normalized_score = float(score)
        except (TypeError, ValueError) as exc:
            raise DeepEvalExecutionError(
                f"DeepEval metric '{metric_name}' returned "
                f"an invalid score: {score!r}."
            ) from exc

        if not 0.0 <= normalized_score <= 1.0:
            raise DeepEvalExecutionError(
                f"DeepEval metric '{metric_name}' returned "
                f"an out-of-range score: {normalized_score}."
            )

        return normalized_score

    @staticmethod
    def _resolve_passed(
        *,
        metric_name: str,
        metric: Any,
        score: float,
        threshold: float,
    ) -> bool:
        """Resolve the DeepEval metric verdict."""

        is_successful = getattr(metric, "is_successful", None)

        if callable(is_successful):
            verdict = is_successful()

            if verdict is not None:
                return bool(verdict)

        # Defensive fallback for test doubles or unusual custom metrics.
        return score >= threshold