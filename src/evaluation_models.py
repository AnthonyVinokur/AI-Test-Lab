from __future__ import annotations

from dataclasses import dataclass, field

from enum import StrEnum

class VerdictPolicy(StrEnum):
    """Controls how metric results affect the final evaluation verdict."""

    ASSERTION_ONLY = "assertion_only"
    ALL_METRICS = "all_metrics"

@dataclass(frozen=True, slots=True)
class EvaluationRequest:
    """Input required by an external evaluation engine."""

    input: str
    actual_output: str
    metrics: tuple[str, ...] = ("answer_relevancy",)
    threshold: float = 0.7
    metric_thresholds: dict[str, float] = field(
        default_factory=dict
    )
    expected_output: str | None = None
    retrieval_context: tuple[str, ...] = field(
        default_factory=tuple
    )


    def __post_init__(self) -> None:
        if not self.input.strip():
            raise ValueError("Evaluation input must not be empty.")

        if not self.actual_output.strip():
            raise ValueError("Actual output must not be empty.")

        if not self.metrics:
            raise ValueError(
                "At least one evaluation metric is required."
            )

        if not 0.0 <= self.threshold <= 1.0:
            raise ValueError(
                "Evaluation threshold must be between 0.0 and 1.0."
            )
        for metric_name, metric_threshold in self.metric_thresholds.items():
            if not metric_name.strip():
                raise ValueError(
                    "Metric threshold name must not be empty."
                )

            if not 0.0 <= metric_threshold <= 1.0:
                raise ValueError(
                    "Metric threshold must be between 0.0 and 1.0."
                )

@dataclass(frozen=True, slots=True)
class MetricResult:
    """Normalized result returned by an evaluation metric."""

    metric_name: str
    score: float
    passed: bool
    threshold: float
    engine: str
    reason: str | None = None