from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator


class ReportContractValidationError(ValueError):
    """Raised when a public report violates its published contract."""


_REPORT_SCHEMA_FILES = {
    "1.0": "report-v1.0.schema.json",
}


def supported_report_schema_versions() -> tuple[str, ...]:
    """Return the report contract versions understood by this runtime."""

    return tuple(_REPORT_SCHEMA_FILES)

def is_report_schema_version_supported(
    schema_version: str,
) -> bool:
    """Return whether this runtime supports a public report schema version."""

    return schema_version in _REPORT_SCHEMA_FILES


@lru_cache(maxsize=None)
def _get_report_validator(
    schema_version: str,
) -> Draft202012Validator:
    schema_filename = _REPORT_SCHEMA_FILES.get(schema_version)

    if schema_filename is None:
        raise ReportContractValidationError(
            "Unsupported public report schema version "
            f"'{schema_version}'."
        )

    schema_path = (
        Path(__file__).resolve().parent.parent
        / "schemas"
        / schema_filename
    )

    schema = json.loads(
        schema_path.read_text(encoding="utf-8")
    )

    Draft202012Validator.check_schema(schema)

    return Draft202012Validator(schema)


def _validate_payload_against_version(
    payload: Mapping[str, Any],
    schema_version: str,
) -> None:
    validator = _get_report_validator(schema_version)

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
        ".".join(
            str(part)
            for part in error.absolute_path
        )
        or "<root>"
    )

    raise ReportContractValidationError(
        "Public report "
        f"v{schema_version} contract validation failed "
        f"at {location} "
        f"[{error.validator}]."
    )


def validate_report_payload(
    payload: Mapping[str, Any],
) -> None:
    """Validate a public report using its declared schema version."""

    schema_version = payload.get("schema_version")

    if not isinstance(schema_version, str):
        raise ReportContractValidationError(
            "Public report contract validation failed "
            "at schema_version [required]."
        )

    if schema_version not in _REPORT_SCHEMA_FILES:
        raise ReportContractValidationError(
            "Unsupported public report schema version "
            f"'{schema_version}'."
        )

    _validate_payload_against_version(
        payload,
        schema_version,
    )


def validate_report_v1_payload(
    payload: Mapping[str, Any],
) -> None:
    """Validate a serialized public report against schema v1.0."""

    _validate_payload_against_version(
        payload,
        "1.0",
    )