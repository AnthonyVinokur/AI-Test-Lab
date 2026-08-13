from __future__ import annotations

from collections.abc import Iterable
from dataclasses import replace
from typing import Any

from src.evaluation_plugins import ExternalEvaluationEngine
from src.evaluation_engines import AssertionEvaluationEngine

from src.evaluation_models import (
    EngineExecutionResult,
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
            fail_on_engine_error: bool = True,
            require_all_engines: bool = False,
            default_metrics: tuple[str, ...] = (),
            default_threshold: float = 0.7,
            default_metric_thresholds: dict[str, float] | None = None,
            default_metric_options: dict[str, dict[str, Any]] | None = None,
            profile_name: str | None = None,
            profile_version: str | None = None,
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

        self.fail_on_engine_error = fail_on_engine_error
        self.require_all_engines = require_all_engines

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
        self.profile_name = profile_name
        self.profile_version = profile_version
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
        metric_results = [
            self._attach_profile_provenance(metric)
            for metric in assertion_result.evaluation_results
        ]
        engine_results: list[EngineExecutionResult] = []
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
                profile_name=self.profile_name,
                profile_version=self.profile_version,
            )

            external_metric_results, engine_results = (
                self._evaluate_external_engines(request)
            )

            metric_results.extend(external_metric_results)

        passed, status, reason = self._resolve_verdict(
            assertion_result=assertion_result,
            metric_results=metric_results,
            engine_results=engine_results,
        )

        return EvaluationResult(
            passed=passed,
            status=status,
            assertion_type=assertion_result.assertion_type,
            expected=assertion_result.expected,
            reason=reason,
            evaluation_results=metric_results,
        )


    def _attach_profile_provenance(
        self,
        metric_result: MetricResult,
    ) -> MetricResult:
        """Attach selected profile identity without rebuilding unnecessarily."""
        if self.profile_name is None and self.profile_version is None:
            return metric_result

        if (
            metric_result.profile_name == self.profile_name
            and metric_result.profile_version == self.profile_version
        ):
            return metric_result

        return replace(
            metric_result,
            profile_name=(
                metric_result.profile_name or self.profile_name
            ),
            profile_version=(
                metric_result.profile_version or self.profile_version
            ),
        )

    def _evaluate_external_engines(
            self,
            request: EvaluationRequest,
    ) -> tuple[list[MetricResult], list[EngineExecutionResult]]:
        """Run configured external engines and capture execution outcomes."""

        metric_results: list[MetricResult] = []
        engine_results: list[EngineExecutionResult] = []

        for engine in self.external_engines:
            try:
                results = engine.evaluate(request)
            except Exception as exc:
                engine_results.append(
                    EngineExecutionResult(
                        engine=engine.name,
                        succeeded=False,
                        error=str(exc),
                    )
                )
                continue

            metric_results.extend(
                self._attach_profile_provenance(metric_result)
                for metric_result in results
            )

            engine_results.append(
                EngineExecutionResult(
                    engine=engine.name,
                    succeeded=True,
                )
            )

        return metric_results, engine_results

    def _resolve_verdict(
            self,
            *,
            assertion_result: EvaluationResult,
            metric_results: list[MetricResult],
            engine_results: list[EngineExecutionResult],
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

        if failed_external_metrics:
            failed_metric_names = ", ".join(
                f"{metric.engine}:{metric.metric_name}"
                for metric in failed_external_metrics
            )

            reason = (
                "Built-in assertion passed, but the evaluation quality gate "
                f"failed: {failed_metric_names}."
            )

            return False, EvaluationStatus.FAIL, reason

        failed_engines = [
            result
            for result in engine_results
            if not result.succeeded
        ]

        if failed_engines and (
                self.fail_on_engine_error
                or self.require_all_engines
        ):
            failed_engine_details = ", ".join(
                (
                    f"{result.engine}: {result.error}"
                    if result.error
                    else result.engine
                )
                for result in failed_engines
            )

            reason = (
                "Built-in assertion passed, but the evaluation quality gate "
                "failed because external engine execution failed: "
                f"{failed_engine_details}."
            )

            return False, EvaluationStatus.FAIL, reason

        return (
            True,
            assertion_result.status,
            assertion_result.reason,
        )