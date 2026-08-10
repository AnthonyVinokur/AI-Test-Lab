from src.evaluation_models import MetricResult, VerdictPolicy
from src.evaluation_pipeline import EvaluationPipeline
from src.models import (
    Assertion,
    AssertionType,
    EvaluationStatus,
    ModelResponse,
    PromptTest,
)
from src.runner import TestRunner as RuntimeTestRunner
from src.evaluation_config import (
    EngineConfig,
    EvaluationProfile,
    QualityGateConfig,
    create_pipeline_from_profile,
)


class FakeModelClient:
    """Deterministic model client for runtime integration tests."""

    def __init__(self, response: str) -> None:
        self.response = response

    def generate(self, prompt: str) -> ModelResponse:
        return ModelResponse(
            provider="fake",
            model="fake-model",
            content=self.response,
        )


class FailingExternalEngine:
    """External engine that deterministically fails its metric."""

    @property
    def name(self) -> str:
        return "fake-external"

    def evaluate(self, request):
        return [
            MetricResult(
                engine=self.name,
                metric_name=request.metrics[0],
                score=0.4,
                threshold=request.threshold,
                passed=False,
                reason="Semantic quality threshold was not met.",
            )
        ]


def make_test_case() -> PromptTest:
    return PromptTest(
        id="profile-runtime-001",
        name="Profile runtime integration",
        category="integration",
        prompt="Explain Python.",
        assertion=Assertion(
            type=AssertionType.CONTAINS,
            expected="programming",
        ),
    )


def test_assertion_only_pipeline_passes_runtime_evaluation() -> None:
    pipeline = EvaluationPipeline(
        verdict_policy=VerdictPolicy.ASSERTION_ONLY,
    )

    runner = RuntimeTestRunner(
        client=FakeModelClient(
            "Python is a programming language."
        ),
        evaluation_pipeline=pipeline,
    )

    result = runner.run_test(make_test_case())

    assert result.status is EvaluationStatus.PASS
    assert result.passed is True
    assert len(result.evaluation_results) == 1
    assert result.evaluation_results[0].engine == "builtin"


def test_quality_gate_can_change_runtime_verdict() -> None:
    pipeline = EvaluationPipeline(
        external_engines=[
            FailingExternalEngine(),
        ],
        verdict_policy=VerdictPolicy.ALL_METRICS,
        default_metrics=("answer_relevancy",),
        default_threshold=0.7,
    )

    runner = RuntimeTestRunner(
        client=FakeModelClient(
            "Python is a programming language."
        ),
        evaluation_pipeline=pipeline,
    )

    result = runner.run_test(make_test_case())

    assert result.status is EvaluationStatus.FAIL
    assert result.passed is False

    assert len(result.evaluation_results) == 2

    builtin_result = result.evaluation_results[0]
    external_result = result.evaluation_results[1]

    assert builtin_result.engine == "builtin"
    assert builtin_result.passed is True

    assert external_result.engine == "fake-external"
    assert external_result.metric_name == "answer_relevancy"
    assert external_result.score == 0.4
    assert external_result.threshold == 0.7
    assert external_result.passed is False


def test_profile_defaults_reach_external_evaluation_request() -> None:
    captured_requests = []

    class CapturingExternalEngine:
        @property
        def name(self) -> str:
            return "capturing-engine"

        def evaluate(self, request):
            captured_requests.append(request)

            return [
                MetricResult(
                    engine=self.name,
                    metric_name=request.metrics[0],
                    score=0.9,
                    threshold=request.threshold,
                    passed=True,
                    reason="Metric passed.",
                )
            ]

    pipeline = EvaluationPipeline(
        external_engines=[
            CapturingExternalEngine(),
        ],
        verdict_policy=VerdictPolicy.ALL_METRICS,
        default_metrics=("answer_relevancy",),
        default_threshold=0.82,
    )

    runner = RuntimeTestRunner(
        client=FakeModelClient(
            "Python is a programming language."
        ),
        evaluation_pipeline=pipeline,
    )

    result = runner.run_test(make_test_case())

    assert result.status is EvaluationStatus.PASS
    assert len(captured_requests) == 1

    request = captured_requests[0]

    assert request.input == "Explain Python."
    assert request.actual_output == (
        "Python is a programming language."
    )
    assert request.metrics == ("answer_relevancy",)
    assert request.threshold == 0.82

def test_profile_configuration_reaches_runtime() -> None:
    profile = EvaluationProfile(
        name="runtime-assertion-only",
        engines=[
            EngineConfig(
                name="assertion",
                enabled=True,
            )
        ],
        quality_gate=QualityGateConfig(
            enabled=False,
        ),
    )

    pipeline = create_pipeline_from_profile(profile)

    runner = RuntimeTestRunner(
        client=FakeModelClient(
            "Python is a programming language."
        ),
        evaluation_pipeline=pipeline,
    )

    result = runner.run_test(make_test_case())

    assert pipeline.verdict_policy is VerdictPolicy.ASSERTION_ONLY
    assert pipeline.external_engines == ()
    assert pipeline.default_metrics == ()

    assert result.status is EvaluationStatus.PASS
    assert result.passed is True
    assert len(result.evaluation_results) == 1
    assert result.evaluation_results[0].engine == "builtin"