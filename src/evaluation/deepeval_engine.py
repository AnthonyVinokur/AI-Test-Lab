from __future__ import annotations

from collections.abc import Callable
from typing import Any

from src.evaluation_engines import EvaluationEngine
from src.evaluation_models import EvaluationRequest, MetricResult


class DeepEvalEngine(EvaluationEngine):
    """Evaluation engine backed by DeepEval metrics."""

    ENGINE_NAME = "deepeval"

    SUPPORTED_METRICS = frozenset(
        {
            "answer_relevancy",
            "faithfulness",
        }
    )

    def __init__(
        self,
        *,
        judge_model: str | Any | None = None,
        metric_factory: Callable[..., Any] | None = None,
    ) -> None:
        """
        Create a DeepEval evaluation engine.

        Args:
            judge_model:
                DeepEval judge model name or a DeepEvalBaseLLM instance.
                When omitted, DeepEval uses its configured default model.

            metric_factory:
                Optional dependency-injection hook used by unit tests.
        """
        self._judge_model = judge_model
        self._metric_factory = metric_factory

    @property
    def name(self) -> str:
        """Return the engine identifier."""
        return self.ENGINE_NAME

    def is_available(self) -> bool:
        """Return True when DeepEval can be imported."""
        try:
            import deepeval  # noqa: F401
        except ImportError:
            return False

        return True

    def evaluate(
        self,
        request: EvaluationRequest,
    ) -> list[MetricResult]:
        """
        Evaluate one model response using configured DeepEval metrics.

        Args:
            request:
                Normalized evaluation request containing the prompt,
                response, selected metrics, threshold, and optional
                retrieval context.

        Returns:
            One normalized result for every requested metric.

        Raises:
            RuntimeError:
                If DeepEval is unavailable, metric execution fails, or a
                metric does not return a score.

            ValueError:
                If a metric is unsupported, required data is missing, or
                DeepEval returns an invalid score.
        """
        if not self.is_available() and self._metric_factory is None:
            raise RuntimeError(
                "DeepEval is not installed. "
                'Install it with: pip install -e ".[deepeval]"'
            )

        test_case = self._create_test_case(request)
        results: list[MetricResult] = []

        for requested_metric_name in request.metrics:
            metric_name = self._normalize_metric_name(
                requested_metric_name
            )

            self._validate_metric_requirements(
                metric_name=metric_name,
                request=request,
            )

            metric = self._create_metric(
                metric_name=metric_name,
                threshold=request.threshold,
            )

            self._measure_metric(
                metric=metric,
                metric_name=metric_name,
                test_case=test_case,
            )

            score = self._normalize_score(
                getattr(metric, "score", None)
            )

            passed = self._resolve_passed(
                metric=metric,
                score=score,
                threshold=request.threshold,
            )

            results.append(
                MetricResult(
                    metric_name=metric_name,
                    score=score,
                    passed=passed,
                    threshold=request.threshold,
                    reason=getattr(metric, "reason", None),
                    engine=self.name,
                )
            )

        return results

    def _create_test_case(
        self,
        request: EvaluationRequest,
    ) -> Any:
        """
        Create a DeepEval test case.

        During unit tests, a dictionary is returned so DeepEval does not
        need to be imported or contacted.
        """
        if self._metric_factory is not None:
            return {
                "input": request.input,
                "actual_output": request.actual_output,
                "expected_output": request.expected_output,
                "retrieval_context": request.retrieval_context,
            }

        from deepeval.test_case import LLMTestCase

        kwargs: dict[str, Any] = {
            "input": request.input,
            "actual_output": request.actual_output,
        }

        if request.expected_output is not None:
            kwargs["expected_output"] = request.expected_output

        if request.retrieval_context:
            kwargs["retrieval_context"] = list(
                request.retrieval_context
            )

        return LLMTestCase(**kwargs)

    def _create_metric(
        self,
        *,
        metric_name: str,
        threshold: float,
    ) -> Any:
        """Create the configured DeepEval metric."""
        if self._metric_factory is not None:
            return self._metric_factory(
                metric_name=metric_name,
                threshold=threshold,
                model=self._judge_model,
            )

        from deepeval.metrics import (
            AnswerRelevancyMetric,
            FaithfulnessMetric,
        )

        common_options: dict[str, Any] = {
            "threshold": threshold,
            "include_reason": True,
            "async_mode": False,
        }

        if self._judge_model is not None:
            common_options["model"] = self._judge_model

        metric_classes: dict[str, type[Any]] = {
            "answer_relevancy": AnswerRelevancyMetric,
            "faithfulness": FaithfulnessMetric,
        }

        metric_class = metric_classes[metric_name]

        return metric_class(**common_options)

    @classmethod
    def _normalize_metric_name(
        cls,
        metric_name: str,
    ) -> str:
        """
        Normalize and validate a requested metric name.

        Names are case-insensitive, and surrounding whitespace is
        ignored.
        """
        normalized_name = metric_name.strip().lower()

        if normalized_name not in cls.SUPPORTED_METRICS:
            supported = ", ".join(
                sorted(cls.SUPPORTED_METRICS)
            )

            raise ValueError(
                f"Unsupported DeepEval metric: {metric_name!r}. "
                f"Supported metrics: {supported}."
            )

        return normalized_name

    @staticmethod
    def _validate_metric_requirements(
        *,
        metric_name: str,
        request: EvaluationRequest,
    ) -> None:
        """Validate data required by the selected metric."""
        if (
            metric_name == "faithfulness"
            and not request.retrieval_context
        ):
            raise ValueError(
                "DeepEval metric 'faithfulness' requires "
                "retrieval_context."
            )

    @staticmethod
    def _measure_metric(
        *,
        metric: Any,
        metric_name: str,
        test_case: Any,
    ) -> None:
        """Run one metric and translate its exception if it fails."""
        try:
            metric.measure(test_case)
        except Exception as exc:
            raise RuntimeError(
                f"DeepEval metric '{metric_name}' failed: {exc}"
            ) from exc

    @staticmethod
    def _normalize_score(score: Any) -> float:
        """Convert a DeepEval score into a validated float."""
        if score is None:
            raise RuntimeError(
                "DeepEval completed without returning a metric score."
            )

        try:
            normalized_score = float(score)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                "DeepEval returned a non-numeric metric score: "
                f"{score!r}"
            ) from exc

        if not 0.0 <= normalized_score <= 1.0:
            raise ValueError(
                "DeepEval returned an invalid score outside the "
                f"0.0–1.0 range: {normalized_score}"
            )

        return normalized_score

    @staticmethod
    def _resolve_passed(
        *,
        metric: Any,
        score: float,
        threshold: float,
    ) -> bool:
        """
        Resolve pass/fail using DeepEval's verdict when available.

        Falls back to comparing the normalized score against the
        configured threshold.
        """
        is_successful = getattr(
            metric,
            "is_successful",
            None,
        )

        if callable(is_successful):
            result = is_successful()

            if result is not None:
                return bool(result)

        return score >= threshold