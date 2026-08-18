from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.report_assessment import ReportAssessment, assess_report
from src.report_decision import ReportDecision, decide_report
from src.report_reader import PublicReport, load_report
from src.report_summary import ReportSummary, summarize_report


@dataclass(frozen=True, slots=True)
class ReportConsumption:
    """Complete public interpretation of a validated AI Test Lab report."""

    report: PublicReport
    summary: ReportSummary
    decision: ReportDecision
    assessment: ReportAssessment


def consume_report(path: str | Path) -> ReportConsumption:
    """Load and interpret a public AI Test Lab report."""

    report = load_report(path)

    summary = summarize_report(
        report.model_dump(mode="json")
    )

    decision = decide_report(summary)
    assessment = assess_report(summary)

    return ReportConsumption(
        report=report,
        summary=summary,
        decision=decision,
        assessment=assessment,
    )