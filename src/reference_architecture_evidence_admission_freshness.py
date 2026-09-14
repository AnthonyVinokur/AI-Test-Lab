from __future__ import annotations

from src.reference_architecture_evidence_admission_contract import (
    ReferenceArchitectureAdmissionReasonCode,
    ReferenceArchitectureEvidenceAdmissionRequestV1,
    ReferenceArchitectureReplayStatus,
)
from src.reference_architecture_evidence_admission_prerequisites import (
    ReferenceArchitectureAdmissionRejection,
)


def enforce_reference_architecture_evidence_freshness(
    request: ReferenceArchitectureEvidenceAdmissionRequestV1,
) -> None:
    """Use only the request's explicit evaluation time; never read a system clock."""
    if request.evaluated_at < request.not_before:
        raise ReferenceArchitectureAdmissionRejection(
            ReferenceArchitectureAdmissionReasonCode.EVIDENCE_NOT_YET_VALID
        )
    if request.evaluated_at >= request.expires_at:
        raise ReferenceArchitectureAdmissionRejection(
            ReferenceArchitectureAdmissionReasonCode.EVIDENCE_EXPIRED
        )
    if request.evaluated_at - request.created_at > request.policy.maximum_evidence_age:
        raise ReferenceArchitectureAdmissionRejection(
            ReferenceArchitectureAdmissionReasonCode.EVIDENCE_TOO_OLD
        )
    if request.replay_status is not ReferenceArchitectureReplayStatus.NOT_REPLAYED:
        raise ReferenceArchitectureAdmissionRejection(
            ReferenceArchitectureAdmissionReasonCode.EVIDENCE_REPLAY_DETECTED
        )


__all__ = ["enforce_reference_architecture_evidence_freshness"]
