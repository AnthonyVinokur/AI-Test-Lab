from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from src.evaluation_run_provenance import EvaluationRunProvenance
from src.evaluation_run_regression_comparison import (
    EvaluationRunCaseResult,
)


@dataclass(frozen=True)
class AcquiredBaselineRegressionResult:
    """Baseline inputs acquired for regression comparison."""

    provenance: EvaluationRunProvenance
    case_results: tuple[EvaluationRunCaseResult, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.provenance, EvaluationRunProvenance):
            raise TypeError(
                "provenance must be an EvaluationRunProvenance"
            )

        if not isinstance(self.case_results, tuple):
            raise TypeError("case_results must be a tuple")

        for result in self.case_results:
            if not isinstance(result, EvaluationRunCaseResult):
                raise TypeError(
                    "case_results must contain "
                    "EvaluationRunCaseResult objects"
                )


class BaselineRegressionResultAcquirer(Protocol):
    """Acquire one previously identified baseline regression run."""

    def acquire(self) -> AcquiredBaselineRegressionResult:
        ...
