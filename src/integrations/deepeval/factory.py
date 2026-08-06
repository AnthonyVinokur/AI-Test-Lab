from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.integrations.deepeval.adapter import DeepEvalEngine


def create_deepeval_engine(
    config: Mapping[str, Any] | None = None,
) -> DeepEvalEngine:
    """
    Create a configured DeepEval evaluation engine.

    Parameters
    ----------
    config:
        Optional configuration dictionary.

    Supported configuration:

        model:
            Judge model used by DeepEval.

        include_reason:
            Include reasoning text in normalized metric results.
    """

    settings = dict(config or {})

    return DeepEvalEngine(
        model=settings.get("model"),
        include_reason=settings.get(
            "include_reason",
            True,
        ),
    )