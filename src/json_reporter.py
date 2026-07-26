import json
from datetime import datetime
from pathlib import Path

from src.models import EvaluationStatus, TestResult
from src.report_analytics import (
    build_model_summaries,
    get_fastest_model,
    get_highest_scoring_model,
)


class JsonReporter:
    """Writes AI test results and model comparisons to JSON."""

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
        errors = sum(
            result.status == EvaluationStatus.ERROR
            for result in results
        )

        total = len(results)
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

        report = {
            "generated_at": generated_at,
            "models": [
                summary.model
                for summary in model_summaries
            ],
            "summary": {
                "passed": passed,
                "failed": failed,
                "errors": errors,
                "total": total,
                "pass_rate_percent": pass_rate_percent,
            },
            "highlights": {
                "highest_scoring_model": (
                    highest_scoring_model.model
                    if highest_scoring_model
                    else None
                ),
                "fastest_model": (
                    fastest_model.model
                    if fastest_model
                    else None
                ),
            },
            "model_comparison": [
                summary.model_dump(mode="json")
                for summary in model_summaries
            ],
            "results": [
                result.model_dump(mode="json")
                for result in results
            ],
        }

        self.report_path.write_text(
            json.dumps(report, indent=2),
            encoding="utf-8",
        )