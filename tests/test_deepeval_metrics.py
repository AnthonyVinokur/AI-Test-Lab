from __future__ import annotations

import pytest

from src.integrations.deepeval.exceptions import (
    UnsupportedDeepEvalMetricError,
)
from src.integrations.deepeval.metrics import (
    create_metric,
    supported_metric_names,
)


def test_lists_supported_deepeval_metrics() -> None:
    assert supported_metric_names() == (
        "answer_relevancy",
        "faithfulness",
        "hallucination",
    )


def test_creates_answer_relevancy_metric() -> None:
    metric = create_metric(
        "answer_relevancy",
        threshold=0.8,
        include_reason=True,
    )

    assert metric.threshold == pytest.approx(0.8)
    assert metric.include_reason is True


def test_normalizes_metric_name() -> None:
    metric = create_metric(
        "  ANSWER_RELEVANCY  ",
        threshold=0.7,
    )

    assert metric is not None


def test_rejects_unsupported_metric() -> None:
    with pytest.raises(
        UnsupportedDeepEvalMetricError,
        match="Unsupported DeepEval metric",
    ):
        create_metric(
            "unknown_metric",
            threshold=0.7,
        )