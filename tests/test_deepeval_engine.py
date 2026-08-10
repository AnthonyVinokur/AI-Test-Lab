from __future__ import annotations

from typing import Any

import pytest

from src.evaluation.deepeval_engine import DeepEvalEngine

from src.evaluation_models import EvaluationRequest



class FakeDeepEvalMetric:
    """Controllable fake metric used by unit tests."""

    def __init__(
        self,
        *,
        score: Any = 0.9,
        reason: str | None = "Metric completed.",
        successful: bool | None = True,
        error: Exception | None = None,
    ) -> None:
        self.score = score
        self.reason = reason
        self._successful = successful
        self._error = error
        self.measured_test_case: Any | None = None

    def measure(self, test_case: Any) -> Any:
        self.measured_test_case = test_case

        if self._error is not None:
            raise self._error

        return self.score

    def is_successful(self) -> bool | None:
        return self._successful


def make_request(
    *,
    metrics: tuple[str, ...] = ("answer_relevancy",),
    threshold: float = 0.7,
    retrieval_context: tuple[str, ...] = (),
) -> EvaluationRequest:
    """Create a reusable evaluation request."""
    return EvaluationRequest(
        input="Who created Python?",
        actual_output=(
            "Python was created by Guido van Rossum."
        ),
        expected_output=(
            "Guido van Rossum created Python."
        ),
        retrieval_context=retrieval_context,
        metrics=metrics,
        threshold=threshold,
    )


def test_engine_name_is_deepeval() -> None:
    engine = DeepEvalEngine(
        metric_factory=lambda **_: FakeDeepEvalMetric()
    )

    assert engine.name == "deepeval"


def test_answer_relevancy_returns_real_metric_values() -> None:
    metric = FakeDeepEvalMetric(
        score=0.91,
        reason=(
            "The response directly answers the question."
        ),
        successful=True,
    )

    engine = DeepEvalEngine(
        metric_factory=lambda **_: metric
    )

    results = engine.evaluate(make_request())

    assert len(results) == 1

    result = results[0]

    assert result.metric_name == "answer_relevancy"
    assert result.score == pytest.approx(0.91)
    assert result.passed is True
    assert result.threshold == pytest.approx(0.7)
    assert result.reason == (
        "The response directly answers the question."
    )
    assert result.engine == "deepeval"


def test_test_case_contains_request_data() -> None:
    metric = FakeDeepEvalMetric()

    engine = DeepEvalEngine(
        metric_factory=lambda **_: metric
    )

    request = make_request(
        retrieval_context=(
            "Python was created by Guido van Rossum.",
        )
    )

    engine.evaluate(request)

    assert metric.measured_test_case == {
        "input": "Who created Python?",
        "actual_output": (
            "Python was created by Guido van Rossum."
        ),
        "expected_output": (
            "Guido van Rossum created Python."
        ),
        "retrieval_context": (
            "Python was created by Guido van Rossum.",
        ),
    }


def test_metric_factory_receives_configuration() -> None:
    received_arguments: dict[str, Any] = {}

    def metric_factory(**kwargs: Any) -> FakeDeepEvalMetric:
        received_arguments.update(kwargs)
        return FakeDeepEvalMetric()

    engine = DeepEvalEngine(
        judge_model="test-judge",
        metric_factory=metric_factory,
    )

    engine.evaluate(
        make_request(
            threshold=0.8,
        )
    )

    assert received_arguments == {
        "metric_name": "answer_relevancy",
        "threshold": 0.8,
        "model": "test-judge",
    }


def test_metric_name_is_normalized() -> None:
    received_names: list[str] = []

    def metric_factory(
        *,
        metric_name: str,
        **_: Any,
    ) -> FakeDeepEvalMetric:
        received_names.append(metric_name)
        return FakeDeepEvalMetric()

    engine = DeepEvalEngine(
        metric_factory=metric_factory
    )

    results = engine.evaluate(
        make_request(
            metrics=("  ANSWER_RELEVANCY  ",)
        )
    )

    assert received_names == ["answer_relevancy"]
    assert results[0].metric_name == "answer_relevancy"


def test_multiple_metrics_are_executed() -> None:
    created_metrics: list[str] = []

    def metric_factory(
        *,
        metric_name: str,
        **_: Any,
    ) -> FakeDeepEvalMetric:
        created_metrics.append(metric_name)

        return FakeDeepEvalMetric(
            score=0.9,
            reason=f"{metric_name} passed.",
            successful=True,
        )

    engine = DeepEvalEngine(
        metric_factory=metric_factory
    )

    results = engine.evaluate(
        make_request(
            metrics=(
                "answer_relevancy",
                "faithfulness",
            ),
            retrieval_context=(
                "Python was created by Guido van Rossum.",
            ),
        )
    )

    assert created_metrics == [
        "answer_relevancy",
        "faithfulness",
    ]

    assert [
        result.metric_name
        for result in results
    ] == [
        "answer_relevancy",
        "faithfulness",
    ]
def test_multiple_metrics_use_per_metric_thresholds() -> None:
    received_thresholds: dict[str, float] = {}

    def metric_factory(
        *,
        metric_name: str,
        threshold: float,
        **_: Any,
    ) -> FakeDeepEvalMetric:
        received_thresholds[metric_name] = threshold

        return FakeDeepEvalMetric(
            score=0.9,
            successful=None,
        )

    engine = DeepEvalEngine(
        metric_factory=metric_factory
    )

    request = EvaluationRequest(
        input="Who created Python?",
        actual_output="Python was created by Guido van Rossum.",
        metrics=(
            "answer_relevancy",
            "faithfulness",
        ),
        threshold=0.7,

        metric_thresholds={
            "answer_relevancy": 0.75,
            "faithfulness": 0.85,
        },
        retrieval_context=(
            "Python was created by Guido van Rossum.",
        ),
    )

    results = engine.evaluate(request)

    assert received_thresholds == {
        "answer_relevancy": 0.75,
        "faithfulness": 0.85,
    }

    assert results[0].threshold == pytest.approx(0.75)
    assert results[1].threshold == pytest.approx(0.85)



def test_faithfulness_requires_retrieval_context() -> None:
    engine = DeepEvalEngine(
        metric_factory=lambda **_: FakeDeepEvalMetric()
    )

    request = make_request(
        metrics=("faithfulness",),
        retrieval_context=(),
    )

    with pytest.raises(
        ValueError,
        match=(
            "faithfulness.*requires retrieval_context"
        ),
    ):
        engine.evaluate(request)


def test_faithfulness_accepts_retrieval_context() -> None:
    engine = DeepEvalEngine(
        metric_factory=lambda **_: FakeDeepEvalMetric(
            score=0.88,
            successful=True,
        )
    )

    results = engine.evaluate(
        make_request(
            metrics=("faithfulness",),
            retrieval_context=(
                "Python was created by Guido van Rossum.",
            ),
        )
    )

    assert results[0].metric_name == "faithfulness"
    assert results[0].score == pytest.approx(0.88)
    assert results[0].passed is True


def test_unsupported_metric_raises_value_error() -> None:
    engine = DeepEvalEngine(
        metric_factory=lambda **_: FakeDeepEvalMetric()
    )

    request = make_request(
        metrics=("imaginary_metric",)
    )

    with pytest.raises(
        ValueError,
        match="Unsupported DeepEval metric",
    ):
        engine.evaluate(request)


def test_measurement_exception_is_wrapped() -> None:
    metric = FakeDeepEvalMetric(
        error=ConnectionError(
            "judge model unavailable"
        )
    )

    engine = DeepEvalEngine(
        metric_factory=lambda **_: metric
    )

    with pytest.raises(
        RuntimeError,
        match=(
            "DeepEval metric 'answer_relevancy' failed"
        ),
    ) as exc_info:
        engine.evaluate(make_request())

    assert isinstance(
        exc_info.value.__cause__,
        ConnectionError,
    )


def test_missing_score_raises_runtime_error() -> None:
    engine = DeepEvalEngine(
        metric_factory=lambda **_: FakeDeepEvalMetric(
            score=None
        )
    )

    with pytest.raises(
        RuntimeError,
        match="without returning a metric score",
    ):
        engine.evaluate(make_request())


@pytest.mark.parametrize(
    "score",
    [
        "not-a-number",
        object(),
    ],
)
def test_non_numeric_score_raises_value_error(
    score: Any,
) -> None:
    engine = DeepEvalEngine(
        metric_factory=lambda **_: FakeDeepEvalMetric(
            score=score
        )
    )

    with pytest.raises(
        ValueError,
        match="non-numeric metric score",
    ):
        engine.evaluate(make_request())


@pytest.mark.parametrize(
    "score",
    [
        -0.01,
        1.01,
    ],
)
def test_out_of_range_score_raises_value_error(
    score: float,
) -> None:
    engine = DeepEvalEngine(
        metric_factory=lambda **_: FakeDeepEvalMetric(
            score=score
        )
    )

    with pytest.raises(
        ValueError,
        match="outside the 0.0–1.0 range",
    ):
        engine.evaluate(make_request())


def test_metric_success_verdict_is_used() -> None:
    engine = DeepEvalEngine(
        metric_factory=lambda **_: FakeDeepEvalMetric(
            score=0.9,
            successful=False,
        )
    )

    result = engine.evaluate(make_request())[0]

    assert result.score == pytest.approx(0.9)
    assert result.passed is False


def test_threshold_is_used_when_verdict_is_none() -> None:
    engine = DeepEvalEngine(
        metric_factory=lambda **_: FakeDeepEvalMetric(
            score=0.81,
            successful=None,
        )
    )

    result = engine.evaluate(
        make_request(
            threshold=0.8,
        )
    )[0]

    assert result.passed is True


def test_threshold_fallback_can_fail() -> None:
    engine = DeepEvalEngine(
        metric_factory=lambda **_: FakeDeepEvalMetric(
            score=0.79,
            successful=None,
        )
    )

    result = engine.evaluate(
        make_request(
            threshold=0.8,
        )
    )[0]

    assert result.passed is False


def test_deepeval_unavailable_raises_runtime_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = DeepEvalEngine()

    monkeypatch.setattr(
        engine,
        "is_available",
        lambda: False,
    )

    with pytest.raises(
        RuntimeError,
        match="DeepEval is not installed",
    ):
        engine.evaluate(make_request())

def test_metric_uses_shared_threshold_as_fallback() -> None:
    received_thresholds: list[float] = []

    def metric_factory(
        *,
        threshold: float,
        **_: Any,
    ) -> FakeDeepEvalMetric:
        received_thresholds.append(threshold)
        return FakeDeepEvalMetric()

    engine = DeepEvalEngine(
        metric_factory=metric_factory
    )

    engine.evaluate(
        make_request(
            threshold=0.82,
        )
    )

    assert received_thresholds == [0.82]