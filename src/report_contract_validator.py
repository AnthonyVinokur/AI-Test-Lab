from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator


class ReportContractValidationError(ValueError):
    """Raised when a public report violates its published contract."""


@lru_cache(maxsize=1)
def _get_report_v1_validator() -> Draft202012Validator:
    schema_path = (
        Path(__file__).resolve().parent.parent
        / "schemas"
        / "report-v1.0.schema.json"
    )

    schema = json.loads(
        schema_path.read_text(encoding="utf-8")
    )

    Draft202012Validator.check_schema(schema)

    return Draft202012Validator(schema)


def validate_report_v1_payload(
    payload: Mapping[str, Any],
) -> None:
    """Validate a serialized public report against schema v1.0."""

    validator = _get_report_v1_validator()

    errors = sorted(
        validator.iter_errors(payload),
        key=lambda error: tuple(
            str(part) for part in error.absolute_path
        ),
    )

    if not errors:
        return

    error = errors[0]

    location = (
        ".".join(str(part) for part in error.absolute_path)
        or "<root>"
    )

    raise ReportContractValidationError(
        "Public report v1.0 contract validation failed "
        f"at {location} "
        f"[{error.validator}]."
    )
