from dataclasses import FrozenInstanceError

import pytest

from src.evaluation_run_regression_enforcement import (
    EvaluationRunRegressionEnforcementDecision,
    enforce_evaluation_run_regression_gate,
)
from src.evaluation_run_regression_gate import (
    EvaluationRunRegressionGate,
    EvaluationRunRegressionGateDecision,
)


def make_gate(
    decision: EvaluationRunRegressionGateDecision,
) -> EvaluationRunRegressionGate:
    return EvaluationRunRegressionGate(
        decision=decision,
        total_metrics=1,
        passed_metrics=0,
        failed_metrics=0,
        not_applicable_metrics=0,
    )


def test_pass_gate_is_allowed():
    gate = make_gate(EvaluationRunRegressionGateDecision.PASS)

    result = enforce_evaluation_run_regression_gate(gate)

    assert result.decision == EvaluationRunRegressionEnforcementDecision.ALLOW


def test_fail_gate_is_blocked():
    gate = make_gate(EvaluationRunRegressionGateDecision.FAIL)

    result = enforce_evaluation_run_regression_gate(gate)

    assert result.decision == EvaluationRunRegressionEnforcementDecision.BLOCK


def test_not_applicable_gate_is_allowed():
    gate = make_gate(EvaluationRunRegressionGateDecision.NOT_APPLICABLE)

    result = enforce_evaluation_run_regression_gate(gate)

    assert result.decision == EvaluationRunRegressionEnforcementDecision.ALLOW


def test_same_gate_produces_same_enforcement_decision():
    gate = make_gate(EvaluationRunRegressionGateDecision.FAIL)

    first = enforce_evaluation_run_regression_gate(gate)
    second = enforce_evaluation_run_regression_gate(gate)

    assert first == second


def test_result_is_immutable():
    gate = make_gate(EvaluationRunRegressionGateDecision.PASS)
    result = enforce_evaluation_run_regression_gate(gate)

    with pytest.raises(FrozenInstanceError):
        result.decision = EvaluationRunRegressionEnforcementDecision.BLOCK