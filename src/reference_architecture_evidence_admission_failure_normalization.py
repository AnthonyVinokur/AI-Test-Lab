from __future__ import annotations

from src.reference_architecture_evidence_admission_contract import (
    ReferenceArchitectureAdmissionDecision,
    ReferenceArchitectureAdmissionReasonCode,
    ReferenceArchitectureInternalAdmissionResultV1,
)
from src.reference_architecture_evidence_admission_translation import (
    ReferenceArchitectureEvidenceAdmissionTranslationError,
)


def normalize_reference_architecture_admission_boundary_failure(
    error: Exception,
    *,
    policy_stage: bool = False,
) -> ReferenceArchitectureInternalAdmissionResultV1:
    """Normalize expected translation failures only; defects remain exceptions."""
    if not isinstance(error, ReferenceArchitectureEvidenceAdmissionTranslationError):
        raise error
    return ReferenceArchitectureInternalAdmissionResultV1(
        decision=ReferenceArchitectureAdmissionDecision.REJECTED,
        reason_code=(
            ReferenceArchitectureAdmissionReasonCode.ADMISSION_POLICY_ERROR
            if policy_stage
            else ReferenceArchitectureAdmissionReasonCode.INVALID_ADMISSION_REQUEST
        ),
    )


__all__ = ["normalize_reference_architecture_admission_boundary_failure"]
