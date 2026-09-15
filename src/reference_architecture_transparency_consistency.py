from __future__ import annotations

from dataclasses import dataclass

from src.reference_architecture_transparency_checkpoint import (
    TransparencyCheckpoint, checkpoint_id,
)
from src.reference_architecture_transparency_merkle import merkle_root


@dataclass(frozen=True, slots=True)
class ConsistencyProof:
    log_id: str
    environment: str
    old_checkpoint_id: str
    new_checkpoint_id: str
    old_tree_size: int
    new_tree_size: int
    history_digests: tuple[str, ...]


def build_consistency_proof(old: TransparencyCheckpoint, new: TransparencyCheckpoint,
                            entries: tuple[str, ...]) -> ConsistencyProof:
    if old.tree_size > new.tree_size or len(entries) != new.tree_size:
        raise ValueError("Checkpoint sizes are inconsistent.")
    return ConsistencyProof(old.log_id, old.environment, checkpoint_id(old), checkpoint_id(new),
                            old.tree_size, new.tree_size, entries)


def verify_consistency_proof(proof: ConsistencyProof, old: TransparencyCheckpoint,
                             new: TransparencyCheckpoint) -> bool:
    try:
        return (isinstance(proof, ConsistencyProof)
                and old.log_id == new.log_id == proof.log_id
                and old.environment == new.environment == proof.environment
                and checkpoint_id(old) == proof.old_checkpoint_id
                and checkpoint_id(new) == proof.new_checkpoint_id
                and old.tree_size == proof.old_tree_size <= proof.new_tree_size == new.tree_size
                and len(proof.history_digests) == new.tree_size
                and merkle_root(proof.history_digests[:old.tree_size]) == old.root_digest
                and merkle_root(proof.history_digests) == new.root_digest
                and (old.tree_size == new.tree_size or new.previous_checkpoint_id == checkpoint_id(old)))
    except Exception:
        return False


def checkpoints_equivocate(left: TransparencyCheckpoint, right: TransparencyCheckpoint) -> bool:
    return (left.log_id == right.log_id and left.environment == right.environment
            and left.tree_size == right.tree_size and left.root_digest != right.root_digest)
