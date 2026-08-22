from __future__ import annotations

from dataclasses import dataclass

from src.evaluation_run_provenance import EvaluationRunProvenance
from src.evaluation_run_reproducibility import (
    verify_evaluation_run_reproducibility,
)


@dataclass(frozen=True)
class EvaluationRunRegressionEligibility:
    eligible: bool
    mismatches: tuple[str, ...]


def determine_evaluation_run_regression_eligibility(
    baseline: EvaluationRunProvenance,
    candidate: EvaluationRunProvenance,
) -> EvaluationRunRegressionEligibility:
    reproducibility = verify_evaluation_run_reproducibility(
        baseline,
        candidate,
    )

    return EvaluationRunRegressionEligibility(
        eligible=reproducibility.reproducible,
        mismatches=reproducibility.mismatches,
    )