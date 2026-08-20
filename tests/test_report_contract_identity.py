from __future__ import annotations

import pytest

from src.report_contract_identity import (
    PUBLIC_REPORT_CONTRACT_NAME,
    public_report_contract_identity,
)
from src.report_contract_validator import supported_report_schema_versions


def test_public_report_contract_name_is_stable() -> None:
    assert PUBLIC_REPORT_CONTRACT_NAME == "ai-test-lab.public-report"


def test_supported_schema_version_has_stable_contract_identity() -> None:
    identity = public_report_contract_identity("1.0")

    assert identity.name == "ai-test-lab.public-report"
    assert identity.schema_version == "1.0"


def test_same_schema_version_produces_same_contract_identity() -> None:
    first = public_report_contract_identity("1.0")
    second = public_report_contract_identity("1.0")

    assert first == second


def test_unsupported_schema_version_has_no_contract_identity() -> None:
    with pytest.raises(
            ValueError,
            match="Unsupported public report schema version",
    ):
        public_report_contract_identity("9.0")


def test_every_supported_schema_version_has_contract_identity() -> None:
    for schema_version in supported_report_schema_versions():
        identity = public_report_contract_identity(schema_version)

        assert identity.name == PUBLIC_REPORT_CONTRACT_NAME
        assert identity.schema_version == schema_version
