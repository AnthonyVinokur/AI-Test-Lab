import pytest

from src.evaluation_config import (
    EngineConfig,
    EvaluationProfile,
    MetricConfig,
    QualityGateConfig,
    create_pipeline_from_profile,
)
from src.evaluation_models import VerdictPolicy


def test_assertion_only_profile_creates_default_pipeline():
    profile = EvaluationProfile(
        name="assertion-only",
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

    assert pipeline.external_engines == ()
    assert pipeline.default_metrics == ()
    assert pipeline.verdict_policy is VerdictPolicy.ASSERTION_ONLY


def test_deepeval_profile_adds_external_engine():
    profile = EvaluationProfile(
        name="deepeval-profile",
        engines=[
            EngineConfig(
                name="assertion",
                enabled=True,
            ),
            EngineConfig(
                name="deepeval",
                enabled=True,
                metrics=[
                    MetricConfig(
                        name="answer_relevancy",
                        threshold=0.7,
                    )
                ],
            ),
        ],
        quality_gate=QualityGateConfig(
            enabled=True,
            minimum_score=0.7,
        ),
    )

    pipeline = create_pipeline_from_profile(profile)

    assert len(pipeline.external_engines) == 1
    assert pipeline.external_engines[0].name == "deepeval"
    assert pipeline.default_metrics == ("answer_relevancy",)
    assert pipeline.default_threshold == 0.7


def test_rejects_unknown_enabled_engine():
    profile = EvaluationProfile(
        name="unknown-engine",
        engines=[
            EngineConfig(
                name="unknown",
                enabled=True,
            )
        ],
    )

    with pytest.raises(
        ValueError,
        match="Unsupported evaluation engine",
    ):
        create_pipeline_from_profile(profile)


def test_rejects_different_metric_thresholds():
    profile = EvaluationProfile(
        name="mixed-thresholds",
        engines=[
            EngineConfig(
                name="deepeval",
                enabled=True,
                metrics=[
                    MetricConfig(
                        name="answer_relevancy",
                        threshold=0.7,
                    ),
                    MetricConfig(
                        name="faithfulness",
                        threshold=0.8,
                    ),
                ],
            )
        ],
    )

    with pytest.raises(
        ValueError,
        match="one shared metric threshold",
    ):
        create_pipeline_from_profile(profile)