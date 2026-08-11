from __future__ import annotations

from dataclasses import dataclass, field

from enum import StrEnum

from typing import Any

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
    metric_options: dict[str, dict[str, Any]] = field(
        default_factory=dict
    )
    expected_output: str | None = None
    retrieval_context: tuple[str, ...] = field(
        default_factory=tuple
    )
    profile_name: str | None = None
    profile_version: str | None = None


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

        for metric_name in self.metric_options:
            if not metric_name.strip():
                raise ValueError(
                    "Metric options name must not be empty."
                )

        normalized_metrics = {
            metric_name.strip().lower()
            for metric_name in self.metrics
        }

        unknown_threshold_metrics = {
            metric_name
            for metric_name in self.metric_thresholds
            if metric_name.strip().lower() not in normalized_metrics
        }
        if unknown_threshold_metrics:
            unknown = ", ".join(sorted(unknown_threshold_metrics))
            raise ValueError(
                "Metric threshold override configured for unselected "
                f"metric(s): {unknown}."
            )

        unknown_option_metrics = {
            metric_name
            for metric_name in self.metric_options
            if metric_name.strip().lower() not in normalized_metrics
        }
        if unknown_option_metrics:
            unknown = ", ".join(sorted(unknown_option_metrics))
            raise ValueError(
                "Metric runtime options configured for unselected "
                f"metric(s): {unknown}."
            )

    def threshold_for(self, metric_name: str) -> float:
        'Return the effective threshold for one selected metric.'
        normalized_name = metric_name.strip().lower()

        for configured_name, configured_threshold in (
            self.metric_thresholds.items()
        ):
            if configured_name.strip().lower() == normalized_name:
                return configured_threshold

        return self.threshold

    def options_for(self, metric_name: str) -> dict[str, Any]:
        'Return a defensive copy of runtime options for one metric.'
        normalized_name = metric_name.strip().lower()

        for configured_name, options in self.metric_options.items():
            if configured_name.strip().lower() == normalized_name:
                return dict(options)

        return {}

@dataclass(frozen=True, slots=True)
class MetricResult:
    """Normalized result returned by an evaluation metric."""

    metric_name: str
    score: float
    passed: bool
    threshold: float
    engine: str
    reason: str | None = None
    runtime_options: dict[str, Any] = field(default_factory=dict)
    profile_name: str | None = None
    profile_version: str | None = None
    evaluator_model: str | None = None

    def __post_init__(self) -> None:
        # Prevent callers from mutating the dictionary used to construct
        # this frozen provenance record after evaluation completes.
        object.__setattr__(
            self,
            "runtime_options",
            dict(self.runtime_options),
        )