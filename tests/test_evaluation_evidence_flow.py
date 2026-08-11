from src.evaluation_models import EvaluationRequest, MetricResult, VerdictPolicy
from src.evaluation_pipeline import EvaluationPipeline
from src.models import Assertion, AssertionType, EvaluationStatus


class EvidenceEngine:
    """Fake external engine that returns deterministic normalized evidence."""

    @property
    def name(self) -> str:
        return "evidence-engine"

    def evaluate(
        self,
        request: EvaluationRequest,
    ) -> list[MetricResult]:
        return [
            MetricResult(
                engine=self.name,
                metric_name="answer_relevancy",
                score=0.91,
                threshold=request.threshold_for("answer_relevancy"),
                passed=True,
                reason="The response directly answers the prompt.",
            )
        ]


class FailingEvidenceEngine:
    """Fake external engine used to verify failed evidence is preserved."""

    @property
    def name(self) -> str:
        return "evidence-engine"

    def evaluate(
        self,
        request: EvaluationRequest,
    ) -> list[MetricResult]:
        return [
            MetricResult(
                engine=self.name,
                metric_name="answer_relevancy",
                score=0.42,
                threshold=request.threshold_for("answer_relevancy"),
                passed=False,
                reason="The response is not sufficiently relevant.",
            )
        ]


def test_normalized_evidence_survives_pipeline_to_evaluation_result() -> None:
    pipeline = EvaluationPipeline(
        external_engines=[EvidenceEngine()],
    )

    result = pipeline.evaluate(
        prompt="Explain Python.",
        actual_response="Python is a programming language.",
        assertion=Assertion(
            type=AssertionType.CONTAINS,
            expected="programming",
        ),
        metrics=("answer_relevancy",),
        threshold=0.7,
        metric_thresholds={
            "answer_relevancy": 0.85,
        },
    )

    assert result.passed is True
    assert result.status is EvaluationStatus.PASS
    assert len(result.evaluation_results) == 2

    builtin_evidence = result.evaluation_results[0]
    external_evidence = result.evaluation_results[1]

    assert builtin_evidence.engine == "builtin"
    assert builtin_evidence.metric_name == "contains"
    assert builtin_evidence.score == 1.0
    assert builtin_evidence.threshold == 1.0
    assert builtin_evidence.passed is True
    assert builtin_evidence.reason == result.reason

    assert external_evidence.engine == "evidence-engine"
    assert external_evidence.metric_name == "answer_relevancy"
    assert external_evidence.score == 0.91
    assert external_evidence.threshold == 0.85
    assert external_evidence.passed is True
    assert external_evidence.reason == (
        "The response directly answers the prompt."
    )


def test_failed_external_evidence_survives_quality_gate_resolution() -> None:
    pipeline = EvaluationPipeline(
        external_engines=[FailingEvidenceEngine()],
        verdict_policy=VerdictPolicy.ALL_METRICS,
    )

    result = pipeline.evaluate(
        prompt="Explain Python.",
        actual_response="Python is a programming language.",
        assertion=Assertion(
            type=AssertionType.CONTAINS,
            expected="programming",
        ),
        metrics=("answer_relevancy",),
        threshold=0.7,
    )

    assert result.passed is False
    assert result.status is EvaluationStatus.FAIL
    assert len(result.evaluation_results) == 2

    external_evidence = result.evaluation_results[1]

    assert external_evidence.engine == "evidence-engine"
    assert external_evidence.metric_name == "answer_relevancy"
    assert external_evidence.score == 0.42
    assert external_evidence.threshold == 0.7
    assert external_evidence.passed is False
    assert external_evidence.reason == (
        "The response is not sufficiently relevant."
    )

    assert "evidence-engine:answer_relevancy" in result.reason


def test_pipeline_preserves_evidence_without_rebuilding_metric_results() -> None:
    produced_result = MetricResult(
        engine="evidence-engine",
        metric_name="answer_relevancy",
        score=0.88,
        threshold=0.8,
        passed=True,
        reason="Evidence object should pass through unchanged.",
    )

    class IdentityEvidenceEngine:
        @property
        def name(self) -> str:
            return "evidence-engine"

        def evaluate(
            self,
            request: EvaluationRequest,
        ) -> list[MetricResult]:
            return [produced_result]

    pipeline = EvaluationPipeline(
        external_engines=[IdentityEvidenceEngine()],
    )

    result = pipeline.evaluate(
        prompt="Explain Python.",
        actual_response="Python is a programming language.",
        assertion=Assertion(
            type=AssertionType.CONTAINS,
            expected="programming",
        ),
        metrics=("answer_relevancy",),
    )

    assert result.evaluation_results[1] is produced_result
