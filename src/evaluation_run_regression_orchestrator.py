from __future__ import annotations

from dataclasses import dataclass

from src.baseline_regression_result_acquirer import (
    BaselineRegressionResultAcquirer,
)
from src.candidate_regression_result_adapter import (
    adapt_candidate_regression_results,
)
from src.evaluation_run_provenance import EvaluationRunProvenance
from src.evaluation_run_regression_comparison import (
    EvaluationRunRegressionComparison,
    compare_evaluation_runs_for_regression,
)
from src.models import TestResult


@dataclass(frozen=True)
class EvaluationRunRegressionOrchestrator:
    """Prepare and compare one baseline and candidate evaluation run."""

    baseline_acquirer: BaselineRegressionResultAcquirer
    candidate_provenance: EvaluationRunProvenance

    def __post_init__(self) -> None:
        if not isinstance(
            self.candidate_provenance,
            EvaluationRunProvenance,
        ):
            raise TypeError(
                "candidate_provenance must be an "
                "EvaluationRunProvenance"
            )

    def compare(
        self,
        candidate_results: list[TestResult],
    ) -> EvaluationRunRegressionComparison:
        baseline = self.baseline_acquirer.acquire()
        adapted_candidate_results = (
            adapt_candidate_regression_results(candidate_results)
        )

        return compare_evaluation_runs_for_regression(
            baseline=baseline.provenance,
            candidate=self.candidate_provenance,
            baseline_results=baseline.case_results,
            candidate_results=adapted_candidate_results,
        )
