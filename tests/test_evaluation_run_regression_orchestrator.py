from __future__ import annotations

import pytest

from src.baseline_regression_result_acquirer import (
    AcquiredBaselineRegressionResult,
)
from src.evaluation_run_provenance import EvaluationRunProvenance
from src.evaluation_run_regression_comparison import (
    EvaluationRunCaseResult,
    EvaluationRunRegressionChange,
)
from src.evaluation_run_regression_orchestrator import (
    EvaluationRunRegressionOrchestrator,
)
from src.models import TestResult as CandidateTestResult


def make_provenance(
    run_id: str,
    *,
    model: str = "llama3.1:latest",
) -> EvaluationRunProvenance:
    return EvaluationRunProvenance(
        run_id=run_id,
        model=model,
        evaluation_profile="default",
        dataset="default",
        dataset_version="1.0",
        report_contract="1.0",
        report_contract_fingerprint="fingerprint-001",
    )


def make_candidate_result(
    *,
    test_id: str,
    passed: bool,
) -> CandidateTestResult:
    return CandidateTestResult.model_construct(
        test_id=test_id,
        passed=passed,
    )


class StubBaselineAcquirer:
    def __init__(
        self,
        acquired: AcquiredBaselineRegressionResult,
    ) -> None:
        self.acquired = acquired
        self.acquire_count = 0

    def acquire(self) -> AcquiredBaselineRegressionResult:
        self.acquire_count += 1
        return self.acquired


class FailingBaselineAcquirer:
    def acquire(self) -> AcquiredBaselineRegressionResult:
        raise RuntimeError("baseline acquisition failed")


def make_baseline_acquirer() -> StubBaselineAcquirer:
    return StubBaselineAcquirer(
        AcquiredBaselineRegressionResult(
            provenance=make_provenance("baseline-run-001"),
            case_results=(
                EvaluationRunCaseResult(
                    case_id="case-001",
                    passed=True,
                ),
            ),
        )
    )


def test_acquires_adapts_and_compares_runs() -> None:
    acquirer = make_baseline_acquirer()
    orchestrator = EvaluationRunRegressionOrchestrator(
        baseline_acquirer=acquirer,
        candidate_provenance=make_provenance(
            "candidate-run-001"
        ),
    )

    comparison = orchestrator.compare(
        [
            make_candidate_result(
                test_id="case-001",
                passed=False,
            )
        ]
    )

    assert acquirer.acquire_count == 1
    assert comparison.baseline_run_id == "baseline-run-001"
    assert comparison.candidate_run_id == "candidate-run-001"
    assert comparison.compared_count == 1
    assert comparison.regressed_count == 1
    assert (
        comparison.case_comparisons[0].change
        is EvaluationRunRegressionChange.REGRESSED
    )


def test_preserves_empty_runs() -> None:
    acquirer = StubBaselineAcquirer(
        AcquiredBaselineRegressionResult(
            provenance=make_provenance("baseline-run-001"),
            case_results=(),
        )
    )
    orchestrator = EvaluationRunRegressionOrchestrator(
        baseline_acquirer=acquirer,
        candidate_provenance=make_provenance(
            "candidate-run-001"
        ),
    )

    comparison = orchestrator.compare([])

    assert comparison.compared_count == 0
    assert comparison.case_comparisons == ()


def test_propagates_baseline_acquisition_failure() -> None:
    orchestrator = EvaluationRunRegressionOrchestrator(
        baseline_acquirer=FailingBaselineAcquirer(),
        candidate_provenance=make_provenance(
            "candidate-run-001"
        ),
    )

    with pytest.raises(
        RuntimeError,
        match="baseline acquisition failed",
    ):
        orchestrator.compare([])


def test_propagates_ineligible_provenance_failure() -> None:
    acquirer = make_baseline_acquirer()
    orchestrator = EvaluationRunRegressionOrchestrator(
        baseline_acquirer=acquirer,
        candidate_provenance=make_provenance(
            "candidate-run-001",
            model="different-model",
        ),
    )

    with pytest.raises(
        ValueError,
        match=(
            "evaluation runs are not eligible "
            "for regression comparison"
        ),
    ):
        orchestrator.compare(
            [
                make_candidate_result(
                    test_id="case-001",
                    passed=True,
                )
            ]
        )


def test_propagates_candidate_adaptation_failure() -> None:
    orchestrator = EvaluationRunRegressionOrchestrator(
        baseline_acquirer=make_baseline_acquirer(),
        candidate_provenance=make_provenance(
            "candidate-run-001"
        ),
    )

    with pytest.raises(
        TypeError,
        match="results must contain TestResult objects",
    ):
        orchestrator.compare(
            ["invalid"]  # type: ignore[list-item]
        )


def test_rejects_invalid_candidate_provenance() -> None:
    with pytest.raises(
        TypeError,
        match=(
            "candidate_provenance must be an "
            "EvaluationRunProvenance"
        ),
    ):
        EvaluationRunRegressionOrchestrator(
            baseline_acquirer=make_baseline_acquirer(),
            candidate_provenance="invalid",  # type: ignore[arg-type]
        )

