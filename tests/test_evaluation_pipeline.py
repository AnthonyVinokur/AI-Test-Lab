from src.evaluation_models import EvaluationRequest, MetricResult
from src.evaluation_pipeline import EvaluationPipeline
from src.models import Assertion, AssertionType


class FakeExternalEngine:
    @property
    def name(self) -> str:
        return "fake"

    def evaluate(self, request):
        return [
            MetricResult(
                engine=self.name,
                metric_name="answer_relevancy",
                score=0.9,
                threshold=request.threshold,
                passed=True,
                reason="The answer is relevant.",
            )
        ]


def test_pipeline_runs_builtin_assertion() -> None:
    pipeline = EvaluationPipeline()

    result = pipeline.evaluate(
        prompt="Say hello",
        actual_response="Hello there",
        assertion=Assertion(
            type=AssertionType.CONTAINS,
            expected="Hello",
        ),
    )

    assert result.passed is True
    assert len(result.evaluation_results) == 1

    metric = result.evaluation_results[0]

    assert metric.engine == "builtin"
    assert metric.score == 1.0
    assert metric.passed is True


def test_pipeline_combines_builtin_and_external_results() -> None:
    pipeline = EvaluationPipeline(
        external_engines=[FakeExternalEngine()],
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

    assert result.passed is True
    assert len(result.evaluation_results) == 2

    assert result.evaluation_results[0].engine == "builtin"
    assert result.evaluation_results[1].engine == "fake"
    assert result.evaluation_results[1].score == 0.9


def test_external_metric_does_not_replace_assertion_verdict() -> None:
    pipeline = EvaluationPipeline(
        external_engines=[FakeExternalEngine()],
    )

    result = pipeline.evaluate(
        prompt="Say orange",
        actual_response="Blue",
        assertion=Assertion(
            type=AssertionType.CONTAINS,
            expected="orange",
        ),
        metrics=("answer_relevancy",),
    )

    assert result.passed is False
    assert result.evaluation_results[0].passed is False
    assert result.evaluation_results[1].passed is True


def test_pipeline_skips_external_engines_without_metrics() -> None:
    pipeline = EvaluationPipeline(
        external_engines=[FakeExternalEngine()],
    )

    result = pipeline.evaluate(
        prompt="Say hello",
        actual_response="Hello",
        assertion=Assertion(
            type=AssertionType.CONTAINS,
            expected="Hello",
        ),
    )

    assert len(result.evaluation_results) == 1
    assert result.evaluation_results[0].engine == "builtin"

def test_pipeline_passes_per_metric_thresholds_to_external_engine() -> None:
    captured_requests: list[EvaluationRequest] = []

    class CapturingEngine:
        @property
        def name(self) -> str:
            return "fake"

        def evaluate(
            self,
            request: EvaluationRequest,
        ) -> list[MetricResult]:
            captured_requests.append(request)

            return [
                MetricResult(
                    engine=self.name,
                    metric_name="answer_relevancy",
                    score=0.9,
                    threshold=request.metric_thresholds[
                        "answer_relevancy"
                    ],
                    passed=True,
                    reason="Passed.",
                )
            ]

    pipeline = EvaluationPipeline(
        external_engines=[CapturingEngine()],
    )

    pipeline.evaluate(
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

    assert len(captured_requests) == 1

    captured_request = captured_requests[0]

    assert captured_request.threshold == 0.7
    assert captured_request.metric_thresholds == {
        "answer_relevancy": 0.85,
    }