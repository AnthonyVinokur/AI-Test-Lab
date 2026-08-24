from dataclasses import dataclass
from enum import Enum

from src.evaluation_metric_regression_severity import (
    EvaluationMetricRegressionSeverity,
    MetricRegressionSeverity,
)


class MetricRegressionGateDecision(str, Enum):
    NOT_APPLICABLE = "not_applicable"
    PASS = "pass"
    FAIL = "fail"


@dataclass(frozen=True)
class EvaluationMetricRegressionGate:
    severity: MetricRegressionSeverity
    max_allowed_severity: MetricRegressionSeverity
    decision: MetricRegressionGateDecision


_SEVERITY_RANK = {
    MetricRegressionSeverity.ACCEPTABLE: 0,
    MetricRegressionSeverity.MINOR: 1,
    MetricRegressionSeverity.MAJOR: 2,
    MetricRegressionSeverity.CRITICAL: 3,
}


def evaluate_metric_regression_gate(
    severity_result: EvaluationMetricRegressionSeverity,
    *,
    max_allowed_severity: MetricRegressionSeverity,
) -> EvaluationMetricRegressionGate:
    if max_allowed_severity is MetricRegressionSeverity.NOT_APPLICABLE:
        raise ValueError(
            "max_allowed_severity cannot be NOT_APPLICABLE"
        )

    severity = severity_result.severity

    if severity is MetricRegressionSeverity.NOT_APPLICABLE:
        return EvaluationMetricRegressionGate(
            severity=severity,
            max_allowed_severity=max_allowed_severity,
            decision=MetricRegressionGateDecision.NOT_APPLICABLE,
        )

    decision = (
        MetricRegressionGateDecision.PASS
        if _SEVERITY_RANK[severity]
        <= _SEVERITY_RANK[max_allowed_severity]
        else MetricRegressionGateDecision.FAIL
    )

    return EvaluationMetricRegressionGate(
        severity=severity,
        max_allowed_severity=max_allowed_severity,
        decision=decision,
    )