"""Public assessment derived from an AI Test Lab report summary.

This module consumes only the public ReportSummary and ReportDecision
contracts. It does not recalculate evaluation, metric, quality-gate,
governance, scoring, or engine logic.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any

from src.report_decision import DecisionStatus, decide_report
from src.report_summary import ReportSummary


class FindingLevel(StrEnum):
    """Severity of a public assessment finding."""

    INFO = "info"
    WARNING = "warning"
    FAILURE = "failure"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class AssessmentFinding:
    """One deterministic finding derived only from public report data."""

    code: str
    level: FindingLevel
    message: str
    test_id: str | None = None
    engine: str | None = None
    metric_name: str | None = None
    score: float | None = None
    threshold: float | None = None


@dataclass(frozen=True, slots=True)
class ReportAssessment:
    """Stable public assessment for downstream report consumers."""

    status: DecisionStatus
    schema_version: str
    generated_at: str
    total: int
    passed: int
    failed: int
    errors: int
    summary: str
    findings: tuple[AssessmentFinding, ...]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable public representation."""
        return asdict(self)


def assess_report(summary: ReportSummary) -> ReportAssessment:
    """Build a deterministic public assessment from a ReportSummary.

    The public decision remains authoritative. Findings explain observable
    public evidence but do not override or recalculate the decision.
    """

    decision = decide_report(summary)
    findings: list[AssessmentFinding] = [_decision_finding(summary, decision.status)]

    for test_id in sorted(set(summary.failed_test_ids)):
        findings.append(
            AssessmentFinding(
                code="failed_test",
                level=FindingLevel.FAILURE,
                test_id=test_id,
                message=f"Test {test_id!r} failed.",
            )
        )

    for metric in sorted(
        summary.failed_metrics,
        key=lambda item: (
            item.test_id,
            item.engine,
            item.metric_name,
            item.score,
            item.threshold,
        ),
    ):
        findings.append(
            AssessmentFinding(
                code="failed_metric",
                level=FindingLevel.FAILURE,
                test_id=metric.test_id,
                engine=metric.engine,
                metric_name=metric.metric_name,
                score=metric.score,
                threshold=metric.threshold,
                message=(
                    f"Metric {metric.metric_name!r} failed for test "
                    f"{metric.test_id!r}: score {metric.score} was below "
                    f"threshold {metric.threshold}."
                ),
            )
        )

    for engine_failure in sorted(
        summary.engine_failures,
        key=lambda item: (item.test_id, item.engine, item.error or ""),
    ):
        message = (
            f"Engine {engine_failure.engine!r} failed for test "
            f"{engine_failure.test_id!r}."
        )
        if engine_failure.error:
            message += f" Error: {engine_failure.error}"

        findings.append(
            AssessmentFinding(
                code="engine_failure",
                level=FindingLevel.WARNING,
                test_id=engine_failure.test_id,
                engine=engine_failure.engine,
                message=message,
            )
        )

    if summary.unexpected_passes:
        findings.append(
            AssessmentFinding(
                code="unexpected_passes",
                level=FindingLevel.WARNING,
                message=(
                    f"Report contains {summary.unexpected_passes} unexpected "
                    "passing test(s)."
                ),
            )
        )

    return ReportAssessment(
        status=decision.status,
        schema_version=decision.schema_version,
        generated_at=decision.generated_at,
        total=decision.total,
        passed=decision.passed,
        failed=decision.failed,
        errors=decision.errors,
        summary=_assessment_summary(summary, decision.status),
        findings=tuple(findings),
    )


def _decision_finding(
    summary: ReportSummary,
    status: DecisionStatus,
) -> AssessmentFinding:
    if status == DecisionStatus.PASS:
        return AssessmentFinding(
            code="report_passed",
            level=FindingLevel.INFO,
            message=f"All {summary.total} evaluated test(s) passed.",
        )

    if status == DecisionStatus.FAIL:
        return AssessmentFinding(
            code="report_failed",
            level=FindingLevel.FAILURE,
            message=(
                f"{summary.failed} of {summary.total} evaluated test(s) failed."
            ),
        )

    if status == DecisionStatus.ERROR:
        return AssessmentFinding(
            code="report_error",
            level=FindingLevel.ERROR,
            message=f"Report contains {summary.errors} evaluation error(s).",
        )

    return AssessmentFinding(
        code="no_data",
        level=FindingLevel.WARNING,
        message="Report contains no evaluation results.",
    )


def _assessment_summary(
    summary: ReportSummary,
    status: DecisionStatus,
) -> str:
    if status == DecisionStatus.PASS:
        return (
            f"Assessment passed: {summary.passed} of {summary.total} "
            "evaluated test(s) passed."
        )

    if status == DecisionStatus.FAIL:
        return (
            f"Assessment failed: {summary.failed} of {summary.total} "
            "evaluated test(s) failed."
        )

    if status == DecisionStatus.ERROR:
        return f"Assessment error: report contains {summary.errors} error(s)."

    return "Assessment unavailable: report contains no evaluation data."
