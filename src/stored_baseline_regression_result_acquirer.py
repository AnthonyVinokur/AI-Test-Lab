from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.baseline_regression_result_acquirer import (
    AcquiredBaselineRegressionResult,
)
from src.evaluation_run_provenance import EvaluationRunProvenance
from src.evaluation_run_regression_comparison import (
    EvaluationRunCaseResult,
)
from src.report_reader import load_report


@dataclass(frozen=True)
class StoredBaselineRegressionResultAcquirer:
    """Acquire baseline case outcomes from a stored public report."""

    report_path: str | Path
    provenance: EvaluationRunProvenance

    def __post_init__(self) -> None:
        if not isinstance(self.provenance, EvaluationRunProvenance):
            raise TypeError(
                "provenance must be an EvaluationRunProvenance"
            )

    def acquire(self) -> AcquiredBaselineRegressionResult:
        report = load_report(self.report_path)

        case_results = tuple(
            EvaluationRunCaseResult(
                case_id=result.test_id,
                passed=result.passed,
            )
            for result in report.results
        )

        return AcquiredBaselineRegressionResult(
            provenance=self.provenance,
            case_results=case_results,
        )
