from __future__ import annotations

from src.evaluation_models import (
    EvaluationRequest,
    MetricResult,
    VerdictPolicy,
)
from src.evaluation_pipeline import EvaluationPipeline
from src.models import Assertion, AssertionType


class PassingEngine:
    @property
    def name(self) -> str:
        return "passing"

    def evaluate(
        self,
        request: EvaluationRequest,
    ) -> list[MetricResult]:
        return [
            MetricResult(
                engine=self.name,
                metric_name="answer_relevancy",
                score=0.90,
                threshold=request.threshold,
                passed=True,
                reason="Passed.",
            )
        ]


class FailingMetricEngine:
    @property
    def name(self) -> str:
        return "failing-metric"

    def evaluate(
        self,
        request: EvaluationRequest,
    ) -> list[MetricResult]:
        return [
            MetricResult(
                engine=self.name,
                metric_name="answer_relevancy",
                score=0.40,
                threshold=request.threshold,
                passed=False,
                reason="Score below threshold.",
            )
        ]


class ErrorEngine:
    @property
    def name(self) -> str:
        return "error-engine"

    def evaluate(
        self,
        request: EvaluationRequest,
    ) -> list[MetricResult]:
        raise RuntimeError("judge unavailable")


def passing_assertion() -> Assertion:
    return Assertion(
        type=AssertionType.CONTAINS,
        expected="Python",
    )


def evaluate(
    pipeline: EvaluationPipeline,
):
    return pipeline.evaluate(
        prompt="What is Python?",
        actual_response="Python is a programming language.",
        assertion=passing_assertion(),
        metrics=("answer_relevancy",),
    )


def test_engine_error_fails_gate_when_policy_requires_it() -> None:
    pipeline = EvaluationPipeline(
        external_engines=[ErrorEngine()],
        verdict_policy=VerdictPolicy.ALL_METRICS,
        fail_on_engine_error=True,
    )

    result = evaluate(pipeline)

    assert result.passed is False
    assert "error-engine" in result.reason
    assert "judge unavailable" in result.reason


def test_engine_error_does_not_automatically_fail_when_policy_allows_it() -> None:
    pipeline = EvaluationPipeline(
        external_engines=[ErrorEngine()],
        verdict_policy=VerdictPolicy.ALL_METRICS,
        fail_on_engine_error=False,
        require_all_engines=False,
    )

    result = evaluate(pipeline)

    assert result.passed is True


def test_required_engine_failure_fails_even_when_engine_errors_are_tolerated() -> None:
    pipeline = EvaluationPipeline(
        external_engines=[
            PassingEngine(),
            ErrorEngine(),
        ],
        verdict_policy=VerdictPolicy.ALL_METRICS,
        fail_on_engine_error=False,
        require_all_engines=True,
    )

    result = evaluate(pipeline)

    assert result.passed is False
    assert "error-engine" in result.reason


def test_metric_failure_is_not_treated_as_engine_error() -> None:
    pipeline = EvaluationPipeline(
        external_engines=[FailingMetricEngine()],
        verdict_policy=VerdictPolicy.ALL_METRICS,
        fail_on_engine_error=False,
        require_all_engines=False,
    )

    result = evaluate(pipeline)

    assert result.passed is False
    assert "failing-metric:answer_relevancy" in result.reason


def test_gate_disabled_preserves_assertion_only_behavior_on_engine_error() -> None:
    pipeline = EvaluationPipeline(
        external_engines=[ErrorEngine()],
        verdict_policy=VerdictPolicy.ASSERTION_ONLY,
        fail_on_engine_error=True,
        require_all_engines=True,
    )

    result = evaluate(pipeline)

    assert result.passed is True


def test_all_engines_succeed_and_metrics_pass() -> None:
    pipeline = EvaluationPipeline(
        external_engines=[PassingEngine()],
        verdict_policy=VerdictPolicy.ALL_METRICS,
        fail_on_engine_error=True,
        require_all_engines=True,
    )

    result = evaluate(pipeline)

    assert result.passed is True