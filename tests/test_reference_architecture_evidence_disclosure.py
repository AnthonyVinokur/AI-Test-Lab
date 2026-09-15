from __future__ import annotations

from dataclasses import FrozenInstanceError, asdict, replace
from datetime import datetime, timedelta, timezone
import json

import pytest

from src.reference_architecture_evidence_disclosure import InMemoryDisclosureReplayRegistry, disclose_evidence
from src.reference_architecture_evidence_disclosure_contract import (
    DisclosureAuthorization, DisclosureDecision, DisclosureReasonCode,
)
from src.reference_architecture_evidence_disclosure_serialization import serialize_disclosure_release
from src.reference_architecture_evidence_disclosure_translation import (
    DisclosureTranslationError, translate_untrusted_disclosure_request,
)
from src.reference_architecture_evidence_disclosure_verification import verify_disclosure_release
from src.reference_architecture_evidence_ledger import InMemoryEvidenceLedger
from src.reference_architecture_evidence_ledger_contract import EvidenceLedgerAppendRequest
from src.reference_architecture_evidence_package_builder import build_evidence_package


NOW = datetime(2026, 9, 15, 22, 0, tzinfo=timezone.utc)


def package_fixture():
    ledger = InMemoryEvidenceLedger(); previous = None; entries = []
    for number in range(1, 3):
        result = ledger.append(EvidenceLedgerAppendRequest(
            evidence_sha256=f"{number:064x}", evidence_type="evaluation-report", producer_id="runner-1",
            evaluation_run_id="run-1", admission_decision_id=f"admission-{number}",
            provenance_reference=f"provenance-{number}", evidence_contract_version="1.0",
            admission_contract_version="1.0", ledger_contract_version="1.0", policy_version="private-policy-7",
            recorded_at=NOW - timedelta(days=1) + timedelta(seconds=number), supersedes_entry_id=previous))
        assert result.entry is not None; previous = result.entry.entry_id; entries.append(result.entry)
    built = build_evidence_package({"ledger_id": entries[0].chain_id}, ledger=ledger,
                                   authorize=lambda _request, _records: True)
    assert built.package is not None
    return built.package


def payload(package, **changes):
    value = {"request_id": "request-1", "requester_id": "requester-1", "recipient_id": "auditor-1",
        "purpose": "external_audit", "environment": "audit", "package": package,
        "requested_record_ids": [r.evidence_id for r in package.records],
        "requested_fields": ["evidence_id", "evidence_digest", "evidence_type", "recorded_at"],
        "output_format": "json", "authorization_id": "auth-1", "requested_at": NOW}
    value.update(changes); return value


def authorization(package, **changes):
    value = DisclosureAuthorization("auth-1", "decision-1", True, "requester-1", "auditor-1",
        package.manifest.package_id, package.package_digest, "external_audit", "audit",
        frozenset(r.evidence_id for r in package.records),
        frozenset({"evidence_id", "evidence_digest", "evidence_type", "recorded_at"}),
        NOW - timedelta(minutes=1), NOW + timedelta(minutes=5))
    return replace(value, **changes)


def execute(package=None, *, payload_changes=None, auth_changes=None, **kwargs):
    package = package or package_fixture()
    request = translate_untrusted_disclosure_request(payload(package, **(payload_changes or {})))
    return disclose_evidence(request, authorization(package, **(auth_changes or {})), **kwargs)


def test_request_translation_is_strict_copied_and_frozen():
    package = package_fixture(); external = payload(package)
    request = translate_untrusted_disclosure_request(external)
    external["requested_fields"].append("policy_version")
    assert "policy_version" not in request.requested_fields
    with pytest.raises(FrozenInstanceError): request.recipient_id = "attacker"  # type: ignore[misc]
    for bad in ({}, {**payload(package), "unknown": "x"}, {**payload(package), "requested_fields": "x"}):
        with pytest.raises(DisclosureTranslationError): translate_untrusted_disclosure_request(bad)


def test_valid_release_is_minimized_deterministic_and_independently_verifiable():
    first = execute(); second = execute()
    assert first.released and serialize_disclosure_release(first.release) == serialize_disclosure_release(second.release)
    assert verify_disclosure_release(serialize_disclosure_release(first.release)).verified
    document = json.loads(serialize_disclosure_release(first.release))
    assert set(dict(document["records"][0]["fields"])) == {"evidence_id", "evidence_digest", "evidence_type", "recorded_at"}
    serialized = serialize_disclosure_release(first.release).decode()
    assert "private-policy-7" not in serialized and "previous_entry_digest" not in serialized
    assert "does not certify correctness" in first.release.receipt.statement


@pytest.mark.parametrize("change", [
    {"requester_id": "attacker"}, {"recipient_id": "other"}, {"purpose": "customer_delivery"},
    {"environment": "production"}, {"authorization_id": "auth-2"},
])
def test_authorization_is_bound_to_requester_recipient_purpose_environment_and_reference(change):
    result = execute(payload_changes=change)
    assert (result.decision, result.reason_code) == (DisclosureDecision.AUTHORIZATION_MISMATCH,
                                                     DisclosureReasonCode.AUTHORIZATION_BINDING_MISMATCH)


def test_package_substitution_and_tampering_fail_integrity_or_binding():
    first, second = package_fixture(), package_fixture()
    # Produce a different valid package by changing its deterministic source timestamp.
    raw = asdict(second); raw["package_digest"] = "0" * 64
    request = translate_untrusted_disclosure_request(payload(first))
    mismatched = disclose_evidence(request, authorization(first, package_id="f" * 64))
    assert mismatched.reason_code is DisclosureReasonCode.AUTHORIZATION_BINDING_MISMATCH
    tampered = replace(first, package_digest="0" * 64)
    assert execute(tampered).reason_code is DisclosureReasonCode.PACKAGE_INTEGRITY_FAILURE


@pytest.mark.parametrize(("field", "reason"), [
    ("policy_version", DisclosureReasonCode.PROTECTED_FIELD_REQUESTED),
    ("internal_policy_rules", DisclosureReasonCode.PROTECTED_FIELD_REQUESTED),
    ("unknown_future_field", DisclosureReasonCode.SCOPE_EXCEEDED),
])
def test_unauthorized_protected_and_unknown_fields_fail_closed(field, reason):
    package = package_fixture()
    result = execute(package, payload_changes={"requested_fields": [field]},
                     auth_changes={"authorized_fields": frozenset({field})})
    assert result.decision is DisclosureDecision.SCOPE_EXCEEDED and result.reason_code is reason


def test_record_scope_escalation_denial_and_lifecycle_recheck():
    package = package_fixture(); one = package.records[0].evidence_id
    scope = execute(package, auth_changes={"authorized_record_ids": frozenset({one})})
    lifecycle = execute(package, lifecycle_allows=lambda _ids: False)
    assert scope.reason_code is DisclosureReasonCode.SCOPE_EXCEEDED
    assert lifecycle.reason_code is DisclosureReasonCode.LIFECYCLE_RESTRICTED


def test_denied_expired_revoked_and_one_time_authorizations_fail_closed():
    assert execute(auth_changes={"granted": False}).reason_code is DisclosureReasonCode.AUTHORIZATION_DENIED
    assert execute(auth_changes={"expires_at": NOW}).reason_code is DisclosureReasonCode.AUTHORIZATION_EXPIRED
    assert execute(auth_changes={"revoked": True}).reason_code is DisclosureReasonCode.AUTHORIZATION_REVOKED
    registry = InMemoryDisclosureReplayRegistry()
    first = execute(auth_changes={"one_time": True}, replay_registry=registry)
    replay = execute(auth_changes={"one_time": True}, replay_registry=registry)
    assert first.released and replay.reason_code is DisclosureReasonCode.REPLAY_DETECTED


def test_unknown_versions_and_missing_replay_store_fail_closed():
    assert execute(payload_changes={"contract_version": "2.0"}).reason_code is DisclosureReasonCode.UNSUPPORTED_VERSION
    assert execute(auth_changes={"one_time": True}).reason_code is DisclosureReasonCode.REPLAY_DETECTED


def test_manifest_content_and_receipt_tampering_are_detected():
    release = execute().release; assert release is not None
    document = json.loads(serialize_disclosure_release(release))
    variants = []
    for mutate in (
        lambda d: d["manifest"].__setitem__("recipient_id", "attacker"),
        lambda d: d["records"][0]["fields"][0].__setitem__(1, "tampered"),
        lambda d: d["receipt"].__setitem__("content_digest", "0" * 64),
    ):
        copy = json.loads(json.dumps(document)); mutate(copy); variants.append(copy)
    assert all(not verify_disclosure_release(value).verified for value in variants)


def test_noncanonical_bytes_and_unknown_algorithm_are_rejected():
    release = execute().release; assert release is not None
    pretty = json.dumps(json.loads(serialize_disclosure_release(release)), indent=2)
    assert not verify_disclosure_release(pretty).verified
    changed = replace(release.manifest, digest_algorithm="sha512")
    result = verify_disclosure_release(replace(release, manifest=changed))
    assert result.reason_code is DisclosureReasonCode.UNSUPPORTED_ALGORITHM


def test_internal_failures_expose_no_exception_or_policy_trace():
    result = execute(lifecycle_allows=lambda _ids: (_ for _ in ()).throw(RuntimeError("secret policy path")))
    assert (result.decision, result.reason_code, result.release) == (
        DisclosureDecision.INTERNAL_ERROR, DisclosureReasonCode.INTERNAL_DISCLOSURE_ERROR, None)
    assert not hasattr(result, "diagnostic") and not hasattr(result, "policy_rules")
