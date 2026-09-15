from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone

import pytest

from src.reference_architecture_evidence_consumption import consume_evidence_package
from src.reference_architecture_evidence_consumption_contract import (
    ConsumptionReasonCode, ConsumptionStatus, EvidenceConsumptionPolicy, EvidenceDisclosurePurpose,
    EvidenceHold, EvidenceLifecycleRecord, EvidenceLifecycleState, RequesterAccessScope,
)
from src.reference_architecture_evidence_consumption_policy import (
    InMemoryConsumptionPolicyRepository, InMemoryHoldRepository, InMemoryLifecycleRepository,
    InMemoryRequesterResolver,
)
from src.reference_architecture_evidence_consumption_translation import (
    EvidenceConsumptionTranslationError, translate_untrusted_evidence_consumption_request,
)
from src.reference_architecture_evidence_ledger import InMemoryEvidenceLedger
from src.reference_architecture_evidence_ledger_contract import EvidenceLedgerAppendRequest
from src.reference_architecture_evidence_package_serialization import serialize_evidence_package
from src.reference_architecture_evidence_package_verification import verify_evidence_package
from src.reference_architecture_evidence_package_contract import PackageVerificationRequest


NOW = datetime(2026, 9, 15, 20, 15, tzinfo=timezone.utc)
PURPOSES = frozenset({EvidenceDisclosurePurpose.INTERNAL_DEBUGGING, EvidenceDisclosurePurpose.EXTERNAL_AUDIT,
                      EvidenceDisclosurePurpose.INCIDENT_INVESTIGATION})


def ledger_fixture(recorded_at: datetime | None = None):
    ledger = InMemoryEvidenceLedger(); previous = None; entries = []
    for number in range(1, 4):
        result = ledger.append(EvidenceLedgerAppendRequest(
            evidence_sha256=f"{number:064x}", evidence_type="evaluation-report", producer_id="runner-1",
            evaluation_run_id="run-1" if number < 3 else "run-2", admission_decision_id=f"admission-{number}",
            provenance_reference=f"provenance-{number}", evidence_contract_version="1.0",
            admission_contract_version="1.0", ledger_contract_version="1.0", policy_version="admission-1",
            recorded_at=(recorded_at or NOW - timedelta(days=1)) + timedelta(seconds=number),
            supersedes_entry_id=previous))
        assert result.entry is not None; previous = result.entry.entry_id; entries.append(result.entry)
    return ledger, tuple(entries)


def policy(**changes):
    value = EvidenceConsumptionPolicy("export-policy", "1.0", NOW - timedelta(days=30), NOW + timedelta(days=30),
        PURPOSES, frozenset({"ci", "external-audit"}), frozenset({"evaluation-report"}),
        {"evaluation-report": timedelta(days=7)})
    return replace(value, **changes)


def scope(ledger_id: str, **changes):
    value = RequesterAccessScope("consumer-1", "service-account", "tenant-1", True, True, PURPOSES,
        frozenset({"ci", "external-audit"}), frozenset({ledger_id}), frozenset({"run-1", "run-2"}),
        frozenset({"evaluation-report"}))
    return replace(value, **changes)


def payload(ledger_id: str, **changes):
    value = {"requester_id": "consumer-1", "requester_type": "service-account", "tenant_id": "tenant-1",
        "ledger_id": ledger_id, "purpose": "external_audit", "target_environment": "external-audit",
        "policy_id": "export-policy", "policy_version": "1.0"}
    value.update(changes); return value


def run(*, payload_changes=None, scopes=None, policies=None, lifecycle=(), holds=(), recorded_at=None, clock=lambda: NOW):
    ledger, entries = ledger_fixture(recorded_at)
    request = payload(entries[0].chain_id, **(payload_changes or {}))
    result = consume_evidence_package(request, ledger=ledger,
        requester_resolver=InMemoryRequesterResolver(scopes if scopes is not None else (scope(entries[0].chain_id),)),
        policy_repository=InMemoryConsumptionPolicyRepository(policies if policies is not None else (policy(),)),
        lifecycle_repository=InMemoryLifecycleRepository(lifecycle), hold_repository=InMemoryHoldRepository(holds), clock=clock)
    return result, ledger, entries


def test_strict_translation_copies_untrusted_data_and_contract_is_frozen() -> None:
    ledger, entries = ledger_fixture(); external = payload(entries[0].chain_id, evidence_ids=[entries[0].entry_id],
                                                               authorization_context={"grant": "safe-reference"})
    request = translate_untrusted_evidence_consumption_request(external)
    external["evidence_ids"].append(entries[1].entry_id); external["authorization_context"]["secret"] = "credential"
    assert request.evidence_ids == (entries[0].entry_id,)
    assert dict(request.authorization_context) == {"grant": "safe-reference"}
    with pytest.raises(FrozenInstanceError): request.requester_id = "attacker"  # type: ignore[misc]


@pytest.mark.parametrize("bad", [{}, {"unknown": "field"}, {"requester_id": ""},
    {"purpose": "unknown"}, {"evidence_ids": "not-a-list"}, {"authorization_context": {str(x): "x" for x in range(17)}}])
def test_malformed_requests_fail_before_any_port_access(bad) -> None:
    base = payload("a" * 64); base.update(bad)
    if bad == {}: base = {}
    with pytest.raises(EvidenceConsumptionTranslationError): translate_untrusted_evidence_consumption_request(base)


def test_authorized_export_builds_verifiable_a07_package_deterministically() -> None:
    first, _, _ = run(); second, _, _ = run()
    assert (first.status, first.reason_code) == (ConsumptionStatus.AUTHORIZED, ConsumptionReasonCode.CONSUMPTION_AUTHORIZED)
    assert serialize_evidence_package(first.package) == serialize_evidence_package(second.package)
    assert verify_evidence_package(PackageVerificationRequest(serialize_evidence_package(first.package))).verified
    assert first.diagnostic is None and first.policy_reference == "export-policy:1.0"


@pytest.mark.parametrize(("scopes", "reason"), [
    ((), ConsumptionReasonCode.REQUESTER_NOT_FOUND),
    (None, ConsumptionReasonCode.REQUESTER_DISABLED),
])
def test_unknown_and_disabled_requesters_fail_closed(scopes, reason) -> None:
    ledger, entries = ledger_fixture()
    selected = scopes if scopes is not None else (scope(entries[0].chain_id, enabled=False),)
    result = consume_evidence_package(payload(entries[0].chain_id), ledger=ledger,
        requester_resolver=InMemoryRequesterResolver(selected), policy_repository=InMemoryConsumptionPolicyRepository((policy(),)),
        lifecycle_repository=InMemoryLifecycleRepository(), hold_repository=InMemoryHoldRepository(), clock=lambda: NOW)
    assert result.reason_code is reason and result.package is None


def test_ambiguous_identity_tenant_and_run_substitution_are_denied() -> None:
    ledger, entries = ledger_fixture(); good = scope(entries[0].chain_id)
    common = dict(ledger=ledger, policy_repository=InMemoryConsumptionPolicyRepository((policy(),)),
        lifecycle_repository=InMemoryLifecycleRepository(), hold_repository=InMemoryHoldRepository(), clock=lambda: NOW)
    ambiguous = consume_evidence_package(payload(entries[0].chain_id), requester_resolver=InMemoryRequesterResolver((good, good)), **common)
    tenant = consume_evidence_package(payload(entries[0].chain_id, tenant_id="tenant-2"), requester_resolver=InMemoryRequesterResolver((good,)), **common)
    run = consume_evidence_package(payload(entries[0].chain_id, run_id="run-3"), requester_resolver=InMemoryRequesterResolver((good,)), **common)
    assert ambiguous.reason_code is ConsumptionReasonCode.AMBIGUOUS_REQUESTER
    assert tenant.reason_code is ConsumptionReasonCode.TENANT_SCOPE_MISMATCH
    assert run.reason_code is ConsumptionReasonCode.RUN_SCOPE_MISMATCH


def test_purpose_environment_and_export_permission_are_independent() -> None:
    for changes, expected in [({"purpose": "regulatory_review"}, ConsumptionReasonCode.PURPOSE_NOT_ALLOWED),
                              ({"target_environment": "production"}, ConsumptionReasonCode.ENVIRONMENT_NOT_ALLOWED)]:
        assert run(payload_changes=changes)[0].reason_code is expected
    ledger, entries = ledger_fixture()
    result = consume_evidence_package(payload(entries[0].chain_id), ledger=ledger,
        requester_resolver=InMemoryRequesterResolver((scope(entries[0].chain_id, may_export=False),)),
        policy_repository=InMemoryConsumptionPolicyRepository((policy(),)), lifecycle_repository=InMemoryLifecycleRepository(),
        hold_repository=InMemoryHoldRepository(), clock=lambda: NOW)
    assert result.reason_code is ConsumptionReasonCode.DISCLOSURE_NOT_ALLOWED


def test_policy_lifecycle_and_version_failures_are_stable() -> None:
    assert run(policies=())[0].reason_code is ConsumptionReasonCode.POLICY_NOT_FOUND
    assert run(payload_changes={"policy_version": "2.0"})[0].reason_code is ConsumptionReasonCode.UNSUPPORTED_POLICY_VERSION
    assert run(policies=(policy(effective_at=NOW + timedelta(seconds=1), expires_at=NOW + timedelta(days=1)),))[0].reason_code is ConsumptionReasonCode.POLICY_NOT_ACTIVE


@pytest.mark.parametrize(("state", "reason"), [
    (EvidenceLifecycleState.RESTRICTED, ConsumptionReasonCode.EVIDENCE_TYPE_RESTRICTED),
    (EvidenceLifecycleState.EXPIRED, ConsumptionReasonCode.EVIDENCE_EXPIRED),
    (EvidenceLifecycleState.RETIRED, ConsumptionReasonCode.EVIDENCE_RETIRED),
    (EvidenceLifecycleState.REVOKED, ConsumptionReasonCode.EVIDENCE_REVOKED),
])
def test_lifecycle_states_deny_without_rewriting_ledger(state, reason) -> None:
    ledger, entries = ledger_fixture(); before = ledger.chain(entries[0].chain_id)
    result = consume_evidence_package(payload(entries[0].chain_id), ledger=ledger,
        requester_resolver=InMemoryRequesterResolver((scope(entries[0].chain_id),)),
        policy_repository=InMemoryConsumptionPolicyRepository((policy(),)),
        lifecycle_repository=InMemoryLifecycleRepository((EvidenceLifecycleRecord(entries[1].entry_id, state),)),
        hold_repository=InMemoryHoldRepository(), clock=lambda: NOW)
    assert result.reason_code is reason and ledger.chain(entries[0].chain_id) == before


def test_retention_boundary_uses_one_explicit_trusted_time() -> None:
    assert run(recorded_at=NOW - timedelta(days=7) - timedelta(seconds=3))[0].reason_code is ConsumptionReasonCode.EVIDENCE_EXPIRED
    calls = []
    def one_clock(): calls.append(1); return NOW
    assert run(clock=one_clock)[0].authorized and len(calls) == 1


def test_hold_precedence_blocks_normal_export_but_preserves_authorized_investigation() -> None:
    ledger, entries = ledger_fixture(recorded_at=NOW - timedelta(days=30))
    hold = EvidenceHold("hold-1", "tenant-1", "legal", NOW - timedelta(days=1), None, "authority-1", "1.0",
                        run_ids=frozenset({"run-1", "run-2"}))
    common = dict(ledger=ledger, requester_resolver=InMemoryRequesterResolver((scope(entries[0].chain_id),)),
        policy_repository=InMemoryConsumptionPolicyRepository((policy(),)), lifecycle_repository=InMemoryLifecycleRepository(),
        hold_repository=InMemoryHoldRepository((hold,)), clock=lambda: NOW)
    blocked = consume_evidence_package(payload(entries[0].chain_id), **common)
    allowed = consume_evidence_package(payload(entries[0].chain_id, purpose="incident_investigation", target_environment="ci"), **common)
    assert blocked.reason_code is ConsumptionReasonCode.EVIDENCE_ON_HOLD
    assert allowed.authorized


def test_incomplete_cryptographic_selection_is_denied_not_redacted() -> None:
    ledger, entries = ledger_fixture()
    result = consume_evidence_package(payload(entries[0].chain_id, evidence_ids=[entries[1].entry_id]), ledger=ledger,
        requester_resolver=InMemoryRequesterResolver((scope(entries[0].chain_id),)),
        policy_repository=InMemoryConsumptionPolicyRepository((policy(),)), lifecycle_repository=InMemoryLifecycleRepository(),
        hold_repository=InMemoryHoldRepository(), clock=lambda: NOW)
    assert result.reason_code is ConsumptionReasonCode.PACKAGE_SELECTION_INCOMPLETE and result.package is None


def test_internal_errors_are_normalized_without_diagnostics_or_policy_details() -> None:
    class BrokenResolver:
        def resolve(self, *_): raise RuntimeError("secret role and storage path")
    ledger, entries = ledger_fixture()
    result = consume_evidence_package(payload(entries[0].chain_id), ledger=ledger, requester_resolver=BrokenResolver(),
        policy_repository=InMemoryConsumptionPolicyRepository((policy(),)), lifecycle_repository=InMemoryLifecycleRepository(),
        hold_repository=InMemoryHoldRepository(), clock=lambda: NOW)
    assert (result.status, result.reason_code, result.diagnostic, result.package) == (
        ConsumptionStatus.ERROR, ConsumptionReasonCode.INTERNAL_CONSUMPTION_ERROR, None, None)
    assert not hasattr(result, "policy_rules") and not hasattr(result, "authorization_context")
