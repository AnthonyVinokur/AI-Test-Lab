from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from src.reference_architecture_evidence_lifecycle_contract import LifecycleStatus
from src.reference_architecture_evidence_lifecycle_verification import LifecycleVerification


class PublicLifecycleOutcome(str, Enum):
    VALID = "valid"
    TEMPORARILY_UNAVAILABLE = "temporarily_unavailable"
    NO_LONGER_VALID = "no_longer_valid"
    REPLACED = "replaced"
    EXPIRED = "expired"
    UNVERIFIABLE = "unverifiable"


@dataclass(frozen=True, slots=True)
class PublicLifecycleResult:
    outcome: PublicLifecycleOutcome
    verified: bool
    receipt_id: str | None
    package_id: str | None
    effective_at: str | None
    observed_at: str | None
    event_reference: str | None
    replacement_receipt_id: str | None
    replacement_package_id: str | None
    reason_category: str
    contract_version: str = "1.0"


_OUTCOMES = {
    LifecycleStatus.ACTIVE: PublicLifecycleOutcome.VALID,
    LifecycleStatus.SUSPENDED: PublicLifecycleOutcome.TEMPORARILY_UNAVAILABLE,
    LifecycleStatus.REVOKED: PublicLifecycleOutcome.NO_LONGER_VALID,
    LifecycleStatus.SUPERSEDED: PublicLifecycleOutcome.REPLACED,
    LifecycleStatus.EXPIRED: PublicLifecycleOutcome.EXPIRED,
    LifecycleStatus.UNKNOWN: PublicLifecycleOutcome.UNVERIFIABLE,
}


def public_lifecycle_result(verification: LifecycleVerification) -> PublicLifecycleResult:
    """Explicitly project safe fields; never serialize internal verification objects."""

    contract = verification.status_contract if verification.verified else None
    outcome = _OUTCOMES.get(verification.status, PublicLifecycleOutcome.UNVERIFIABLE)
    if not verification.verified:
        outcome = PublicLifecycleOutcome.UNVERIFIABLE
    return PublicLifecycleResult(
        outcome=outcome,
        verified=verification.verified,
        receipt_id=contract.receipt_id if contract else None,
        package_id=contract.evidence_package_id if contract else None,
        effective_at=contract.effective_at.strftime("%Y-%m-%dT%H:%M:%SZ") if contract else None,
        observed_at=contract.observed_at.strftime("%Y-%m-%dT%H:%M:%SZ") if contract else None,
        event_reference=contract.latest_event_id if contract else None,
        replacement_receipt_id=verification.replacement_receipt_id if verification.verified else None,
        replacement_package_id=verification.replacement_package_id if verification.verified else None,
        reason_category="verified_lifecycle" if verification.verified else "lifecycle_unverifiable",
    )

