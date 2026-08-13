"""Build an EvaluationPipeline from a validated profile."""

from __future__ import annotations

from typing import Any

from src.evaluation.deepeval_engine import DeepEvalEngine
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
    metric_thresholds: dict[str, float] = {}
    metric_options: dict[str, dict[str, Any]] = {}

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

                if metric.name is None:
                    raise EvaluationConfigValidationError(
                        "Enabled evaluation metric must have a name."
                    )
                metric_name = metric.name

                if metric.options:
                    metric_options[metric_name] = dict(metric.options)

                selected_metrics.append(metric_name)

                if metric.threshold is not None:
                    metric_thresholds[metric_name] = metric.threshold

            continue

        raise EvaluationConfigValidationError(
            f"Unsupported evaluation engine in profile: "
            f"{engine_config.name!r}"
        )

    verdict_policy = _resolve_verdict_policy(profile)

    return EvaluationPipeline(
        external_engines=external_engines,
        verdict_policy=verdict_policy,
        fail_on_engine_error=(
            profile.quality_gate.fail_on_engine_error
        ),
        require_all_engines=(
            profile.quality_gate.require_all_engines
        ),
        default_metrics=tuple(selected_metrics),
        default_threshold=profile.quality_gate.minimum_score,
        default_metric_thresholds=metric_thresholds,
        default_metric_options=metric_options,
        profile_name=profile.name,
        profile_version=profile.version,
    )


def _resolve_verdict_policy(
    profile: EvaluationProfile,
) -> VerdictPolicy:
    """Map quality-gate configuration to the pipeline verdict policy."""

    if not profile.quality_gate.enabled:
        return VerdictPolicy.ASSERTION_ONLY

    return VerdictPolicy.ALL_METRICS