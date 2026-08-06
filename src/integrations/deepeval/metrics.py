from __future__ import annotations

from collections.abc import Callable
from typing import Any

from src.integrations.deepeval.exceptions import (
    DeepEvalDependencyError,
    UnsupportedDeepEvalMetricError,
)


MetricFactory = Callable[..., Any]


def _load_metric_classes() -> dict[str, MetricFactory]:
    """
    Import DeepEval metrics lazily.

    DeepEval remains an optional dependency because it is imported only when
    the integration is actually used.
    """

    try:
        from deepeval.metrics import (
            AnswerRelevancyMetric,
            FaithfulnessMetric,
            HallucinationMetric,
        )
    except ImportError as exc:
        raise DeepEvalDependencyError(
            "DeepEval is not installed. Install it with: pip install deepeval"
        ) from exc

    return {
        "answer_relevancy": AnswerRelevancyMetric,
        "faithfulness": FaithfulnessMetric,
        "hallucination": HallucinationMetric,
    }


def supported_metric_names() -> tuple[str, ...]:
    """Return the metric names supported by the DeepEval adapter."""

    return tuple(sorted(_load_metric_classes()))


def create_metric(
    metric_name: str,
    *,
    threshold: float,
    model: str | None = None,
    include_reason: bool = True,
) -> Any:
    """Create a configured DeepEval metric instance."""

    normalized_name = metric_name.strip().lower()

    metric_classes = _load_metric_classes()

    try:
        metric_class = metric_classes[normalized_name]
    except KeyError as exc:
        available = ", ".join(sorted(metric_classes))

        raise UnsupportedDeepEvalMetricError(
            f"Unsupported DeepEval metric '{normalized_name}'. "
            f"Available metrics: {available}."
        ) from exc

    options: dict[str, Any] = {
        "threshold": threshold,
        "include_reason": include_reason,
    }

    if model is not None:
        options["model"] = model

    return metric_class(**options)