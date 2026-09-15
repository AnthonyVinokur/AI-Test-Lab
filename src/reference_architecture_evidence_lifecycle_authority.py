from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from src.reference_architecture_evidence_lifecycle_contract import (
    LifecycleEvent,
    LifecycleEventType,
    lifecycle_identifier,
    lifecycle_utc,
)


@dataclass(frozen=True, slots=True)
class LifecycleAuthorityGrant:
    authority_id: str
    issuer_id: str
    key_id: str
    receipt_id: str
    evidence_package_id: str
    environment: str
    permitted_event_types: frozenset[LifecycleEventType]
    valid_from: datetime
    valid_until: datetime
    revoked: bool = False
    contract_version: str = "1.0"

    def __post_init__(self) -> None:
        for value, name in (
            (self.authority_id, "authority_id"),
            (self.issuer_id, "issuer_id"),
            (self.key_id, "key_id"),
            (self.environment, "environment"),
        ):
            lifecycle_identifier(value, name)
        if not self.permitted_event_types or any(
            not isinstance(item, LifecycleEventType) for item in self.permitted_event_types
        ):
            raise ValueError("permitted_event_types must contain supported lifecycle events.")
        object.__setattr__(self, "valid_from", lifecycle_utc(self.valid_from, "valid_from"))
        object.__setattr__(self, "valid_until", lifecycle_utc(self.valid_until, "valid_until"))
        if self.valid_until <= self.valid_from:
            raise ValueError("authority validity window is invalid.")
        if type(self.revoked) is not bool or self.contract_version != "1.0":
            raise ValueError("authority grant is unsupported.")


class LifecycleAuthorityError(ValueError):
    pass


def verify_lifecycle_authority(event: LifecycleEvent, grant: LifecycleAuthorityGrant) -> None:
    """Fail closed unless the grant authorizes this exact transition target and context."""

    if not isinstance(event, LifecycleEvent) or not isinstance(grant, LifecycleAuthorityGrant):
        raise LifecycleAuthorityError("Lifecycle authority could not be verified.")
    allowed = (
        not grant.revoked
        and event.authority_id == grant.authority_id
        and event.issuer_id == grant.issuer_id
        and event.receipt_id == grant.receipt_id
        and event.evidence_package_id == grant.evidence_package_id
        and event.environment == grant.environment
        and event.event_type in grant.permitted_event_types
        and grant.valid_from <= event.effective_at < grant.valid_until
        and event.contract_version == grant.contract_version
    )
    if not allowed:
        raise LifecycleAuthorityError("Lifecycle authority could not be verified.")

