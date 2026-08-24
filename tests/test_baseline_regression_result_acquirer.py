from dataclasses import FrozenInstanceError

import pytest

from src.baseline_regression_result_acquirer import (
    AcquiredBaselineRegressionResult,
    BaselineRegressionResultAcquirer,
)
from src.evaluation_run_provenance import EvaluationRunProvenance
from src.evaluation_run_regression_comparison import (
    EvaluationRunCaseResult,
)


def make_provenance() -> EvaluationRunProvenance:
    return EvaluationRunProvenance(
        run_id="baseline-run-001",
        model="llama3.1:latest",
        evaluation_profile="fast-ci",
        dataset="core-regression",
        dataset_version="1.0.0",
        report_contract="evaluation-report-v1",
        report_contract_fingerprint="fingerprint-001",
    )


def test_groups_baseline_provenance_and_case_results() -> None:
    provenance = make_provenance()
    case_results = (
        EvaluationRunCaseResult(
            case_id="greeting-001",
            passed=True,
        ),
        EvaluationRunCaseResult(
            case_id="python-001",
            passed=False,
        ),
    )

    acquired = AcquiredBaselineRegressionResult(
        provenance=provenance,
        case_results=case_results,
    )

    assert acquired.provenance is provenance
    assert acquired.case_results is case_results


def test_acquired_baseline_result_is_immutable() -> None:
    acquired = AcquiredBaselineRegressionResult(
        provenance=make_provenance(),
        case_results=(),
    )

    with pytest.raises(FrozenInstanceError):
        acquired.case_results = ()  # type: ignore[misc]


def test_empty_case_results_are_preserved() -> None:
    acquired = AcquiredBaselineRegressionResult(
        provenance=make_provenance(),
        case_results=(),
    )

    assert acquired.case_results == ()


def test_rejects_invalid_provenance() -> None:
    with pytest.raises(
        TypeError,
        match="provenance must be an EvaluationRunProvenance",
    ):
        AcquiredBaselineRegressionResult(
            provenance="invalid",  # type: ignore[arg-type]
            case_results=(),
        )


def test_rejects_non_tuple_case_results() -> None:
    with pytest.raises(
        TypeError,
        match="case_results must be a tuple",
    ):
        AcquiredBaselineRegressionResult(
            provenance=make_provenance(),
            case_results=[],  # type: ignore[arg-type]
        )


def test_rejects_invalid_case_result_members() -> None:
    with pytest.raises(
        TypeError,
        match=(
            "case_results must contain "
            "EvaluationRunCaseResult objects"
        ),
    ):
        AcquiredBaselineRegressionResult(
            provenance=make_provenance(),
            case_results=("invalid",),  # type: ignore[arg-type]
        )


def test_acquirer_protocol_describes_expected_return_contract() -> None:
    class StubAcquirer:
        def acquire(self) -> AcquiredBaselineRegressionResult:
            return AcquiredBaselineRegressionResult(
                provenance=make_provenance(),
                case_results=(
                    EvaluationRunCaseResult(
                        case_id="greeting-001",
                        passed=True,
                    ),
                ),
            )

    acquirer: BaselineRegressionResultAcquirer = StubAcquirer()

    acquired = acquirer.acquire()

    assert acquired.provenance.run_id == "baseline-run-001"
    assert acquired.case_results == (
        EvaluationRunCaseResult(
            case_id="greeting-001",
            passed=True,
        ),
    )
