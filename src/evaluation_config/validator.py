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