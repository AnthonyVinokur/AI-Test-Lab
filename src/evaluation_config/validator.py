"""Cross-check evaluation profiles against the plugin registry."""

from __future__ import annotations

from collections.abc import Iterable

from src.evaluation_config.errors import (
    EvaluationConfigValidationError,
)
from src.evaluation_config.models import EvaluationProfile


def validate_registered_engines(
    profile: EvaluationProfile,
    registered_engine_names: Iterable[str],
) -> None:
    """Ensure every enabled profile engine is registered."""

    registered = {
        engine_name.casefold()
        for engine_name in registered_engine_names
    }

    missing = sorted(
        engine.name
        for engine in profile.engines
        if engine.enabled
        and engine.name.casefold() not in registered
    )

    if missing:
        missing_text = ", ".join(missing)

        raise EvaluationConfigValidationError(
            "Evaluation profile references unregistered "
            f"engine(s): {missing_text}."
        )

def validate_supported_metrics(
    profile: EvaluationProfile,
    supported_metrics_by_engine: dict[str, Iterable[str]],
) -> None:
    """Ensure enabled profile metrics are supported by their engine."""

    normalized_supported = {
        engine_name.casefold(): {
            metric_name.casefold()
            for metric_name in metric_names
        }
        for engine_name, metric_names in supported_metrics_by_engine.items()
    }

    for engine in profile.engines:
        if not engine.enabled:
            continue

        supported = normalized_supported.get(
            engine.name.casefold()
        )

        if supported is None:
            continue

        unsupported = sorted(
            metric.name
            for metric in engine.metrics
            if metric.enabled
            and metric.name.casefold() not in supported
        )

        if unsupported:
            unsupported_text = ", ".join(unsupported)
            supported_text = ", ".join(sorted(supported))

            raise EvaluationConfigValidationError(
                f"Evaluation engine '{engine.name}' does not support "
                f"metric(s): {unsupported_text}. "
                f"Supported metrics: {supported_text}."
            )