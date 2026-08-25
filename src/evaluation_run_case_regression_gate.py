from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from src.evaluation_run_regression_comparison import (
    EvaluationRunRegressionComparison,
)


class EvaluationRunCaseRegressionGateDecision(str, Enum):
    NOT_APPLICABLE = "not_applicable"
    PASS = "pass"
    FAIL = "fail"


@dataclass(frozen=True)
class EvaluationRunCaseRegressionGate:
    decision: EvaluationRunCaseRegressionGateDecision
    compared_count: int
    unchanged_count: int
    improved_count: int
    regressed_count: int


def evaluate_run_case_regression_gate(
    comparison: EvaluationRunRegressionComparison,
) -> EvaluationRunCaseRegressionGate:
    """Evaluate a deterministic gate from case-level regression results."""

    if not isinstance(
        comparison,
        EvaluationRunRegressionComparison,
    ):
        raise TypeError(
            "comparison must be an "
            "EvaluationRunRegressionComparison"
        )

    if comparison.compared_count == 0:
        decision = (
            EvaluationRunCaseRegressionGateDecision.NOT_APPLICABLE
        )
    elif comparison.has_regressions:
        decision = EvaluationRunCaseRegressionGateDecision.FAIL
    else:
        decision = EvaluationRunCaseRegressionGateDecision.PASS

    return EvaluationRunCaseRegressionGate(
        decision=decision,
        compared_count=comparison.compared_count,
        unchanged_count=comparison.unchanged_count,
        improved_count=comparison.improved_count,
        regressed_count=comparison.regressed_count,
    )