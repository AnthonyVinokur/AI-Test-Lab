from __future__ import annotations

import base64
from dataclasses import asdict, dataclass
from datetime import datetime
from hashlib import sha256
from typing import Callable

from src.reference_architecture_transparency_contract import (
    TRANSPARENCY_CONTRACT_VERSION, TRANSPARENCY_DIGEST_ALGORITHM,
    TRANSPARENCY_SERIALIZATION_ALGORITHM, TransparencyOperation,
    transparency_digest, transparency_identifier, transparency_utc,
)
from src.reference_architecture_transparency_serialization import (
    canonical_transparency_json_bytes, canonical_transparency_timestamp,
)


CHECKPOINT_SIGNATURE_ALGORITHM = "ed25519"


@dataclass(frozen=True, slots=True)
class TransparencyAuthorityGrant:
    operator_id: str
    key_id: str
    log_id: str
    environment: str
    allowed_operations: frozenset[TransparencyOperation]
    valid_from: datetime
    valid_until: datetime
    contract_version: str = TRANSPARENCY_CONTRACT_VERSION

    def __post_init__(self) -> None:
        for value, name in ((self.operator_id, "operator_id"), (self.key_id, "key_id"),
                            (self.log_id, "log_id"), (self.environment, "environment")):
            transparency_identifier(value, name)
        if not self.allowed_operations or any(not isinstance(x, TransparencyOperation)
                                              for x in self.allowed_operations):
            raise ValueError("allowed_operations is invalid.")
        object.__setattr__(self, "valid_from", transparency_utc(self.valid_from, "valid_from"))
        object.__setattr__(self, "valid_until", transparency_utc(self.valid_until, "valid_until"))
        if self.valid_until <= self.valid_from or self.contract_version != TRANSPARENCY_CONTRACT_VERSION:
            raise ValueError("authority grant is invalid.")


@dataclass(frozen=True, slots=True)
class TransparencyCheckpoint:
    log_id: str
    environment: str
    tree_size: int
    root_digest: str
    previous_checkpoint_id: str | None
    created_at: datetime
    operator_id: str
    key_id: str
    signature_base64: str
    contract_version: str = TRANSPARENCY_CONTRACT_VERSION
    serialization_algorithm: str = TRANSPARENCY_SERIALIZATION_ALGORITHM
    digest_algorithm: str = TRANSPARENCY_DIGEST_ALGORITHM
    signature_algorithm: str = CHECKPOINT_SIGNATURE_ALGORITHM

    def __post_init__(self) -> None:
        for value, name in ((self.log_id, "log_id"), (self.environment, "environment"),
                            (self.operator_id, "operator_id"), (self.key_id, "key_id")):
            transparency_identifier(value, name)
        transparency_digest(self.root_digest, "root_digest")
        if self.previous_checkpoint_id is not None:
            transparency_digest(self.previous_checkpoint_id, "previous_checkpoint_id")
        if type(self.tree_size) is not int or self.tree_size < 0:
            raise ValueError("tree_size is invalid.")
        object.__setattr__(self, "created_at", transparency_utc(self.created_at, "created_at"))
        try:
            signature = base64.b64decode(self.signature_base64, validate=True)
        except Exception as error:
            raise ValueError("signature_base64 is invalid.") from error
        if self.signature_base64 and len(signature) != 64:
            raise ValueError("signature_base64 is invalid.")
        if (self.contract_version, self.serialization_algorithm, self.digest_algorithm,
                self.signature_algorithm) != (TRANSPARENCY_CONTRACT_VERSION,
                TRANSPARENCY_SERIALIZATION_ALGORITHM, TRANSPARENCY_DIGEST_ALGORITHM,
                CHECKPOINT_SIGNATURE_ALGORITHM):
            raise ValueError("checkpoint algorithms or version are unsupported.")


def checkpoint_payload(checkpoint: TransparencyCheckpoint) -> bytes:
    document = asdict(checkpoint)
    document["created_at"] = canonical_transparency_timestamp(checkpoint.created_at)
    document.pop("signature_base64")
    return canonical_transparency_json_bytes(document)


def checkpoint_id(checkpoint: TransparencyCheckpoint) -> str:
    return sha256(checkpoint_payload(checkpoint) + b"\x00" + checkpoint.signature_base64.encode("ascii")).hexdigest()


def build_checkpoint(*, signer: Callable[[bytes], bytes], **values: object) -> TransparencyCheckpoint:
    draft = TransparencyCheckpoint(signature_base64="", **values)
    signature = base64.b64encode(signer(checkpoint_payload(draft))).decode("ascii")
    return TransparencyCheckpoint(**{**values, "signature_base64": signature})


def verify_checkpoint(checkpoint: TransparencyCheckpoint, grant: TransparencyAuthorityGrant, *,
                      entries: tuple[str, ...], observed_at: datetime,
                      signature_verifier: Callable[[bytes, bytes], bool]) -> bool:
    from src.reference_architecture_transparency_merkle import merkle_root
    try:
        observed = transparency_utc(observed_at, "observed_at")
        authorized = (grant.operator_id == checkpoint.operator_id and grant.key_id == checkpoint.key_id
                      and grant.log_id == checkpoint.log_id and grant.environment == checkpoint.environment
                      and TransparencyOperation.CHECKPOINT in grant.allowed_operations
                      and grant.valid_from <= checkpoint.created_at < grant.valid_until
                      and checkpoint.created_at <= observed and checkpoint.contract_version == grant.contract_version)
        signature = base64.b64decode(checkpoint.signature_base64, validate=True)
        return (authorized and checkpoint.tree_size == len(entries)
                and checkpoint.root_digest == merkle_root(entries)
                and signature_verifier(checkpoint_payload(checkpoint), signature))
    except Exception:
        return False
