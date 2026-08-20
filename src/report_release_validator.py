from pathlib import Path

from src.report_consumer import consume_report
from src.report_contract_validator import ReportContractValidationError
from src.report_reader import ReportReadError


class ReportReleaseValidationError(ValueError):
    """Raised when a public report is not safe or valid for release."""


def validate_report_for_release(report_path: str | Path) -> None:
    try:
        consume_report(report_path)
    except (ReportContractValidationError, ReportReadError) as exc:
        raise ReportReleaseValidationError(
            "Public report is not release ready."
        ) from exc