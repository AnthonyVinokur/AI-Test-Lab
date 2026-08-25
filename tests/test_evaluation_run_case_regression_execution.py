from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from src.baseline_regression_result_acquirer import (
    AcquiredBaselineRegressionResult,
)
from src.evaluation_run_case_regression_execution import (
    execute_evaluation_run_case_regression,
)
from src.evaluation_run_case_regression_gate import (
    EvaluationRunCaseRegressionGateDecision,
)
from src.evaluation_run_provenance import EvaluationRunProvenance
from src.evaluation_run_regression_comparison import (
    EvaluationRunCaseResult,
)
from src.evaluation_run_regression_enforcement import (
    EvaluationRunRegressionEnforcementDecision,
)
from src.evaluation_run_regression_orchestrator import (
    EvaluationRunRegressionOrchestrator,
)
from src.models import TestResult as CandidateTestResult


def make_provenance(run_id: str) -> EvaluationRunProvenance:
    return EvaluationRunProvenance(
        run_id=run_id,
        model="llama3.1:latest",
        evaluation_profile="default",
        dataset="default",
        dataset_version="1.0",
        report_contract="1.0",
        report_contract_fingerprint="fingerprint-001",
    )


def make_candidate_result(
    *,
    passed: bool,
) -> CandidateTestResult:
    return CandidateTestResult.model_construct(
        test_id="case-001",
        passed=passed,
    )


class StubBaselineAcquirer:
    def __init__(
        self,
        case_results: tuple[EvaluationRunCaseResult, ...],
    ) -> None:
        self.case_results = case_results

    def acquire(self) -> AcquiredBaselineRegressionResult:
        return AcquiredBaselineRegressionResult(
            provenance=make_provenance("baseline-run-001"),
            case_results=self.case_results,
        )


class FailingBaselineAcquirer:
    def acquire(self) -> AcquiredBaselineRegressionResult:
        raise RuntimeError("baseline acquisition failed")


def make_orchestrator(
    baseline_results: tuple[EvaluationRunCaseResult, ...],
) -> EvaluationRunRegressionOrchestrator:
    return EvaluationRunRegressionOrchestrator(
        baseline_acquirer=StubBaselineAcquirer(
            baseline_results,
        ),
        candidate_provenance=make_provenance(
            "candidate-run-001",
        ),
    )


def test_executes_pass_allow_chain() -> None:
    orchestrator = make_orchestrator(
        (
            EvaluationRunCaseResult(
                case_id="case-001",
                passed=True,
            ),
        )
    )

    result = execute_evaluation_run_case_regression(
        orchestrator,
        [make_candidate_result(passed=True)],
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


def test_executes_fail_block_chain() -> None:
    orchestrator = make_orchestrator(
        (
            EvaluationRunCaseResult(
                case_id="case-001",
                passed=True,
            ),
        )
    )

    result = execute_evaluation_run_case_regression(
        orchestrator,
        [make_candidate_result(passed=False)],
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


def test_executes_not_applicable_allow_chain() -> None:
    orchestrator = make_orchestrator(())

    result = execute_evaluation_run_case_regression(
        orchestrator,
        [],
    )

    assert result.comparison.compared_count == 0
    assert (
        result.gate.decision
        is EvaluationRunCaseRegressionGateDecision.NOT_APPLICABLE
    )
    assert (
        result.enforcement.decision
        is EvaluationRunRegressionEnforcementDecision.ALLOW
    )


def test_execution_result_is_immutable() -> None:
    orchestrator = make_orchestrator(())

    result = execute_evaluation_run_case_regression(
        orchestrator,
        [],
    )

    with pytest.raises(FrozenInstanceError):
        result.gate = result.gate


def test_rejects_invalid_orchestrator() -> None:
    with pytest.raises(
        TypeError,
        match=(
            "orchestrator must be an "
            "EvaluationRunRegressionOrchestrator"
        ),
    ):
        execute_evaluation_run_case_regression(
            object(),  # type: ignore[arg-type]
            [],
        )


def test_propagates_orchestration_failure() -> None:
    orchestrator = EvaluationRunRegressionOrchestrator(
        baseline_acquirer=FailingBaselineAcquirer(),
        candidate_provenance=make_provenance(
            "candidate-run-001",
        ),
    )

    with pytest.raises(
        RuntimeError,
        match="baseline acquisition failed",
    ):
        execute_evaluation_run_case_regression(
            orchestrator,
            [],
        )
