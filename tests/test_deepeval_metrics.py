from __future__ import annotations

from typing import Any

import pytest

from src.integrations.deepeval.exceptions import (
    UnsupportedDeepEvalMetricError,
)
from src.integrations.deepeval.metrics import (
    create_metric,
    supported_metric_names,
)


class FakeMetric:
    """Test double for DeepEval metric construction."""

    def __init__(
        self,
        *,
        threshold: float,
        include_reason: bool = True,
        model: str | None = None,
        **kwargs: Any,
    ) -> None:
        self.threshold = threshold
        self.include_reason = include_reason
        self.model = model
        self.kwargs = kwargs


@pytest.fixture
def fake_metric_classes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "src.integrations.deepeval.metrics._load_metric_classes",
        lambda: {
            "answer_relevancy": FakeMetric,
            "faithfulness": FakeMetric,
            "hallucination": FakeMetric,
        },
    )


def test_lists_supported_deepeval_metrics(
    fake_metric_classes: None,
) -> None:
    assert supported_metric_names() == (
        "answer_relevancy",
        "faithfulness",
        "hallucination",
    )


def test_creates_answer_relevancy_metric(
    fake_metric_classes: None,
) -> None:
    metric = create_metric(
        "answer_relevancy",
        threshold=0.8,
        include_reason=True,
    )

    assert metric.threshold == pytest.approx(0.8)
    assert metric.include_reason is True


def test_normalizes_metric_name(
    fake_metric_classes: None,
) -> None:
    metric = create_metric(
        "  ANSWER_RELEVANCY  ",
        threshold=0.7,
    )

    assert isinstance(metric, FakeMetric)
    assert metric.threshold == pytest.approx(0.7)


def test_passes_model_to_metric(
    fake_metric_classes: None,
) -> None:
    metric = create_metric(
        "answer_relevancy",
        threshold=0.8,
        model="test-model",
    )

    assert metric.model == "test-model"


def test_rejects_unsupported_metric(
    fake_metric_classes: None,
) -> None:
    with pytest.raises(
        UnsupportedDeepEvalMetricError,
        match="Unsupported DeepEval metric",
    ):
        create_metric(
            "unknown_metric",
            threshold=0.7,
        )