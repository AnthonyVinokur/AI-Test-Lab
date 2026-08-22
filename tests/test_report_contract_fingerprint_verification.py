from __future__ import annotations

import pytest

from src.report_contract_fingerprint import (
    public_report_contract_fingerprint,
)
from src.report_contract_verification import (
    verify_public_report_contract_fingerprint,
)


def test_matching_contract_fingerprint_verifies() -> None:
    fingerprint = public_report_contract_fingerprint("1.0")

    assert verify_public_report_contract_fingerprint(
        "1.0",
        fingerprint,
    ) is True


def test_mismatched_contract_fingerprint_does_not_verify() -> None:
    fingerprint = "sha256:" + "0" * 64

    assert verify_public_report_contract_fingerprint(
        "1.0",
        fingerprint,
    ) is False


@pytest.mark.parametrize(
    "fingerprint",
    (
        "",
        "sha256:",
        "md5:" + "0" * 32,
        "sha256:" + "0" * 63,
        "sha256:" + "0" * 65,
        "sha256:" + "G" * 64,
    ),
)
def test_malformed_contract_fingerprint_is_rejected(
    fingerprint: str,
) -> None:
    with pytest.raises(
        ValueError,
        match="Malformed public report contract fingerprint",
    ):
        verify_public_report_contract_fingerprint(
            "1.0",
            fingerprint,
        )


def test_unsupported_schema_version_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="Unsupported public report schema version",
    ):
        verify_public_report_contract_fingerprint(
            "9.0",
            "sha256:" + "0" * 64,
        )
