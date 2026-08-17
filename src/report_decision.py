"""Public decision model derived from an AI Test Lab report summary.

This module consumes only the public ReportSummary contract. It does not
recalculate evaluation, metric, quality-gate, governance, or engine logic.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any

from src.report_summary import ReportSummary


class DecisionStatus(StrEnum):
    """Public decision states derived from a report summary."""

    PASS = "pass"
    FAIL = "fail"
    ERROR = "error"
    NO_DATA = "no_data"


@dataclass(frozen=True, slots=True)
class ReportDecision:
    """Small public decision derived from a ReportSummary."""

    status: DecisionStatus
    schema_version: str
    generated_at: str
    total: int
    passed: int
    failed: int
    errors: int

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable public representation."""
        return asdict(self)


def decide_report(summary: ReportSummary) -> ReportDecision:
    """Translate a public report summary into a consumer decision."""

    status_map = {
        "passed": DecisionStatus.PASS,
        "failed": DecisionStatus.FAIL,
        "error": DecisionStatus.ERROR,
        "empty": DecisionStatus.NO_DATA,
    }

    try:
        status = status_map[summary.overall_status]
    except KeyError as exc:
        raise ValueError(
            f"unsupported report summary status: {summary.overall_status!r}"
        ) from exc

    return ReportDecision(
        status=status,
        schema_version=summary.schema_version,
        generated_at=summary.generated_at,
        total=summary.total,
        passed=summary.passed,
        failed=summary.failed,
        errors=summary.errors,
    )