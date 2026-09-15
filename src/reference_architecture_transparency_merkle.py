from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Protocol, Sequence

from src.reference_architecture_transparency_contract import transparency_digest


EMPTY_ROOT = sha256(b"").hexdigest()


def leaf_hash(entry_digest: str) -> str:
    transparency_digest(entry_digest, "entry_digest")
    return sha256(b"\x00" + bytes.fromhex(entry_digest)).hexdigest()


def node_hash(left: str, right: str) -> str:
    transparency_digest(left, "left")
    transparency_digest(right, "right")
    return sha256(b"\x01" + bytes.fromhex(left) + bytes.fromhex(right)).hexdigest()


def merkle_root(entry_digests: Sequence[str]) -> str:
    if not entry_digests:
        return EMPTY_ROOT
    level = [leaf_hash(value) for value in entry_digests]
    while len(level) > 1:
        level = [node_hash(level[index], level[index + 1]) if index + 1 < len(level)
                 else level[index] for index in range(0, len(level), 2)]
    return level[0]


class TransparencyStore(Protocol):
    def entries(self) -> tuple[str, ...]: ...
    def append(self, entry_digest: str) -> int: ...


class InMemoryTransparencyStore:
    def __init__(self) -> None:
        self._entries: list[str] = []

    def entries(self) -> tuple[str, ...]:
        return tuple(self._entries)

    def append(self, entry_digest: str) -> int:
        transparency_digest(entry_digest, "entry_digest")
        if entry_digest in self._entries:
            raise ValueError("Duplicate transparency entry rejected.")
        self._entries.append(entry_digest)
        return len(self._entries) - 1


@dataclass(frozen=True, slots=True)
class InclusionProof:
    log_id: str
    environment: str
    entry_digest: str
    leaf_index: int
    tree_size: int
    proof_path: tuple[str, ...]
    checkpoint_id: str
    root_digest: str


def build_inclusion_proof(entries: Sequence[str], leaf_index: int, *, log_id: str,
                          environment: str, checkpoint_id: str) -> InclusionProof:
    if type(leaf_index) is not int or not 0 <= leaf_index < len(entries):
        raise ValueError("leaf_index is outside the tree.")
    level = [leaf_hash(value) for value in entries]
    index = leaf_index
    path: list[str] = []
    while len(level) > 1:
        sibling = index - 1 if index % 2 else index + 1
        if sibling < len(level):
            path.append(level[sibling])
        level = [node_hash(level[i], level[i + 1]) if i + 1 < len(level) else level[i]
                 for i in range(0, len(level), 2)]
        index //= 2
    return InclusionProof(log_id, environment, entries[leaf_index], leaf_index, len(entries),
                          tuple(path), checkpoint_id, level[0])


def verify_inclusion_proof(proof: InclusionProof, *, expected_entry_digest: str,
                           expected_checkpoint_id: str, expected_log_id: str,
                           expected_environment: str,
                           expected_root_digest: str | None = None,
                           expected_tree_size: int | None = None) -> bool:
    try:
        if not isinstance(proof, InclusionProof) or proof.entry_digest != expected_entry_digest:
            return False
        if (proof.checkpoint_id != expected_checkpoint_id or proof.log_id != expected_log_id
                or proof.environment != expected_environment or proof.tree_size < 1
                or not 0 <= proof.leaf_index < proof.tree_size):
            return False
        if expected_root_digest is not None and proof.root_digest != expected_root_digest:
            return False
        if expected_tree_size is not None and proof.tree_size != expected_tree_size:
            return False
        current = leaf_hash(proof.entry_digest)
        index, width, used = proof.leaf_index, proof.tree_size, 0
        while width > 1:
            has_sibling = index % 2 == 1 or index + 1 < width
            if has_sibling:
                if used >= len(proof.proof_path):
                    return False
                sibling = proof.proof_path[used]
                current = node_hash(sibling, current) if index % 2 else node_hash(current, sibling)
                used += 1
            index //= 2
            width = (width + 1) // 2
        return used == len(proof.proof_path) and current == proof.root_digest
    except (TypeError, ValueError):
        return False
