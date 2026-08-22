from __future__ import annotations

from pathlib import Path

import pytest

from src.report_contract_fingerprint import (
    public_report_contract_fingerprint,
)
from src.report_contract_verification import (
    verify_public_report_contract_for_report,
)

REPORT_FIXTURE = Path("tests/fixtures/report-v1.0.json")


def test_report_verifies_against_matching_public_contract() -> None:
    fingerprint = public_report_contract_fingerprint("1.0")

    assert verify_public_report_contract_for_report(
        REPORT_FIXTURE,
        fingerprint,
    ) is True


def test_report_does_not_verify_against_different_public_contract() -> None:
    fingerprint = "sha256:" + "0" * 64

    assert verify_public_report_contract_for_report(
        REPORT_FIXTURE,
        fingerprint,
    ) is False


def test_report_contract_verification_rejects_malformed_fingerprint() -> None:
    with pytest.raises(
            ValueError,
            match="Malformed public report contract fingerprint",
    ):
        verify_public_report_contract_for_report(
            REPORT_FIXTURE,
            "invalid",
        )


def test_report_contract_verification_uses_report_schema_version(
        monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, str] = {}

    def fake_verify(schema_version: str, fingerprint: str) -> bool:
        captured["schema_version"] = schema_version
        captured["fingerprint"] = fingerprint
        return True

    monkeypatch.setattr(
        "src.report_contract_verification."
        "verify_public_report_contract_fingerprint",
        fake_verify,
    )

    fingerprint = "sha256:" + "0" * 64

    assert verify_public_report_contract_for_report(
        REPORT_FIXTURE,
        fingerprint,
    ) is True

    assert captured == {
        "schema_version": "1.0",
        "fingerprint": fingerprint,
    }


def test_invalid_report_is_rejected_before_contract_verification(
        tmp_path: Path,
) -> None:
    invalid_report = tmp_path / "invalid-report.json"
    invalid_report.write_text(
        '{"schema_version": "1.0"}',
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        verify_public_report_contract_for_report(
            invalid_report,
            "sha256:" + "0" * 64,
        )
