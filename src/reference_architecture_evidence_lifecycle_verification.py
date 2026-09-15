from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Sequence

from src.reference_architecture_evidence_disclosure_contract import EvidenceDisclosureRelease
from src.reference_architecture_evidence_disclosure_serialization import disclosure_digest
from src.reference_architecture_evidence_disclosure_verification import verify_disclosure_release
from src.reference_architecture_evidence_lifecycle_chain import (
    AuthenticatedLifecycleEvent,
    AuthorityResolver,
    SignatureVerifier,
    verify_lifecycle_chain,
)
from src.reference_architecture_evidence_lifecycle_contract import LifecycleStatus, LifecycleStatusContract
from src.reference_architecture_evidence_lifecycle_resolution import (
    lifecycle_status_contract,
    resolve_lifecycle_status,
)


@dataclass(frozen=True, slots=True)
class LifecycleVerification:
    verified: bool
    status: LifecycleStatus
    status_contract: LifecycleStatusContract | None
    reason: str
    replacement_receipt_id: str | None = None
    replacement_package_id: str | None = None


def verify_release_lifecycle(
    release: EvidenceDisclosureRelease,
    history: Sequence[AuthenticatedLifecycleEvent],
    *,
    observed_at: datetime,
    authority_resolver: AuthorityResolver,
    signature_verifier: SignatureVerifier,
) -> LifecycleVerification:
    """Bind a verified ATL-A.09 release to its authenticated lifecycle history."""

    try:
        disclosure = verify_disclosure_release(release)
        if not disclosure.verified:
            raise ValueError
        events = verify_lifecycle_chain(
            history, authority_resolver=authority_resolver, signature_verifier=signature_verifier
        )
        receipt, manifest = release.receipt, release.manifest
        expected = (receipt.receipt_digest, receipt.manifest_digest, receipt.source_package_id)
        actual = (events[0].receipt_id, events[0].release_manifest_digest, events[0].evidence_package_id)
        if actual != expected or receipt.manifest_digest != disclosure_digest(asdict(manifest)):
            raise ValueError
        resolution = resolve_lifecycle_status(events, observed_at=observed_at)
        if not resolution.trustworthy:
            return LifecycleVerification(False, LifecycleStatus.UNKNOWN, None, resolution.reason)
        contract = lifecycle_status_contract(resolution)
        event = resolution.effective_event
        return LifecycleVerification(
            True,
            resolution.status,
            contract,
            "verified",
            event.replacement_receipt_id if event else None,
            event.replacement_package_id if event else None,
        )
    except Exception:
        return LifecycleVerification(False, LifecycleStatus.UNKNOWN, None, "lifecycle_unverifiable")
