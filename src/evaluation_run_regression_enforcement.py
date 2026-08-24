from dataclasses import dataclass
from enum import Enum

from src.evaluation_run_regression_gate import (
    EvaluationRunRegressionGate,
    EvaluationRunRegressionGateDecision,
)


class EvaluationRunRegressionEnforcementDecision(str, Enum):
    ALLOW = "allow"
    BLOCK = "block"


@dataclass(frozen=True)
class EvaluationRunRegressionEnforcement:
    decision: EvaluationRunRegressionEnforcementDecision


def enforce_evaluation_run_regression_gate(
    gate: EvaluationRunRegressionGate,
) -> EvaluationRunRegressionEnforcement:
    if gate.decision == EvaluationRunRegressionGateDecision.FAIL:
        decision = EvaluationRunRegressionEnforcementDecision.BLOCK
    else:
        decision = EvaluationRunRegressionEnforcementDecision.ALLOW

    return EvaluationRunRegressionEnforcement(
        decision=decision,
    )
