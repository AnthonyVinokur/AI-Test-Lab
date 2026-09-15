from __future__ import annotations

import json
from dataclasses import FrozenInstanceError, asdict, replace
from datetime import datetime, timedelta, timezone

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from src.reference_architecture_transparency_checkpoint import (
    TransparencyAuthorityGrant, TransparencyCheckpoint, build_checkpoint, checkpoint_id,
    verify_checkpoint,
)
from src.reference_architecture_transparency_consistency import (
    build_consistency_proof, checkpoints_equivocate, verify_consistency_proof,
)
from src.reference_architecture_transparency_contract import (
    TransparencyEntry, TransparencyOperation,
)
from src.reference_architecture_transparency_merkle import (
    InMemoryTransparencyStore, build_inclusion_proof, merkle_root,
    verify_inclusion_proof,
)
from src.reference_architecture_transparency_outcome import (
    PublicTransparencyDecision, public_transparency_outcome,
)
from src.reference_architecture_transparency_serialization import (
    TransparencyDocumentError, serialize_transparency_entry,
    translate_untrusted_transparency_entry, transparency_entry_digest,
)


NOW = datetime(2026, 9, 15, 22, 0, tzinfo=timezone.utc)
PRIVATE_KEY = Ed25519PrivateKey.generate()


def entry(index: int = 1, **changes: object) -> TransparencyEntry:
    values: dict[str, object] = dict(
        log_id="atl-transparency", receipt_id=f"{index:x}" * 64,
        release_manifest_id="2" * 64, evidence_package_id="3" * 64,
        lifecycle_event_id=f"{index + 3:x}" * 64,
        lifecycle_event_digest=f"{index + 4:x}" * 64,
        lifecycle_chain_head=f"{index + 5:x}" * 64, lifecycle_chain_length=index,
        environment="audit", recorded_at=NOW + timedelta(seconds=index),
    )
    values.update(changes)
    return TransparencyEntry(**values)  # type: ignore[arg-type]


def grant(**changes: object) -> TransparencyAuthorityGrant:
    values: dict[str, object] = dict(
        operator_id="operator-1", key_id="key-1", log_id="atl-transparency",
        environment="audit", allowed_operations=frozenset(TransparencyOperation),
        valid_from=NOW - timedelta(days=1), valid_until=NOW + timedelta(days=1),
    )
    values.update(changes)
    return TransparencyAuthorityGrant(**values)  # type: ignore[arg-type]


def checkpoint(entries: tuple[str, ...], *, previous: str | None = None,
               created_at: datetime = NOW, **changes: object) -> TransparencyCheckpoint:
    values: dict[str, object] = dict(
        log_id="atl-transparency", environment="audit", tree_size=len(entries),
        root_digest=merkle_root(entries), previous_checkpoint_id=previous,
        created_at=created_at, operator_id="operator-1", key_id="key-1",
    )
    values.update(changes)
    return build_checkpoint(signer=PRIVATE_KEY.sign, **values)  # type: ignore[arg-type]


def signature_verifier(payload: bytes, signature: bytes) -> bool:
    try:
        PRIVATE_KEY.public_key().verify(signature, payload)
        return True
    except Exception:
        return False


def test_entry_contract_is_immutable_exact_and_canonical():
    value = entry()
    with pytest.raises(FrozenInstanceError):
        value.environment = "production"  # type: ignore[misc]
    raw = serialize_transparency_entry(value)
    assert translate_untrusted_transparency_entry(raw) == value
    assert raw == serialize_transparency_entry(value)
    assert transparency_entry_digest(value) != transparency_entry_digest(replace(value, lifecycle_chain_length=2))


def test_translation_rejects_unknown_missing_malformed_and_noncanonical_documents():
    document = json.loads(serialize_transparency_entry(entry()))
    attacks = [
        {**document, "extra": "x"},
        {key: value for key, value in document.items() if key != "receipt_id"},
        {**document, "receipt_id": "not-a-digest"},
        {**document, "recorded_at": "2026-09-15T22:00:01+00:00"},
        {**document, "contract_version": "2.0"},
        {**document, "digest_algorithm": "sha512"},
    ]
    for attack in attacks:
        with pytest.raises(TransparencyDocumentError, match="document is invalid"):
            translate_untrusted_transparency_entry(attack)
    with pytest.raises(TransparencyDocumentError):
        translate_untrusted_transparency_entry(json.dumps(document, indent=2))


@pytest.mark.parametrize("changes", [
    {"operator_id": "attacker"}, {"key_id": "other-key"}, {"log_id": "other-log"},
    {"environment": "production"}, {"allowed_operations": frozenset({TransparencyOperation.APPEND})},
    {"valid_until": NOW},
])
def test_checkpoint_authority_binds_actor_key_log_environment_operation_and_time(changes):
    digests = (transparency_entry_digest(entry()),)
    assert not verify_checkpoint(checkpoint(digests), grant(**changes), entries=digests,
                                 observed_at=NOW, signature_verifier=signature_verifier)


def test_signed_checkpoint_binds_root_size_log_environment_and_explicit_time():
    digests = tuple(transparency_entry_digest(entry(i)) for i in range(1, 4))
    value = checkpoint(digests)
    assert verify_checkpoint(value, grant(), entries=digests, observed_at=NOW,
                             signature_verifier=signature_verifier)
    attacks = [replace(value, tree_size=2), replace(value, root_digest="9" * 64),
               replace(value, log_id="other-log"), replace(value, environment="production")]
    for attack in attacks:
        assert not verify_checkpoint(attack, grant(), entries=digests, observed_at=NOW,
                                     signature_verifier=signature_verifier)
    assert not verify_checkpoint(value, grant(), entries=digests,
                                 observed_at=NOW - timedelta(seconds=1),
                                 signature_verifier=signature_verifier)


def test_append_only_store_rejects_duplicates_and_root_detects_history_attacks():
    values = tuple(transparency_entry_digest(entry(i)) for i in range(1, 4))
    store = InMemoryTransparencyStore()
    for index, value in enumerate(values):
        assert store.append(value) == index
    with pytest.raises(ValueError, match="Duplicate"):
        store.append(values[0])
    root = merkle_root(store.entries())
    attacks = (values[:-1], (values[1], values[0], values[2]),
               (values[0], "9" * 64, values[2]), ("8" * 64,) + values)
    assert all(merkle_root(attack) != root for attack in attacks)


@pytest.mark.parametrize("size", [1, 2, 3, 4, 5, 8])
def test_inclusion_proofs_verify_for_balanced_and_unbalanced_trees(size):
    values = tuple(transparency_entry_digest(entry(i)) for i in range(1, size + 1))
    cp = checkpoint(values)
    for index, value in enumerate(values):
        proof = build_inclusion_proof(values, index, log_id=cp.log_id,
                                      environment=cp.environment, checkpoint_id=checkpoint_id(cp))
        assert verify_inclusion_proof(proof, expected_entry_digest=value,
                                      expected_checkpoint_id=checkpoint_id(cp),
                                      expected_log_id=cp.log_id, expected_environment=cp.environment,
                                      expected_root_digest=cp.root_digest,
                                      expected_tree_size=cp.tree_size)


def test_inclusion_proof_rejects_entry_position_path_size_checkpoint_and_context_attacks():
    values = tuple(transparency_entry_digest(entry(i)) for i in range(1, 5))
    cp = checkpoint(values)
    proof = build_inclusion_proof(values, 1, log_id=cp.log_id,
                                  environment=cp.environment, checkpoint_id=checkpoint_id(cp))
    attacks = [replace(proof, leaf_index=2), replace(proof, tree_size=3),
               replace(proof, proof_path=proof.proof_path[:-1]),
               replace(proof, proof_path=tuple(reversed(proof.proof_path))),
               replace(proof, proof_path=proof.proof_path + ("9" * 64,)),
               replace(proof, checkpoint_id="8" * 64), replace(proof, log_id="other-log"),
               replace(proof, environment="production")]
    assert all(not verify_inclusion_proof(x, expected_entry_digest=values[1],
                                          expected_checkpoint_id=checkpoint_id(cp),
                                          expected_log_id=cp.log_id,
                                          expected_environment=cp.environment,
                                          expected_root_digest=cp.root_digest,
                                          expected_tree_size=cp.tree_size) for x in attacks)


def test_consistency_proof_accepts_append_only_growth_and_same_tree():
    values = tuple(transparency_entry_digest(entry(i)) for i in range(1, 5))
    old = checkpoint(values[:2])
    new = checkpoint(values, previous=checkpoint_id(old), created_at=NOW + timedelta(seconds=1))
    proof = build_consistency_proof(old, new, values)
    assert verify_consistency_proof(proof, old, new)
    same = checkpoint(values[:2], previous=old.previous_checkpoint_id)
    assert verify_consistency_proof(build_consistency_proof(old, same, values[:2]), old, same)


def test_consistency_rejects_rollback_rewrite_unrelated_context_ancestry_and_path_attacks():
    values = tuple(transparency_entry_digest(entry(i)) for i in range(1, 5))
    old = checkpoint(values[:2])
    new = checkpoint(values, previous=checkpoint_id(old), created_at=NOW + timedelta(seconds=1))
    proof = build_consistency_proof(old, new, values)
    attacks = [replace(proof, history_digests=("9" * 64,) + values[1:]),
               replace(proof, history_digests=values[:-1]), replace(proof, log_id="other-log")]
    assert all(not verify_consistency_proof(x, old, new) for x in attacks)
    wrong_ancestry = checkpoint(values, previous="7" * 64, created_at=NOW + timedelta(seconds=1))
    assert not verify_consistency_proof(build_consistency_proof(old, wrong_ancestry, values),
                                        old, wrong_ancestry)
    rollback = checkpoint(values[:1])
    with pytest.raises(ValueError):
        build_consistency_proof(old, rollback, values[:1])


def test_conflicting_roots_at_same_size_explicitly_detect_equivocation():
    values = tuple(transparency_entry_digest(entry(i)) for i in range(1, 3))
    left = checkpoint(values)
    right = checkpoint((values[0], "9" * 64))
    assert checkpoints_equivocate(left, right)
    assert not checkpoints_equivocate(left, replace(right, environment="production"))


def test_public_outcome_is_json_safe_and_does_not_leak_protected_information():
    outcome = public_transparency_outcome(
        decision=PublicTransparencyDecision.EQUIVOCATION_DETECTED, observed_at=NOW,
        log_id="atl-transparency", checkpoint_id="1" * 64, tree_size=2,
    )
    serialized = json.dumps(asdict(outcome), default=str)
    assert outcome.decision is PublicTransparencyDecision.EQUIVOCATION_DETECTED
    assert outcome.reason_category == "equivocation_detected"
    for secret in ("key_id", "operator_id", "authority", "private", "policy", "storage"):
        assert secret not in serialized


def test_stale_and_unverifiable_results_are_explicit_and_fail_closed():
    stale = public_transparency_outcome(decision=PublicTransparencyDecision.STALE_CHECKPOINT,
                                        observed_at=NOW)
    unknown = public_transparency_outcome(decision=PublicTransparencyDecision.UNVERIFIABLE,
                                          observed_at=NOW)
    assert stale.reason_category == "checkpoint_stale"
    assert unknown.log_id is None and unknown.reason_category == "transparency_unverifiable"
