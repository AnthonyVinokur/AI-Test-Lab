from __future__ import annotations

from pathlib import Path

from src.candidate_evaluation_run_provenance import (
    construct_candidate_evaluation_run_provenance,
)
from src.evaluation_run_identity import EvaluationRunIdentity
from src.evaluation_run_regression_orchestrator import (
    EvaluationRunRegressionOrchestrator,
)
from src.stored_baseline_regression_result_acquirer import (
    StoredBaselineRegressionResultAcquirer,
)
from src.stored_evaluation_run_provenance_loader import (
    load_stored_evaluation_run_provenance,
)


def assemble_evaluation_run_regression_runtime(
    *,
    baseline_report_path: str | Path,
    baseline_provenance_path: str | Path,
    candidate_identity: EvaluationRunIdentity,
    candidate_dataset_version: str,
    report_schema_version: str,
) -> EvaluationRunRegressionOrchestrator:
    """Assemble the runtime dependencies for evaluation-run regression."""

    baseline_provenance = load_stored_evaluation_run_provenance(
        baseline_provenance_path
    )

    baseline_acquirer = StoredBaselineRegressionResultAcquirer(
        report_path=baseline_report_path,
        provenance=baseline_provenance,
    )

    candidate_provenance = (
        construct_candidate_evaluation_run_provenance(
            identity=candidate_identity,
            dataset_version=candidate_dataset_version,
            report_schema_version=report_schema_version,
        )
    )

    return EvaluationRunRegressionOrchestrator(
        baseline_acquirer=baseline_acquirer,
        candidate_provenance=candidate_provenance,
    )
