from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from src.evaluation_models import EvaluationRequest
from src.integrations.deepeval.adapter import DeepEvalEngine
from src.integrations.deepeval.exceptions import DeepEvalExecutionError


@dataclass
class FakeMetric:
    score: object = 0.85
    reason: str | None = "The answer is relevant."
    successful: bool | None = True
    measured_test_case: Any = None

    def measure(self, test_case: Any) -> None:
        self.measured_test_case = test_case

    def is_successful(self) -> bool | None:
        return self.successful


def make_request(
    *,
    metrics: tuple[str, ...] = ("answer_relevancy",),
    threshold: float = 0.7,
    expected_output: str | None = None,
    retrieval_context: tuple[str, ...] = (),
) -> EvaluationRequest:
    return EvaluationRequest(
        input="What is Python?",
        actual_output="Python is a programming language.",
        metrics=metrics,
        threshold=threshold,
        expected_output=expected_output,
        retrieval_context=retrieval_context,
    )


def test_engine_name_is_deepeval() -> None:
    engine = DeepEvalEngine()

    assert engine.name == "deepeval"


def test_evaluates_and_normalizes_metric_result() -> None:
    fake_metric = FakeMetric()

    def metric_creator(
        metric_name: str,
        **options: object,
    ) -> FakeMetric:
        assert metric_name == "answer_relevancy"
        assert options["threshold"] == pytest.approx(0.7)
        assert options["include_reason"] is True
        assert options["model"] is None
        return fake_metric

    engine = DeepEvalEngine(metric_creator=metric_creator)

    results = engine.evaluate(make_request())

    assert len(results) == 1

    result = results[0]

    assert result.metric_name == "answer_relevancy"
    assert result.score == pytest.approx(0.85)
    assert result.passed is True
    assert result.threshold == pytest.approx(0.7)
    assert result.engine == "deepeval"
    assert result.reason == "The answer is relevant."


def test_creates_deepeval_test_case_from_request() -> None:
    fake_metric = FakeMetric()

    engine = DeepEvalEngine(
        metric_creator=lambda *args, **kwargs: fake_metric
    )

    engine.evaluate(
        make_request(
            expected_output="Python is a programming language.",
            retrieval_context=(
                "Python is widely used for software development.",
            ),
        )
    )

    test_case = fake_metric.measured_test_case

    assert test_case.input == "What is Python?"
    assert (
        test_case.actual_output
        == "Python is a programming language."
    )
    assert (
        test_case.expected_output
        == "Python is a programming language."
    )
    assert test_case.retrieval_context == [
        "Python is widely used for software development."
    ]
    assert test_case.context == [
        "Python is widely used for software development."
    ]


def test_evaluates_multiple_metrics() -> None:
    created_metric_names: list[str] = []

    def metric_creator(
        metric_name: str,
        **options: object,
    ) -> FakeMetric:
        created_metric_names.append(metric_name)

        return FakeMetric(
            score=0.9,
            reason=f"{metric_name} completed.",
            successful=True,
        )

    engine = DeepEvalEngine(metric_creator=metric_creator)

    results = engine.evaluate(
        make_request(
            metrics=(
                "answer_relevancy",
                "faithfulness",
            )
        )
    )

    assert created_metric_names == [
        "answer_relevancy",
        "faithfulness",
    ]
    assert [result.metric_name for result in results] == [
        "answer_relevancy",
        "faithfulness",
    ]


def test_uses_metric_success_verdict() -> None:
    metric = FakeMetric(
        score=0.95,
        successful=False,
    )

    engine = DeepEvalEngine(
        metric_creator=lambda *args, **kwargs: metric
    )

    result = engine.evaluate(make_request())[0]

    assert result.score == pytest.approx(0.95)
    assert result.passed is False


def test_falls_back_to_threshold_when_verdict_is_none() -> None:
    metric = FakeMetric(
        score=0.8,
        successful=None,
    )

    engine = DeepEvalEngine(
        metric_creator=lambda *args, **kwargs: metric
    )

    result = engine.evaluate(
        make_request(threshold=0.7)
    )[0]

    assert result.passed is True


def test_rejects_missing_metric_score() -> None:
    metric = FakeMetric(score=None)

    engine = DeepEvalEngine(
        metric_creator=lambda *args, **kwargs: metric
    )

    with pytest.raises(
        DeepEvalExecutionError,
        match="did not return a score",
    ):
        engine.evaluate(make_request())


def test_rejects_invalid_metric_score() -> None:
    metric = FakeMetric(score="invalid")

    engine = DeepEvalEngine(
        metric_creator=lambda *args, **kwargs: metric
    )

    with pytest.raises(
        DeepEvalExecutionError,
        match="invalid score",
    ):
        engine.evaluate(make_request())


def test_rejects_out_of_range_metric_score() -> None:
    metric = FakeMetric(score=1.5)

    engine = DeepEvalEngine(
        metric_creator=lambda *args, **kwargs: metric
    )

    with pytest.raises(
        DeepEvalExecutionError,
        match="out-of-range score",
    ):
        engine.evaluate(make_request())


def test_wraps_metric_execution_failure() -> None:
    class BrokenMetric(FakeMetric):
        def measure(self, test_case: Any) -> None:
            raise RuntimeError("Judge service unavailable.")

    engine = DeepEvalEngine(
        metric_creator=lambda *args, **kwargs: BrokenMetric()
    )

    with pytest.raises(
        DeepEvalExecutionError,
        match="Judge service unavailable",
    ):
        engine.evaluate(make_request())