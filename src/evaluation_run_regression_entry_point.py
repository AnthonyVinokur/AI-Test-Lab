from __future__ import annotations

from pathlib import Path

from src.evaluation_run_case_regression_execution import (
    EvaluationRunCaseRegressionExecution,
    execute_evaluation_run_case_regression,
)
from src.evaluation_run_identity import EvaluationRunIdentity
from src.evaluation_run_regression_runtime import (
    assemble_evaluation_run_regression_runtime,
)
from src.models import TestResult


def execute_evaluation_run_regression(
    *,
    candidate_results: list[TestResult],
    baseline_report_path: str | Path,
    baseline_provenance_path: str | Path,
    candidate_identity: EvaluationRunIdentity,
    candidate_dataset_version: str,
    report_schema_version: str,
) -> EvaluationRunCaseRegressionExecution:
    """Execute evaluation-run regression from explicit runtime inputs."""

    orchestrator = assemble_evaluation_run_regression_runtime(
        baseline_report_path=baseline_report_path,
        baseline_provenance_path=baseline_provenance_path,
        candidate_identity=candidate_identity,
        candidate_dataset_version=candidate_dataset_version,
        report_schema_version=report_schema_version,
    )

    return execute_evaluation_run_case_regression(
        orchestrator,
        candidate_results,
    )
