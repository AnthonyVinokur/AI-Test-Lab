from __future__ import annotations

from pathlib import Path

import pytest

import json

from src.report_contract_validator import (
    ReportContractValidationError,
)

from src.evaluation_run_provenance import EvaluationRunProvenance
from src.evaluation_run_regression_comparison import (
    EvaluationRunCaseResult,
)
from src.report_reader import ReportReadError
from src.stored_baseline_regression_result_acquirer import (
    StoredBaselineRegressionResultAcquirer,
)


_FIXTURE_PATH = (
    Path(__file__).parent
    / "fixtures"
    / "report-v1.0.json"
)


def make_provenance() -> EvaluationRunProvenance:
    return EvaluationRunProvenance(
        run_id="baseline-run-001",
        model="llama3.1:latest",
        evaluation_profile="default",
        dataset="default",
        dataset_version="1.0",
        report_contract="1.0",
        report_contract_fingerprint="fingerprint-001",
    )


def test_acquires_case_results_from_stored_public_report() -> None:
    provenance = make_provenance()
    acquirer = StoredBaselineRegressionResultAcquirer(
        report_path=_FIXTURE_PATH,
        provenance=provenance,
    )

    acquired = acquirer.acquire()

    assert acquired.provenance is provenance
    assert acquired.case_results == (
        EvaluationRunCaseResult(
            case_id="greeting-001",
            passed=True,
        ),
    )


def test_acquired_case_results_are_immutable_tuple() -> None:
    acquired = StoredBaselineRegressionResultAcquirer(
        report_path=_FIXTURE_PATH,
        provenance=make_provenance(),
    ).acquire()

    assert isinstance(acquired.case_results, tuple)


def test_missing_report_is_rejected(tmp_path: Path) -> None:
    acquirer = StoredBaselineRegressionResultAcquirer(
        report_path=tmp_path / "missing.json",
        provenance=make_provenance(),
    )

    with pytest.raises(
        ReportReadError,
        match="Unable to read report",
    ):
        acquirer.acquire()


def test_invalid_report_json_is_rejected(tmp_path: Path) -> None:
    report_path = tmp_path / "invalid.json"
    report_path.write_text(
        "{not valid json",
        encoding="utf-8",
    )
    acquirer = StoredBaselineRegressionResultAcquirer(
        report_path=report_path,
        provenance=make_provenance(),
    )

    with pytest.raises(
        ReportReadError,
        match="Invalid report JSON",
    ):
        acquirer.acquire()


def test_rejects_invalid_provenance() -> None:
    with pytest.raises(
        TypeError,
        match="provenance must be an EvaluationRunProvenance",
    ):
        StoredBaselineRegressionResultAcquirer(
            report_path=_FIXTURE_PATH,
            provenance="invalid",  # type: ignore[arg-type]
        )

def test_empty_report_results_are_preserved(
    tmp_path: Path,
) -> None:
    payload = json.loads(
        _FIXTURE_PATH.read_text(encoding="utf-8")
    )
    payload["results"] = []

    report_path = tmp_path / "empty-report.json"
    report_path.write_text(
        json.dumps(payload),
        encoding="utf-8",
    )

    acquired = StoredBaselineRegressionResultAcquirer(
        report_path=report_path,
        provenance=make_provenance(),
    ).acquire()

    assert acquired.case_results == ()


def test_structurally_invalid_report_is_rejected(
    tmp_path: Path,
) -> None:
    payload = json.loads(
        _FIXTURE_PATH.read_text(encoding="utf-8")
    )
    payload["results"][0].pop("test_id")

    report_path = tmp_path / "invalid-report.json"
    report_path.write_text(
        json.dumps(payload),
        encoding="utf-8",
    )

    acquirer = StoredBaselineRegressionResultAcquirer(
        report_path=report_path,
        provenance=make_provenance(),
    )

    with pytest.raises(
        ReportContractValidationError,
        match="contract validation failed",
    ):
        acquirer.acquire()
