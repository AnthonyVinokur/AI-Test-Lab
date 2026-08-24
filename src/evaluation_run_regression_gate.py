from dataclasses import dataclass
from enum import Enum

from src.evaluation_metric_regression_gate import MetricRegressionGateDecision


class EvaluationRunRegressionGateDecision(str, Enum):
    NOT_APPLICABLE = "not_applicable"
    PASS = "pass"
    FAIL = "fail"


@dataclass(frozen=True)
class EvaluationRunRegressionGate:
    decision: EvaluationRunRegressionGateDecision
    total_metrics: int
    passed_metrics: int
    failed_metrics: int
    not_applicable_metrics: int


def evaluate_run_regression_gate(
    metric_decisions: tuple[MetricRegressionGateDecision, ...],
) -> EvaluationRunRegressionGate:
    total_metrics = len(metric_decisions)

    passed_metrics = sum(
        decision == MetricRegressionGateDecision.PASS
        for decision in metric_decisions
    )
    failed_metrics = sum(
        decision == MetricRegressionGateDecision.FAIL
        for decision in metric_decisions
    )
    not_applicable_metrics = sum(
        decision == MetricRegressionGateDecision.NOT_APPLICABLE
        for decision in metric_decisions
    )

    if failed_metrics > 0:
        decision = EvaluationRunRegressionGateDecision.FAIL
    elif passed_metrics > 0:
        decision = EvaluationRunRegressionGateDecision.PASS
    else:
        decision = EvaluationRunRegressionGateDecision.NOT_APPLICABLE

    return EvaluationRunRegressionGate(
        decision=decision,
        total_metrics=total_metrics,
        passed_metrics=passed_metrics,
        failed_metrics=failed_metrics,
        not_applicable_metrics=not_applicable_metrics,
    )
