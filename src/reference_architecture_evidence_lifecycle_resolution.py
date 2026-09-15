from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Sequence

from src.reference_architecture_evidence_lifecycle_contract import (
    LifecycleEvent,
    LifecycleEventType,
    LifecycleStatus,
    LifecycleStatusContract,
    lifecycle_utc,
)


@dataclass(frozen=True, slots=True)
class LifecycleResolution:
    status: LifecycleStatus
    observed_at: datetime
    effective_event: LifecycleEvent | None
    trustworthy: bool
    reason: str


_TRANSITIONS = {
    (LifecycleStatus.ACTIVE, LifecycleEventType.SUSPENDED): LifecycleStatus.SUSPENDED,
    (LifecycleStatus.ACTIVE, LifecycleEventType.REVOKED): LifecycleStatus.REVOKED,
    (LifecycleStatus.ACTIVE, LifecycleEventType.EXPIRED): LifecycleStatus.EXPIRED,
    (LifecycleStatus.ACTIVE, LifecycleEventType.SUPERSEDED): LifecycleStatus.SUPERSEDED,
    (LifecycleStatus.SUSPENDED, LifecycleEventType.REINSTATED): LifecycleStatus.ACTIVE,
    (LifecycleStatus.SUSPENDED, LifecycleEventType.REVOKED): LifecycleStatus.REVOKED,
    (LifecycleStatus.SUSPENDED, LifecycleEventType.EXPIRED): LifecycleStatus.EXPIRED,
    (LifecycleStatus.SUSPENDED, LifecycleEventType.SUPERSEDED): LifecycleStatus.SUPERSEDED,
}


def resolve_lifecycle_status(events: Sequence[LifecycleEvent], *, observed_at: datetime) -> LifecycleResolution:
    """Resolve status at caller-supplied time; no local clock is consulted."""

    observed = lifecycle_utc(observed_at, "observed_at")
    eligible = tuple(event for event in events if event.effective_at <= observed)
    if not eligible:
        return LifecycleResolution(LifecycleStatus.UNKNOWN, observed, None, False, "history_unavailable")
    status = LifecycleStatus.UNKNOWN
    previous: LifecycleEvent | None = None
    for index, event in enumerate(eligible):
        if previous is not None and event.effective_at == previous.effective_at:
            return LifecycleResolution(LifecycleStatus.UNKNOWN, observed, event, False, "conflicting_events")
        if index == 0:
            if event.event_type is not LifecycleEventType.ISSUED:
                return LifecycleResolution(LifecycleStatus.UNKNOWN, observed, event, False, "invalid_transition")
            status = LifecycleStatus.ACTIVE
        else:
            next_status = _TRANSITIONS.get((status, event.event_type))
            if next_status is None:
                return LifecycleResolution(LifecycleStatus.UNKNOWN, observed, event, False, "invalid_transition")
            status = next_status
        previous = event
    return LifecycleResolution(status, observed, previous, status is not LifecycleStatus.UNKNOWN, "resolved")


def lifecycle_status_contract(resolution: LifecycleResolution) -> LifecycleStatusContract:
    event = resolution.effective_event
    if not resolution.trustworthy or event is None:
        raise ValueError("Untrustworthy lifecycle resolution cannot become a verified status contract.")
    return LifecycleStatusContract(
        receipt_id=event.receipt_id,
        release_manifest_digest=event.release_manifest_digest,
        evidence_package_id=event.evidence_package_id,
        status=resolution.status,
        effective_at=event.effective_at,
        observed_at=resolution.observed_at,
        latest_event_id=event.event_digest,
    )

