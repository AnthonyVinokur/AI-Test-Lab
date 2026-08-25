from __future__ import annotations

from dataclasses import dataclass

from src.evaluation_run_case_regression_gate import (
    EvaluationRunCaseRegressionGate,
    evaluate_run_case_regression_gate,
)
from src.evaluation_run_regression_comparison import (
    EvaluationRunRegressionComparison,
)
from src.evaluation_run_regression_enforcement import (
    EvaluationRunRegressionEnforcement,
    enforce_evaluation_run_case_regression_gate,
)
from src.evaluation_run_regression_orchestrator import (
    EvaluationRunRegressionOrchestrator,
)
from src.models import TestResult


@dataclass(frozen=True)
class EvaluationRunCaseRegressionExecution:
    """Result of the case-level regression execution chain."""

    comparison: EvaluationRunRegressionComparison
    gate: EvaluationRunCaseRegressionGate
    enforcement: EvaluationRunRegressionEnforcement


def execute_evaluation_run_case_regression(
    orchestrator: EvaluationRunRegressionOrchestrator,
    candidate_results: list[TestResult],
) -> EvaluationRunCaseRegressionExecution:
    """Execute comparison, case-level gating, and enforcement."""

    if not isinstance(
        orchestrator,
        EvaluationRunRegressionOrchestrator,
    ):
        raise TypeError(
            "orchestrator must be an "
            "EvaluationRunRegressionOrchestrator"
        )

    comparison = orchestrator.compare(candidate_results)
    gate = evaluate_run_case_regression_gate(comparison)
    enforcement = enforce_evaluation_run_case_regression_gate(
        gate
    )

    return EvaluationRunCaseRegressionExecution(
        comparison=comparison,
        gate=gate,
        enforcement=enforcement,
    )
