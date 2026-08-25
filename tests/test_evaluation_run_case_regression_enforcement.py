from dataclasses import FrozenInstanceError

import pytest

from src.evaluation_run_case_regression_gate import (
    EvaluationRunCaseRegressionGate,
    EvaluationRunCaseRegressionGateDecision,
)
from src.evaluation_run_regression_enforcement import (
    EvaluationRunRegressionEnforcementDecision,
    enforce_evaluation_run_case_regression_gate,
)


def make_gate(
    decision: EvaluationRunCaseRegressionGateDecision,
) -> EvaluationRunCaseRegressionGate:
    return EvaluationRunCaseRegressionGate(
        decision=decision,
        compared_count=1,
        unchanged_count=0,
        improved_count=0,
        regressed_count=0,
    )


def test_pass_case_gate_is_allowed() -> None:
    gate = make_gate(
        EvaluationRunCaseRegressionGateDecision.PASS,
    )

    result = enforce_evaluation_run_case_regression_gate(gate)

    assert (
        result.decision
        == EvaluationRunRegressionEnforcementDecision.ALLOW
    )


def test_fail_case_gate_is_blocked() -> None:
    gate = make_gate(
        EvaluationRunCaseRegressionGateDecision.FAIL,
    )

    result = enforce_evaluation_run_case_regression_gate(gate)

    assert (
        result.decision
        == EvaluationRunRegressionEnforcementDecision.BLOCK
    )


def test_not_applicable_case_gate_is_allowed() -> None:
    gate = make_gate(
        EvaluationRunCaseRegressionGateDecision.NOT_APPLICABLE,
    )

    result = enforce_evaluation_run_case_regression_gate(gate)

    assert (
        result.decision
        == EvaluationRunRegressionEnforcementDecision.ALLOW
    )


def test_same_case_gate_produces_same_enforcement() -> None:
    gate = make_gate(
        EvaluationRunCaseRegressionGateDecision.FAIL,
    )

    first = enforce_evaluation_run_case_regression_gate(gate)
    second = enforce_evaluation_run_case_regression_gate(gate)

    assert first == second


def test_case_gate_enforcement_result_is_immutable() -> None:
    gate = make_gate(
        EvaluationRunCaseRegressionGateDecision.PASS,
    )
    result = enforce_evaluation_run_case_regression_gate(gate)

    with pytest.raises(FrozenInstanceError):
        result.decision = (
            EvaluationRunRegressionEnforcementDecision.BLOCK
        )


def test_non_case_gate_input_is_rejected() -> None:
    with pytest.raises(
        TypeError,
        match=(
            "gate must be an "
            "EvaluationRunCaseRegressionGate"
        ),
    ):
        enforce_evaluation_run_case_regression_gate(
            object(),  # type: ignore[arg-type]
        )
