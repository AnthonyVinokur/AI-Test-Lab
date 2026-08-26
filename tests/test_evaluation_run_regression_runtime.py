from __future__ import annotations

import json

import pytest

from src.evaluation_run_identity import EvaluationRunIdentity
from src.evaluation_run_regression_orchestrator import (
    EvaluationRunRegressionOrchestrator,
)
from src.evaluation_run_regression_runtime import (
    assemble_evaluation_run_regression_runtime,
)
from src.stored_baseline_regression_result_acquirer import (
    StoredBaselineRegressionResultAcquirer,
)
from src.stored_evaluation_run_provenance_loader import (
    StoredEvaluationRunProvenanceLoadError,
)


def _candidate_identity() -> EvaluationRunIdentity:
    return EvaluationRunIdentity(
        run_id="run-candidate-001",
        model="llama3.1:latest",
        evaluation_profile="fast-ci",
        dataset="regression-suite",
    )


def _write_baseline_provenance(tmp_path):
    provenance_path = tmp_path / "baseline.provenance.json"

    provenance_path.write_text(
        json.dumps(
            {
                "run_id": "run-baseline-001",
                "model": "llama3.1:latest",
                "evaluation_profile": "fast-ci",
                "dataset": "regression-suite",
                "dataset_version": "1",
                "report_contract": "evaluation-report",
                "report_contract_fingerprint": "baseline-fingerprint",
            }
        ),
        encoding="utf-8",
    )

    return provenance_path


def test_assembles_regression_orchestrator_from_runtime_inputs(
    tmp_path,
) -> None:
    provenance_path = _write_baseline_provenance(tmp_path)
    report_path = tmp_path / "baseline.json"

    runtime = assemble_evaluation_run_regression_runtime(
        baseline_report_path=report_path,
        baseline_provenance_path=provenance_path,
        candidate_identity=_candidate_identity(),
        candidate_dataset_version="2",
        report_schema_version="1.0",
    )

    assert isinstance(runtime, EvaluationRunRegressionOrchestrator)
    assert isinstance(
        runtime.baseline_acquirer,
        StoredBaselineRegressionResultAcquirer,
    )


def test_wires_baseline_report_path_into_acquirer(tmp_path) -> None:
    provenance_path = _write_baseline_provenance(tmp_path)
    report_path = tmp_path / "baseline.json"

    runtime = assemble_evaluation_run_regression_runtime(
        baseline_report_path=report_path,
        baseline_provenance_path=provenance_path,
        candidate_identity=_candidate_identity(),
        candidate_dataset_version="2",
        report_schema_version="1.0",
    )

    assert runtime.baseline_acquirer.report_path == report_path


def test_loads_baseline_provenance_from_supplied_path(tmp_path) -> None:
    provenance_path = _write_baseline_provenance(tmp_path)

    runtime = assemble_evaluation_run_regression_runtime(
        baseline_report_path=tmp_path / "baseline.json",
        baseline_provenance_path=provenance_path,
        candidate_identity=_candidate_identity(),
        candidate_dataset_version="2",
        report_schema_version="1.0",
    )

    assert runtime.baseline_acquirer.provenance.run_id == "run-baseline-001"
    assert runtime.baseline_acquirer.provenance.dataset_version == "1"


def test_constructs_candidate_provenance_from_runtime_inputs(
    tmp_path,
) -> None:
    provenance_path = _write_baseline_provenance(tmp_path)
    identity = _candidate_identity()

    runtime = assemble_evaluation_run_regression_runtime(
        baseline_report_path=tmp_path / "baseline.json",
        baseline_provenance_path=provenance_path,
        candidate_identity=identity,
        candidate_dataset_version="7",
        report_schema_version="1.0",
    )

    candidate = runtime.candidate_provenance

    assert candidate.run_id == identity.run_id
    assert candidate.model == identity.model
    assert candidate.evaluation_profile == identity.evaluation_profile
    assert candidate.dataset == identity.dataset
    assert candidate.dataset_version == "7"


def test_assembly_does_not_load_baseline_report(tmp_path) -> None:
    provenance_path = _write_baseline_provenance(tmp_path)

    missing_report = tmp_path / "does-not-exist.json"

    runtime = assemble_evaluation_run_regression_runtime(
        baseline_report_path=missing_report,
        baseline_provenance_path=provenance_path,
        candidate_identity=_candidate_identity(),
        candidate_dataset_version="2",
        report_schema_version="1.0",
    )

    assert runtime.baseline_acquirer.report_path == missing_report


def test_rejects_invalid_baseline_provenance(tmp_path) -> None:
    provenance_path = tmp_path / "invalid.provenance.json"
    provenance_path.write_text("not-json", encoding="utf-8")

    with pytest.raises(StoredEvaluationRunProvenanceLoadError):
        assemble_evaluation_run_regression_runtime(
            baseline_report_path=tmp_path / "baseline.json",
            baseline_provenance_path=provenance_path,
            candidate_identity=_candidate_identity(),
            candidate_dataset_version="2",
            report_schema_version="1.0",
        )


def test_rejects_unsupported_candidate_report_schema_version(
    tmp_path,
) -> None:
    provenance_path = _write_baseline_provenance(tmp_path)

    with pytest.raises(
        ValueError,
        match="Unsupported public report schema version",
    ):
        assemble_evaluation_run_regression_runtime(
            baseline_report_path=tmp_path / "baseline.json",
            baseline_provenance_path=provenance_path,
            candidate_identity=_candidate_identity(),
            candidate_dataset_version="2",
            report_schema_version="999.0",
        )
