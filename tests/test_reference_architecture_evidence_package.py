from __future__ import annotations

import json
from dataclasses import replace
from datetime import datetime, timezone

import pytest

from src.reference_architecture_evidence_ledger import InMemoryEvidenceLedger
from src.reference_architecture_evidence_ledger_contract import EvidenceLedgerAppendRequest
from src.reference_architecture_evidence_package_builder import build_evidence_package
from src.reference_architecture_evidence_package_contract import (
    PackageReasonCode, PackageVerificationRequest,
)
from src.reference_architecture_evidence_package_serialization import serialize_evidence_package
from src.reference_architecture_evidence_package_translation import (
    EvidencePackageTranslationError, translate_untrusted_evidence_package_request,
)
from src.reference_architecture_evidence_package_verification import verify_evidence_package


def ledger_with_three_entries() -> tuple[InMemoryEvidenceLedger, str, tuple[str, ...]]:
    ledger = InMemoryEvidenceLedger()
    previous = None
    ids = []
    ledger_id = ""
    for sequence in range(1, 4):
        result = ledger.append(EvidenceLedgerAppendRequest(
            evidence_sha256=f"{sequence:064x}", evidence_type="evaluation-report", producer_id="test-runner",
            evaluation_run_id="run-1" if sequence < 3 else "run-2",
            admission_decision_id=f"admission-{sequence}", provenance_reference=f"provenance-{sequence}",
            evidence_contract_version="1.0", admission_contract_version="1.0",
            ledger_contract_version="1.0", policy_version="policy-1",
            recorded_at=datetime(2026, 9, sequence, tzinfo=timezone.utc), supersedes_entry_id=previous,
        ))
        assert result.entry is not None
        previous = result.entry.entry_id
        ledger_id = result.entry.chain_id
        ids.append(result.entry.entry_id)
    return ledger, ledger_id, tuple(ids)


def build(**overrides):
    ledger, ledger_id, ids = ledger_with_three_entries()
    payload = {"ledger_id": ledger_id}
    payload.update(overrides)
    result = build_evidence_package(payload, ledger=ledger)
    return result, ledger, ledger_id, ids


def test_translates_untrusted_request_into_separate_frozen_command() -> None:
    payload = {"ledger_id": "a" * 64, "evidence_ids": ["b" * 64], "metadata": {"case": "audit"}}
    request = translate_untrusted_evidence_package_request(payload)
    payload["evidence_ids"].append("c" * 64)
    assert request.evidence_ids == ("b" * 64,)
    assert request.metadata == {"case": "audit"}


@pytest.mark.parametrize("payload", [{}, {"ledger_id": "bad"}, {"ledger_id": "a" * 64, "unknown": 1},
                                      {"ledger_id": "a" * 64, "evidence_ids": "bad"}])
def test_rejects_malformed_external_requests(payload) -> None:
    with pytest.raises(EvidencePackageTranslationError):
        translate_untrusted_evidence_package_request(payload)


def test_builds_deterministic_public_package_and_verifies_offline() -> None:
    first, ledger, ledger_id, _ = build(metadata={"purpose": "external-audit"})
    second = build_evidence_package({"ledger_id": ledger_id, "metadata": {"purpose": "external-audit"}}, ledger=ledger)
    assert first.built and second.built
    assert serialize_evidence_package(first.package) == serialize_evidence_package(second.package)
    verification = verify_evidence_package(PackageVerificationRequest(serialize_evidence_package(first.package)))
    assert verification.verified
    assert first.package.manifest.entry_count == 3
    assert not hasattr(first.package.records[0], "_seal")


def test_rejects_unknown_ledger_and_unsupported_version() -> None:
    ledger, _, _ = ledger_with_three_entries()
    missing = build_evidence_package({"ledger_id": "f" * 64}, ledger=ledger)
    unsupported = build_evidence_package({"ledger_id": "f" * 64, "format_version": "2.0"}, ledger=ledger)
    assert missing.reason_code is PackageReasonCode.LEDGER_NOT_FOUND
    assert unsupported.reason_code is PackageReasonCode.UNSUPPORTED_PACKAGE_VERSION


def test_rejects_missing_duplicate_empty_and_incomplete_selections() -> None:
    result, ledger, ledger_id, ids = build()
    missing = build_evidence_package({"ledger_id": ledger_id, "evidence_ids": ["f" * 64]}, ledger=ledger)
    duplicate = build_evidence_package({"ledger_id": ledger_id, "evidence_ids": [ids[0], ids[0]]}, ledger=ledger)
    empty = build_evidence_package({"ledger_id": ledger_id, "run_id": "missing-run"}, ledger=ledger)
    incomplete = build_evidence_package({"ledger_id": ledger_id, "evidence_ids": [ids[1]]}, ledger=ledger)
    assert missing.reason_code is PackageReasonCode.EVIDENCE_NOT_FOUND
    assert duplicate.reason_code is PackageReasonCode.DUPLICATE_EVIDENCE_REFERENCE
    assert empty.reason_code is PackageReasonCode.EMPTY_SELECTION
    assert incomplete.reason_code is PackageReasonCode.PACKAGE_INCOMPLETE


def test_authorization_boundary_fails_closed() -> None:
    ledger, ledger_id, _ = ledger_with_three_entries()
    result = build_evidence_package({"ledger_id": ledger_id}, ledger=ledger, authorize=lambda request, records: False)
    assert result.reason_code is PackageReasonCode.UNAUTHORIZED_SELECTION


def tampered_document(field: str, value):
    result, _, _, _ = build()
    document = json.loads(serialize_evidence_package(result.package))
    document["records"][1][field] = value
    # Canonicalize the attacker document so failure is about its content, not whitespace.
    return json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


@pytest.mark.parametrize(("field", "value", "reason"), [
    ("evidence_digest", "f" * 64, PackageReasonCode.EVIDENCE_DIGEST_MISMATCH),
    ("run_id", "substituted-run", PackageReasonCode.EVIDENCE_DIGEST_MISMATCH),
    ("admission_reference", "substituted-admission", PackageReasonCode.EVIDENCE_DIGEST_MISMATCH),
    ("previous_entry_digest", "f" * 64, PackageReasonCode.EVIDENCE_DIGEST_MISMATCH),
])
def test_detects_record_tampering_before_trusting_bindings(field, value, reason) -> None:
    verification = verify_evidence_package(PackageVerificationRequest(tampered_document(field, value)))
    assert verification.reason_code is reason


def test_detects_omission_insertion_and_reordering() -> None:
    result, _, _, _ = build()
    base = json.loads(serialize_evidence_package(result.package))
    variants = []
    omitted = json.loads(json.dumps(base)); omitted["records"].pop(1); variants.append(omitted)
    inserted = json.loads(json.dumps(base)); inserted["records"].append(inserted["records"][-1]); variants.append(inserted)
    reordered = json.loads(json.dumps(base)); reordered["records"].reverse(); variants.append(reordered)
    for value in variants:
        raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
        assert not verify_evidence_package(PackageVerificationRequest(raw)).verified


def test_rejects_noncanonical_json_even_when_values_are_unchanged() -> None:
    result, _, _, _ = build()
    pretty = json.dumps(json.loads(serialize_evidence_package(result.package)), indent=2).encode()
    assert verify_evidence_package(PackageVerificationRequest(pretty)).reason_code is PackageReasonCode.MANIFEST_MISMATCH


def test_detects_package_digest_substitution() -> None:
    result, _, _, _ = build()
    document = json.loads(serialize_evidence_package(result.package))
    document["package_digest"] = "f" * 64
    raw = json.dumps(document, sort_keys=True, separators=(",", ":")).encode()
    outcome = verify_evidence_package(PackageVerificationRequest(raw))
    assert outcome.reason_code is PackageReasonCode.PACKAGE_DIGEST_MISMATCH


def test_verifier_normalizes_malformed_input_without_exception_details() -> None:
    outcome = verify_evidence_package(PackageVerificationRequest(b"not-json"))
    assert outcome.reason_code is PackageReasonCode.MALFORMED_REQUEST
    assert outcome.diagnostic is None
