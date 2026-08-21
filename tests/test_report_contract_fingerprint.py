from __future__ import annotations

import re

import pytest

from src.report_contract_fingerprint import (
    PUBLIC_REPORT_FINGERPRINT_ALGORITHM,
    public_report_contract_fingerprint,
)
from src.report_contract_validator import supported_report_schema_versions


def test_public_report_fingerprint_algorithm_is_stable() -> None:
    assert PUBLIC_REPORT_FINGERPRINT_ALGORITHM == "sha256"


def test_supported_schema_version_has_contract_fingerprint() -> None:
    fingerprint = public_report_contract_fingerprint("1.0")

    assert fingerprint.startswith("sha256:")
    assert re.fullmatch(r"sha256:[0-9a-f]{64}", fingerprint)


def test_same_schema_version_produces_same_fingerprint() -> None:
    first = public_report_contract_fingerprint("1.0")
    second = public_report_contract_fingerprint("1.0")

    assert first == second


def test_every_supported_schema_version_has_contract_fingerprint() -> None:
    for schema_version in supported_report_schema_versions():
        fingerprint = public_report_contract_fingerprint(schema_version)

        assert re.fullmatch(r"sha256:[0-9a-f]{64}", fingerprint)


def test_unsupported_schema_version_has_no_contract_fingerprint() -> None:
    with pytest.raises(
            ValueError,
            match="Unsupported public report schema version",
    ):
        public_report_contract_fingerprint("9.0")
