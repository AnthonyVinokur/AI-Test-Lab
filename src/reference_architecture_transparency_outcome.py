from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from src.reference_architecture_transparency_contract import transparency_utc


class PublicTransparencyDecision(str, Enum):
    INCLUDED = "included"
    NOT_INCLUDED = "not_included"
    CONSISTENT = "consistent"
    STALE_CHECKPOINT = "stale_checkpoint"
    EQUIVOCATION_DETECTED = "equivocation_detected"
    UNAUTHORIZED_CHECKPOINT = "unauthorized_checkpoint"
    INVALID_PROOF = "invalid_proof"
    UNVERIFIABLE = "unverifiable"


@dataclass(frozen=True, slots=True)
class PublicTransparencyOutcome:
    decision: PublicTransparencyDecision
    log_id: str | None
    entry_digest: str | None
    checkpoint_id: str | None
    tree_size: int | None
    observed_at: datetime
    reason_category: str

    def __post_init__(self) -> None:
        if not isinstance(self.decision, PublicTransparencyDecision):
            raise ValueError("decision is unsupported.")
        object.__setattr__(self, "observed_at", transparency_utc(self.observed_at, "observed_at"))


def public_transparency_outcome(*, decision: PublicTransparencyDecision, observed_at: datetime,
                                log_id: str | None = None, entry_digest: str | None = None,
                                checkpoint_id: str | None = None, tree_size: int | None = None
                                ) -> PublicTransparencyOutcome:
    reasons = {
        PublicTransparencyDecision.INCLUDED: "entry_included",
        PublicTransparencyDecision.NOT_INCLUDED: "entry_not_included",
        PublicTransparencyDecision.CONSISTENT: "history_consistent",
        PublicTransparencyDecision.STALE_CHECKPOINT: "checkpoint_stale",
        PublicTransparencyDecision.EQUIVOCATION_DETECTED: "equivocation_detected",
        PublicTransparencyDecision.UNAUTHORIZED_CHECKPOINT: "checkpoint_unauthorized",
        PublicTransparencyDecision.INVALID_PROOF: "proof_invalid",
        PublicTransparencyDecision.UNVERIFIABLE: "transparency_unverifiable",
    }
    return PublicTransparencyOutcome(decision, log_id, entry_digest, checkpoint_id, tree_size,
                                     observed_at, reasons[decision])
