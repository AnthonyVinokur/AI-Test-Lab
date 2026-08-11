from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from src.evaluation_plugins import ExternalEvaluationEngine
from src.evaluation_engines import AssertionEvaluationEngine
from src.evaluation_models import (
    EvaluationRequest,
    MetricResult,
    VerdictPolicy,
)
from src.models import (
    Assertion,
    EvaluationResult,
    EvaluationStatus,
)


class EvaluationPipeline:
    """Runs deterministic and semantic evaluation engines."""

    def __init__(
            self,
            *,
            assertion_engine: AssertionEvaluationEngine | None = None,
            external_engines: Iterable[ExternalEvaluationEngine] | None = None,
            verdict_policy: VerdictPolicy = VerdictPolicy.ASSERTION_ONLY,
            default_metrics: tuple[str, ...] = (),
            default_threshold: float = 0.7,
            default_metric_thresholds: dict[str, float] | None = None,
            default_metric_options: dict[str, dict[str, Any]] | None = None,
    ) -> None:
        if not 0.0 <= default_threshold <= 1.0:
            raise ValueError(
                "Default evaluation threshold must be between 0.0 and 1.0."
            )

        self.assertion_engine = (
                assertion_engine or AssertionEvaluationEngine()
        )

        self.external_engines = tuple(external_engines or ())
        self.verdict_policy = verdict_policy
        self.default_metrics = default_metrics
        self.default_threshold = default_threshold

        self.default_metric_thresholds = dict(
            default_metric_thresholds or {}
        )

        self.default_metric_options = {
            metric_name: dict(options)
            for metric_name, options in (
                    default_metric_options or {}
            ).items()
        }
    def evaluate(
            self,
            *,
            prompt: str,
            actual_response: str,
            assertion: Assertion,
            metrics: tuple[str, ...] | None = None,
            threshold: float | None = None,
            metric_thresholds: dict[str, float] | None = None,
            metric_options: dict[str, dict[str, Any]] | None = None,
            expected_output: str | None = None,
            retrieval_context: tuple[str, ...] = (),
    ) -> EvaluationResult:

        """Evaluate one model response."""

        selected_metrics = (
            self.default_metrics
            if metrics is None
            else metrics
        )

        selected_threshold = (
            self.default_threshold
            if threshold is None
            else threshold
        )

        selected_metric_thresholds = (
            self.default_metric_thresholds
            if metric_thresholds is None
            else metric_thresholds
        )
        selected_metric_options = (
            self.default_metric_options
            if metric_options is None
            else metric_options
        )

        assertion_result = self.assertion_engine.evaluate(
            actual_response=actual_response,
            assertion=assertion,
        )
        metric_results = list(assertion_result.evaluation_results)

        if selected_metrics:
            request = EvaluationRequest(
                input=prompt,
                actual_output=actual_response,
                metrics=selected_metrics,
                threshold=selected_threshold,
                metric_thresholds=selected_metric_thresholds,
                metric_options=selected_metric_options,
                expected_output=expected_output,
                retrieval_context=retrieval_context,
            )

            metric_results.extend(
                self._evaluate_external_engines(request)
            )

        passed, status, reason = self._resolve_verdict(
            assertion_result=assertion_result,
            metric_results=metric_results,
        )

        return EvaluationResult(
            passed=passed,
            status=status,
            assertion_type=assertion_result.assertion_type,
            expected=assertion_result.expected,
            reason=reason,
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

    def _resolve_verdict(
        self,
        *,
        assertion_result: EvaluationResult,
        metric_results: list[MetricResult],
    ) -> tuple[bool, EvaluationStatus, str]:
        """Convert assertion and metric results into one final verdict."""

        if self.verdict_policy is VerdictPolicy.ASSERTION_ONLY:
            return (
                assertion_result.passed,
                assertion_result.status,
                assertion_result.reason,
            )

        if not assertion_result.passed:
            return (
                False,
                assertion_result.status,
                assertion_result.reason,
            )

        failed_external_metrics = [
            metric
            for metric in metric_results
            if metric.engine != self.assertion_engine.name
            and not metric.passed
        ]

        if not failed_external_metrics:
            return (
                True,
                assertion_result.status,
                assertion_result.reason,
            )

        failed_metric_names = ", ".join(
            f"{metric.engine}:{metric.metric_name}"
            for metric in failed_external_metrics
        )

        reason = (
            "Built-in assertion passed, but the evaluation quality gate "
            f"failed: {failed_metric_names}."
        )

        return False, EvaluationStatus.FAIL, reason