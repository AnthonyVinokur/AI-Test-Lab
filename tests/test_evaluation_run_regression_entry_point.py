from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.evaluation_run_case_regression_gate import (
    EvaluationRunCaseRegressionGateDecision,
)
from src.evaluation_run_identity import EvaluationRunIdentity
from src.evaluation_run_regression_enforcement import (
    EvaluationRunRegressionEnforcementDecision,
)
from src.evaluation_run_regression_entry_point import (
    execute_evaluation_run_regression,
)
from src.models import TestResult as CandidateTestResult
from src.report_contract_fingerprint import (
    public_report_contract_fingerprint,
)
from src.report_contract_identity import (
    public_report_contract_identity,
)
from src.report_reader import ReportReadError
from src.stored_evaluation_run_provenance_loader import (
    StoredEvaluationRunProvenanceLoadError,
)

_FIXTURE_PATH = (
        Path(__file__).parent
        / "fixtures"
        / "report-v1.0.json"
)


def _candidate_identity() -> EvaluationRunIdentity:
    return EvaluationRunIdentity(
        run_id="run-candidate-001",
        model="llama3.1:latest",
        evaluation_profile="fast-ci",
        dataset="regression-suite",
    )


def _candidate_result(*, passed: bool) -> CandidateTestResult:
    return CandidateTestResult.model_construct(
        test_id="case-001",
        passed=passed,
    )


def _write_baseline_provenance(tmp_path):
    provenance_path = tmp_path / "baseline.provenance.json"

    contract = public_report_contract_identity("1.0")
    fingerprint = public_report_contract_fingerprint("1.0")

    provenance_path.write_text(
        json.dumps(
            {
                "run_id": "run-baseline-001",
                "model": "llama3.1:latest",
                "evaluation_profile": "fast-ci",
                "dataset": "regression-suite",
                "dataset_version": "2",
                "report_contract": contract.name,
                "report_contract_fingerprint": fingerprint,
            }
        ),
        encoding="utf-8",
    )

    return provenance_path


def _write_baseline_report(tmp_path, *, passed: bool):
    payload = json.loads(
        _FIXTURE_PATH.read_text(encoding="utf-8")
    )

    payload["results"][0]["test_id"] = "case-001"
    payload["results"][0]["passed"] = passed

    path = tmp_path / "baseline.json"
    path.write_text(
        json.dumps(payload),
        encoding="utf-8",
    )

    return path


def test_executes_regression_from_runtime_inputs(tmp_path) -> None:
    result = execute_evaluation_run_regression(
        candidate_results=[
            _candidate_result(passed=True),
        ],
        baseline_report_path=_write_baseline_report(
            tmp_path,
            passed=True,
        ),
        baseline_provenance_path=_write_baseline_provenance(
            tmp_path
        ),
        candidate_identity=_candidate_identity(),
        candidate_dataset_version="2",
        report_schema_version="1.0",
    )

    assert result.comparison.compared_count == 1
    assert result.comparison.regressed_count == 0
    assert (
            result.gate.decision
            is EvaluationRunCaseRegressionGateDecision.PASS
    )
    assert (
            result.enforcement.decision
            is EvaluationRunRegressionEnforcementDecision.ALLOW
    )


def test_executes_blocking_regression(tmp_path) -> None:
    result = execute_evaluation_run_regression(
        candidate_results=[
            _candidate_result(passed=False),
        ],
        baseline_report_path=_write_baseline_report(
            tmp_path,
            passed=True,
        ),
        baseline_provenance_path=_write_baseline_provenance(
            tmp_path
        ),
        candidate_identity=_candidate_identity(),
        candidate_dataset_version="2",
        report_schema_version="1.0",
    )

    assert result.comparison.regressed_count == 1
    assert (
            result.gate.decision
            is EvaluationRunCaseRegressionGateDecision.FAIL
    )
    assert (
            result.enforcement.decision
            is EvaluationRunRegressionEnforcementDecision.BLOCK
    )


def test_propagates_missing_baseline_report(tmp_path) -> None:
    with pytest.raises(
            ReportReadError,
            match="Unable to read report",
    ):
        execute_evaluation_run_regression(
            candidate_results=[
                _candidate_result(passed=True),
            ],
            baseline_report_path=tmp_path / "missing.json",
            baseline_provenance_path=_write_baseline_provenance(
                tmp_path
            ),
            candidate_identity=_candidate_identity(),
            candidate_dataset_version="2",
            report_schema_version="1.0",
        )


def test_propagates_invalid_baseline_provenance(tmp_path) -> None:
    provenance_path = tmp_path / "invalid.provenance.json"
    provenance_path.write_text(
        "not-json",
        encoding="utf-8",
    )

    with pytest.raises(
            StoredEvaluationRunProvenanceLoadError,
            match="Invalid evaluation-run provenance JSON",
    ):
        execute_evaluation_run_regression(
            candidate_results=[],
            baseline_report_path=tmp_path / "baseline.json",
            baseline_provenance_path=provenance_path,
            candidate_identity=_candidate_identity(),
            candidate_dataset_version="2",
            report_schema_version="1.0",
        )


def test_rejects_unsupported_report_schema(tmp_path) -> None:
    with pytest.raises(
            ValueError,
            match="Unsupported public report schema version",
    ):
        execute_evaluation_run_regression(
            candidate_results=[],
            baseline_report_path=tmp_path / "baseline.json",
            baseline_provenance_path=_write_baseline_provenance(
                tmp_path
            ),
            candidate_identity=_candidate_identity(),
            candidate_dataset_version="2",
            report_schema_version="999.0",
        )
