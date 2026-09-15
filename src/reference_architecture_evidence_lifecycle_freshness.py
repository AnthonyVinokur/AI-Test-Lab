from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Sequence

from src.reference_architecture_evidence_lifecycle_contract import (
    LifecycleEvent,
    LifecycleStatusContract,
    lifecycle_digest,
    lifecycle_identifier,
    lifecycle_utc,
)
from src.reference_architecture_evidence_lifecycle_serialization import lifecycle_sha256


@dataclass(frozen=True, slots=True)
class LifecycleStatusSnapshot:
    status: LifecycleStatusContract
    environment: str
    chain_length: int
    chain_head_id: str
    snapshot_digest: str
    contract_version: str = "1.0"

    def __post_init__(self) -> None:
        if not isinstance(self.status, LifecycleStatusContract):
            raise ValueError("status must be a LifecycleStatusContract.")
        lifecycle_identifier(self.environment, "environment")
        if type(self.chain_length) is not int or self.chain_length < 1:
            raise ValueError("chain_length must be a positive integer.")
        lifecycle_digest(self.chain_head_id, "chain_head_id")
        lifecycle_digest(self.snapshot_digest, "snapshot_digest")
        if self.contract_version != "1.0":
            raise ValueError("contract_version is unsupported.")


def _snapshot_seed(status: LifecycleStatusContract, environment: str, chain_length: int, chain_head_id: str) -> dict:
    status_document = asdict(status)
    status_document["status"] = status.status.value
    status_document["effective_at"] = status.effective_at.strftime("%Y-%m-%dT%H:%M:%SZ")
    status_document["observed_at"] = status.observed_at.strftime("%Y-%m-%dT%H:%M:%SZ")
    return {"status": status_document, "environment": environment, "chain_length": chain_length,
            "chain_head_id": chain_head_id, "contract_version": "1.0"}


def build_status_snapshot(
    status: LifecycleStatusContract, *, environment: str, chain_length: int, chain_head_id: str
) -> LifecycleStatusSnapshot:
    seed = _snapshot_seed(status, environment, chain_length, chain_head_id)
    return LifecycleStatusSnapshot(status, environment, chain_length, chain_head_id, lifecycle_sha256(seed))


def verify_status_freshness(
    snapshot: LifecycleStatusSnapshot,
    authoritative_history: Sequence[LifecycleEvent],
    *,
    expected_environment: str,
    observed_at: datetime,
) -> bool:
    """Accept only a snapshot matching the complete authoritative chain at this observation time."""

    try:
        observed = lifecycle_utc(observed_at, "observed_at")
        eligible = tuple(event for event in authoritative_history if event.effective_at <= observed)
        if not eligible:
            return False
        expected_digest = lifecycle_sha256(
            _snapshot_seed(snapshot.status, snapshot.environment, snapshot.chain_length, snapshot.chain_head_id)
        )
        head = eligible[-1]
        return (
            snapshot.snapshot_digest == expected_digest
            and snapshot.environment == expected_environment == head.environment
            and snapshot.chain_length == len(eligible)
            and snapshot.chain_head_id == head.event_digest == snapshot.status.latest_event_id
            and snapshot.status.receipt_id == head.receipt_id
            and snapshot.status.evidence_package_id == head.evidence_package_id
            and snapshot.status.release_manifest_digest == head.release_manifest_digest
            and snapshot.status.observed_at == observed
        )
    except Exception:
        return False

