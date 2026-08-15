import json
from datetime import datetime
from pathlib import Path

from src.models import EvaluationStatus, TestResult
from src.report_analytics import (
    build_model_summaries,
    get_fastest_model,
    get_highest_scoring_model,
)
from src.report_mapper import map_model_summary, map_test_result
from src.report_schema import (
    ReportHighlightsV1,
    ReportSummaryV1,
    ReportV1,
)


from src.report_contract_validator import validate_report_payload

class JsonReporter:
    """Writes validated public AI test evidence to JSON."""

    def __init__(self, report_path: Path) -> None:
        self.report_path = report_path

    def write(self, results: list[TestResult]) -> None:
        self.report_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        generated_at = (
            datetime.now()
            .astimezone()
            .isoformat(timespec="seconds")
        )

        passed = sum(
            result.status == EvaluationStatus.PASS
            for result in results
        )
        failed = sum(
            result.status == EvaluationStatus.FAIL
            for result in results
        )
        expected_failures = sum(
            result.status == EvaluationStatus.XFAIL
            for result in results
        )
        unexpected_passes = sum(
            result.status == EvaluationStatus.XPASS
            for result in results
        )
        errors = sum(
            result.status == EvaluationStatus.ERROR
            for result in results
        )

        total = len(results)
        total_estimated_cost_usd = round(
            sum(result.estimated_cost_usd for result in results),
            6,
        )
        pass_rate_percent = (
            round(passed / total * 100, 2)
            if total
            else 0.0
        )

        model_summaries = build_model_summaries(results)
        fastest_model = get_fastest_model(model_summaries)
        highest_scoring_model = get_highest_scoring_model(
            model_summaries
        )

        # IP Protection Boundary:
        # Internal runtime models never serialize directly. Every field that
        # crosses into the public report contract is explicitly allow-listed
        # by the ReportV1 DTOs and mapper functions.
        report = ReportV1(
            generated_at=generated_at,
            models=[summary.model for summary in model_summaries],
            summary=ReportSummaryV1(
                passed=passed,
                failed=failed,
                expected_failures=expected_failures,
                unexpected_passes=unexpected_passes,
                errors=errors,
                total=total,
                pass_rate_percent=pass_rate_percent,
                total_estimated_cost_usd=total_estimated_cost_usd,
            ),
            highlights=ReportHighlightsV1(
                highest_scoring_model=(
                    highest_scoring_model.model
                    if highest_scoring_model
                    else None
                ),
                fastest_model=(
                    fastest_model.model
                    if fastest_model
                    else None
                ),
            ),
            model_comparison=[
                map_model_summary(summary)
                for summary in model_summaries
            ],
            results=[
                map_test_result(result)
                for result in results
            ],
        )

        report_payload = report.model_dump(mode="json")

        # Runtime public-contract boundary:
        # The explicit public DTO has already removed internal runtime state.
        # Validate the final serialized representation against the published
        # JSON Schema before allowing the artifact to reach disk.
        validate_report_payload(report_payload)

        self.report_path.write_text(
            json.dumps(
                report_payload,
                indent=2,
            ),
            encoding="utf-8",
        )
