from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol, runtime_checkable

from src.evaluation_models import EvaluationRequest, MetricResult


@runtime_checkable
class ExternalEvaluationEngine(Protocol):
    """Contract implemented by external evaluation engine plugins."""

    @property
    def name(self) -> str:
        """Return the unique engine identifier."""
        ...

    def evaluate(
        self,
        request: EvaluationRequest,
    ) -> list[MetricResult]:
        """Evaluate one request and return normalized metric results."""
        ...


@runtime_checkable
class EvaluationEngineFactory(Protocol):
    """Factory used to construct an external evaluation engine."""

    def __call__(
        self,
        config: Mapping[str, Any] | None = None,
    ) -> ExternalEvaluationEngine:
        ...