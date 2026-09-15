from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from src.reference_architecture_evidence_consumption_contract import (
    EvidenceConsumptionPolicy, EvidenceHold, EvidenceLifecycleRecord, RequesterAccessScope,
)
from src.reference_architecture_evidence_ledger_contract import EvidenceLedgerEntry


class RequesterResolverPort(Protocol):
    def resolve(self, requester_id: str, requester_type: str) -> tuple[RequesterAccessScope, ...]: ...


class ConsumptionPolicyRepositoryPort(Protocol):
    def get(self, policy_id: str, version: str) -> EvidenceConsumptionPolicy | None: ...
    def contains_policy(self, policy_id: str) -> bool: ...


class LifecycleRepositoryPort(Protocol):
    def state_for(self, evidence_id: str) -> EvidenceLifecycleRecord: ...


class HoldRepositoryPort(Protocol):
    def holds_for(self, entries: Sequence[EvidenceLedgerEntry]) -> tuple[EvidenceHold, ...]: ...


class InMemoryRequesterResolver:
    def __init__(self, scopes: Sequence[RequesterAccessScope] = ()) -> None:
        self._scopes = tuple(scopes)

    def resolve(self, requester_id: str, requester_type: str) -> tuple[RequesterAccessScope, ...]:
        return tuple(x for x in self._scopes if x.requester_id == requester_id and x.requester_type == requester_type)


class InMemoryConsumptionPolicyRepository:
    def __init__(self, policies: Sequence[EvidenceConsumptionPolicy] = ()) -> None:
        self._policies = {(x.policy_id, x.version): x for x in policies}

    def get(self, policy_id: str, version: str) -> EvidenceConsumptionPolicy | None:
        return self._policies.get((policy_id, version))

    def contains_policy(self, policy_id: str) -> bool:
        return any(item_id == policy_id for item_id, _ in self._policies)


class InMemoryLifecycleRepository:
    def __init__(self, records: Sequence[EvidenceLifecycleRecord] = ()) -> None:
        self._records = {x.evidence_id: x for x in records}

    def state_for(self, evidence_id: str) -> EvidenceLifecycleRecord:
        return self._records.get(evidence_id, EvidenceLifecycleRecord(evidence_id))


class InMemoryHoldRepository:
    def __init__(self, holds: Sequence[EvidenceHold] = ()) -> None:
        self._holds = tuple(holds)

    def holds_for(self, entries: Sequence[EvidenceLedgerEntry]) -> tuple[EvidenceHold, ...]:
        evidence_ids = {x.entry_id for x in entries}; run_ids = {x.evaluation_run_id for x in entries}
        return tuple(x for x in self._holds if x.evidence_ids & evidence_ids or x.run_ids & run_ids)
