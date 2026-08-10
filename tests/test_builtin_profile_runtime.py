from __future__ import annotations

import pytest

from src.evaluation_models import VerdictPolicy
from src.evaluation_pipeline import EvaluationPipeline
from src.evaluation_config import create_pipeline_from_profile
from src.evaluation_config.loader import load_evaluation_profile
from src.evaluation_config.errors import (
    EvaluationConfigValidationError,
)


@pytest.mark.parametrize(
    "profile_name",
    [
        "fast-ci",
        "default",
        "enterprise",
    ],
)
def test_supported_builtin_profile_builds_runtime_pipeline(
    profile_name: str,
) -> None:
    profile = load_evaluation_profile(profile_name)

    pipeline = create_pipeline_from_profile(profile)

    assert isinstance(pipeline, EvaluationPipeline)


def test_fast_ci_builds_assertion_only_runtime() -> None:
    profile = load_evaluation_profile("fast-ci")

    pipeline = create_pipeline_from_profile(profile)

    assert pipeline.external_engines == ()
    assert pipeline.default_metrics == ()
    assert pipeline.default_threshold == pytest.approx(0.70)
    assert pipeline.verdict_policy is VerdictPolicy.ALL_METRICS


def test_default_does_not_activate_disabled_deepeval() -> None:
    profile = load_evaluation_profile("default")

    pipeline = create_pipeline_from_profile(profile)

    assert pipeline.external_engines == ()
    assert pipeline.default_metrics == ()
    assert pipeline.default_threshold == pytest.approx(0.70)


def test_enterprise_activates_deepeval() -> None:
    profile = load_evaluation_profile("enterprise")

    pipeline = create_pipeline_from_profile(profile)

    assert len(pipeline.external_engines) == 1
    assert pipeline.external_engines[0].name == "deepeval"


def test_enterprise_preserves_metric_configuration() -> None:
    profile = load_evaluation_profile("enterprise")

    pipeline = create_pipeline_from_profile(profile)

    assert pipeline.default_metrics == (
        "answer_relevancy",
        "faithfulness",
    )
    assert pipeline.default_threshold == pytest.approx(0.90)
    assert pipeline.verdict_policy is VerdictPolicy.ALL_METRICS


def test_deep_quality_rejects_multiple_runtime_thresholds() -> None:
    profile = load_evaluation_profile("deep-quality")

    with pytest.raises(
        ValueError,
        match="supports one shared metric threshold",
    ):
        create_pipeline_from_profile(profile)


def test_rag_rejects_unsupported_runtime_engine() -> None:
    profile = load_evaluation_profile("rag")

    with pytest.raises(
        EvaluationConfigValidationError,
        match="Unsupported evaluation engine",
    ):
        create_pipeline_from_profile(profile)