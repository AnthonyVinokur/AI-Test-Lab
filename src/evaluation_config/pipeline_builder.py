"""Build an EvaluationPipeline from a validated profile."""

from __future__ import annotations

from src.evaluation.deepeval_engine import DeepEvalEngine
from src.evaluation_config import EvaluationConfigValidationError
from src.evaluation_config.models import EvaluationProfile
from src.evaluation_models import VerdictPolicy
from src.evaluation_pipeline import EvaluationPipeline

from src.evaluation_config.validator import (
    validate_supported_metrics,
)
from src.integrations.deepeval.metrics import (
    supported_metric_names,
)
from src.evaluation_config.errors import (
    EvaluationConfigValidationError,
)


def create_pipeline_from_profile(
    profile: EvaluationProfile,
) -> EvaluationPipeline:
    """Construct a configured evaluation pipeline."""

    external_engines = []
    selected_metrics: list[str] = []
    metric_thresholds: list[float] = []

    for engine_config in profile.engines:
        if not engine_config.enabled:
            continue

        normalized_name = engine_config.name.strip().lower()

        # The assertion engine is built into EvaluationPipeline.
        if normalized_name in {"assertion", "builtin"}:
            continue

        if normalized_name == "deepeval":
            validate_supported_metrics(
                profile,
                {
                    "deepeval": supported_metric_names(),
                },
            )

            judge_model = engine_config.options.get("judge_model")

            external_engines.append(
                DeepEvalEngine(
                    judge_model=judge_model,
                )
            )

            for metric in engine_config.metrics:
                if not metric.enabled:
                    continue

                selected_metrics.append(metric.name)

                if metric.threshold is not None:
                    metric_thresholds.append(metric.threshold)

            continue

        raise EvaluationConfigValidationError(
            f"Unsupported evaluation engine in profile: "
            f"{engine_config.name!r}"
        )

    threshold = _resolve_threshold(
        profile=profile,
        metric_thresholds=metric_thresholds,
    )

    verdict_policy = _resolve_verdict_policy(profile)

    return EvaluationPipeline(
        external_engines=external_engines,
        verdict_policy=verdict_policy,
        default_metrics=tuple(selected_metrics),
        default_threshold=threshold,
    )


def _resolve_threshold(
    *,
    profile: EvaluationProfile,
    metric_thresholds: list[float],
) -> float:
    """Resolve one threshold for the current pipeline API."""

    if metric_thresholds:
        unique_thresholds = set(metric_thresholds)

        if len(unique_thresholds) > 1:
            raise ValueError(
                "The current evaluation pipeline supports one shared "
                "metric threshold per run. Configure all enabled metrics "
                "with the same threshold."
            )

        return metric_thresholds[0]

    return profile.quality_gate.minimum_score


def _resolve_verdict_policy(
    profile: EvaluationProfile,
) -> VerdictPolicy:
    """Map quality-gate configuration to the pipeline verdict policy."""

    if not profile.quality_gate.enabled:
        return VerdictPolicy.ASSERTION_ONLY

    return VerdictPolicy.ALL_METRICS