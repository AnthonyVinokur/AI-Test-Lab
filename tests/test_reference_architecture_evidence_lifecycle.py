from __future__ import annotations

import base64
import json
from dataclasses import FrozenInstanceError, asdict, replace
from datetime import datetime, timedelta, timezone

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from src.reference_architecture_evidence_lifecycle_authority import (
    LifecycleAuthorityError,
    LifecycleAuthorityGrant,
    verify_lifecycle_authority,
)
from src.reference_architecture_evidence_lifecycle_chain import (
    AuthenticatedLifecycleEvent,
    LifecycleChainError,
    LifecycleEventProof,
    histories_are_consistent,
    verify_lifecycle_chain,
)
from src.reference_architecture_evidence_lifecycle_contract import (
    LifecycleEventType,
    LifecycleReasonCategory,
    LifecycleStatus,
)
from src.reference_architecture_evidence_lifecycle_freshness import (
    build_status_snapshot,
    verify_status_freshness,
)
from src.reference_architecture_evidence_lifecycle_outcome import (
    PublicLifecycleOutcome,
    public_lifecycle_result,
)
from src.reference_architecture_evidence_lifecycle_resolution import (
    lifecycle_status_contract,
    resolve_lifecycle_status,
)
from src.reference_architecture_evidence_lifecycle_serialization import (
    LifecycleDocumentError,
    build_lifecycle_event,
    serialize_lifecycle_event,
    translate_untrusted_lifecycle_event,
)
from src.reference_architecture_evidence_lifecycle_verification import LifecycleVerification


NOW = datetime(2026, 9, 15, 22, 0, tzinfo=timezone.utc)
RECEIPT = "1" * 64
MANIFEST = "2" * 64
PACKAGE = "3" * 64
REPLACEMENT_RECEIPT = "4" * 64
REPLACEMENT_PACKAGE = "5" * 64
PRIVATE_KEY = Ed25519PrivateKey.generate()


def event(event_type=LifecycleEventType.ISSUED, *, previous=None, at=NOW, **changes):
    values = dict(
        receipt_id=RECEIPT,
        release_manifest_digest=MANIFEST,
        evidence_package_id=PACKAGE,
        event_type=event_type,
        effective_at=at,
        issuer_id="lifecycle-issuer",
        authority_id="authority-1",
        environment="audit",
        reason_category=LifecycleReasonCategory.RELEASE_ISSUED,
        previous_event_id=previous,
        replacement_receipt_id=None,
        replacement_package_id=None,
    )
    if event_type is LifecycleEventType.SUPERSEDED:
        values.update(replacement_receipt_id=REPLACEMENT_RECEIPT,
                      replacement_package_id=REPLACEMENT_PACKAGE,
                      reason_category=LifecycleReasonCategory.REPLACEMENT_AVAILABLE)
    values.update(changes)
    return build_lifecycle_event(**values)


def grant(**changes):
    values = dict(
        authority_id="authority-1",
        issuer_id="lifecycle-issuer",
        key_id="key-1",
        receipt_id=RECEIPT,
        evidence_package_id=PACKAGE,
        environment="audit",
        permitted_event_types=frozenset(LifecycleEventType),
        valid_from=NOW - timedelta(days=1),
        valid_until=NOW + timedelta(days=2),
    )
    values.update(changes)
    return LifecycleAuthorityGrant(**values)


def authenticated(value):
    signature = PRIVATE_KEY.sign(value.event_digest.encode("ascii"))
    return AuthenticatedLifecycleEvent(value, LifecycleEventProof("key-1", base64.b64encode(signature).decode("ascii")))


def resolver(_authority_id):
    return grant()


def signature_verifier(value, proof):
    try:
        PRIVATE_KEY.public_key().verify(base64.b64decode(proof.signature_base64), value.event_digest.encode("ascii"))
        return True
    except Exception:
        return False


def history(*types):
    result = []
    previous = None
    for index, event_type in enumerate(types):
        built = event(event_type, previous=previous, at=NOW + timedelta(minutes=index))
        result.append(authenticated(built))
        previous = built.event_digest
    return tuple(result)


def test_contracts_are_frozen_strict_and_canonical():
    issued = event()
    with pytest.raises(FrozenInstanceError):
        issued.issuer_id = "attacker"  # type: ignore[misc]
    first = serialize_lifecycle_event(issued)
    assert translate_untrusted_lifecycle_event(first) == issued
    document = json.loads(first)
    reordered = {key: document[key] for key in reversed(document)}
    assert translate_untrusted_lifecycle_event(reordered) == issued
    with pytest.raises(LifecycleDocumentError):
        translate_untrusted_lifecycle_event(json.dumps(document, indent=2))
    document["unknown"] = "fail-closed"
    with pytest.raises(LifecycleDocumentError):
        translate_untrusted_lifecycle_event(document)


@pytest.mark.parametrize("changes", [
    {"issuer_id": "attacker"}, {"environment": "production"},
    {"receipt_id": "9" * 64}, {"evidence_package_id": "8" * 64},
    {"event_type": LifecycleEventType.REVOKED},
])
def test_authority_is_bound_to_exact_actor_scope_context_and_event(changes):
    issued = event()
    authority = grant(permitted_event_types=frozenset({LifecycleEventType.ISSUED}))
    changed = build_lifecycle_event(**{**{k: v for k, v in asdict(issued).items() if k != "event_digest"}, **changes})
    with pytest.raises(LifecycleAuthorityError):
        verify_lifecycle_authority(changed, authority)


def test_chain_detects_forgery_removal_reordering_and_substitution():
    values = history(LifecycleEventType.ISSUED, LifecycleEventType.SUSPENDED, LifecycleEventType.REVOKED)
    assert len(verify_lifecycle_chain(values, authority_resolver=resolver, signature_verifier=signature_verifier)) == 3
    attacks = [
        (values[0], values[2]),
        (values[1], values[0], values[2]),
        (values[0], replace(values[1], proof=LifecycleEventProof("key-1", base64.b64encode(b"x" * 64).decode()))),
    ]
    for attack in attacks:
        with pytest.raises(LifecycleChainError):
            verify_lifecycle_chain(attack, authority_resolver=resolver, signature_verifier=signature_verifier)


def test_status_resolution_supports_history_and_rejects_invalid_transitions():
    values = [item.event for item in history(LifecycleEventType.ISSUED, LifecycleEventType.SUSPENDED,
                                              LifecycleEventType.REINSTATED, LifecycleEventType.REVOKED)]
    assert resolve_lifecycle_status(values, observed_at=NOW + timedelta(seconds=1)).status is LifecycleStatus.ACTIVE
    assert resolve_lifecycle_status(values, observed_at=NOW + timedelta(minutes=1)).status is LifecycleStatus.SUSPENDED
    assert resolve_lifecycle_status(values, observed_at=NOW + timedelta(minutes=3)).status is LifecycleStatus.REVOKED
    invalid = (*values, event(LifecycleEventType.REINSTATED, previous=values[-1].event_digest,
                              at=NOW + timedelta(minutes=4)))
    result = resolve_lifecycle_status(invalid, observed_at=NOW + timedelta(minutes=5))
    assert not result.trustworthy and result.status is LifecycleStatus.UNKNOWN


def test_same_time_conflicts_and_diverging_supersession_histories_fail_closed():
    issued = event()
    suspended = event(LifecycleEventType.SUSPENDED, previous=issued.event_digest, at=NOW)
    assert not resolve_lifecycle_status((issued, suspended), observed_at=NOW).trustworthy
    left = (issued, event(LifecycleEventType.SUPERSEDED, previous=issued.event_digest, at=NOW + timedelta(minutes=1)))
    right = (issued, event(LifecycleEventType.REVOKED, previous=issued.event_digest, at=NOW + timedelta(minutes=1)))
    assert not histories_are_consistent(left, right)


def test_freshness_rejects_active_replay_rollback_context_and_time_manipulation():
    events = [item.event for item in history(LifecycleEventType.ISSUED, LifecycleEventType.REVOKED)]
    old_resolution = resolve_lifecycle_status(events, observed_at=NOW)
    old_status = lifecycle_status_contract(old_resolution)
    old_snapshot = build_status_snapshot(old_status, environment="audit", chain_length=1,
                                         chain_head_id=events[0].event_digest)
    assert verify_status_freshness(old_snapshot, events, expected_environment="audit", observed_at=NOW)
    assert not verify_status_freshness(old_snapshot, events, expected_environment="audit",
                                       observed_at=NOW + timedelta(minutes=1))
    assert not verify_status_freshness(old_snapshot, events, expected_environment="production", observed_at=NOW)


@pytest.mark.parametrize(("status", "outcome"), [
    (LifecycleStatus.ACTIVE, PublicLifecycleOutcome.VALID),
    (LifecycleStatus.SUSPENDED, PublicLifecycleOutcome.TEMPORARILY_UNAVAILABLE),
    (LifecycleStatus.REVOKED, PublicLifecycleOutcome.NO_LONGER_VALID),
    (LifecycleStatus.EXPIRED, PublicLifecycleOutcome.EXPIRED),
    (LifecycleStatus.SUPERSEDED, PublicLifecycleOutcome.REPLACED),
])
def test_public_outcomes_are_stable_and_do_not_leak_protected_details(status, outcome):
    issued = event()
    resolution = resolve_lifecycle_status((issued,), observed_at=NOW)
    contract = replace(lifecycle_status_contract(resolution), status=status)
    result = public_lifecycle_result(LifecycleVerification(True, status, contract, "private-policy-path"))
    assert result.outcome is outcome
    serialized = json.dumps(asdict(result))
    assert "private-policy-path" not in serialized
    assert "issuer_id" not in serialized and "authority_id" not in serialized and "key_id" not in serialized


def test_unknown_versions_algorithms_and_unverified_results_fail_closed():
    issued = event()
    document = json.loads(serialize_lifecycle_event(issued))
    for field, value in (("contract_version", "2.0"), ("digest_algorithm", "sha512"),
                         ("serialization_algorithm", "pickle")):
        changed = dict(document); changed[field] = value
        with pytest.raises(LifecycleDocumentError):
            translate_untrusted_lifecycle_event(changed)
    result = public_lifecycle_result(LifecycleVerification(False, LifecycleStatus.UNKNOWN, None, "secret"))
    assert result.outcome is PublicLifecycleOutcome.UNVERIFIABLE
    assert result.receipt_id is None and result.reason_category == "lifecycle_unverifiable"
