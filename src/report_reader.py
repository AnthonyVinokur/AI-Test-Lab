from __future__ import annotations

import json
from pathlib import Path
from typing import TypeAlias

from pydantic import ValidationError

from src.report_contract_validator import validate_report_payload
from src.report_schema import ReportV1


PublicReport: TypeAlias = ReportV1


class ReportReadError(ValueError):
    """Raised when a public report cannot be read."""


_REPORT_MODELS = {
    "1.0": ReportV1,
}


def load_report(path: str | Path) -> PublicReport:
    """Load and validate a versioned public AI Test Lab report."""

    report_path = Path(path)

    try:
        raw = report_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ReportReadError(
            f"Unable to read report '{report_path}'."
        ) from exc

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ReportReadError(
            f"Invalid report JSON in '{report_path}'."
        ) from exc

    if not isinstance(payload, dict):
        raise ReportReadError(
            "Report JSON root must be an object."
        )

    # The published JSON Schema remains the authoritative
    # external contract boundary.
    validate_report_payload(payload)

    schema_version = payload["schema_version"]
    report_model = _REPORT_MODELS[schema_version]

    try:
        return report_model.model_validate(payload)
    except ValidationError as exc:
        raise ReportReadError(
            "Validated public report could not be converted "
            "to its consumer model."
        ) from exc