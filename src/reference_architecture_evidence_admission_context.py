from __future__ import annotations

from src.reference_architecture_evidence_admission_contract import (
    ReferenceArchitectureAdmissionReasonCode,
    ReferenceArchitectureEvidenceAdmissionRequestV1,
)
from src.reference_architecture_evidence_admission_prerequisites import (
    ReferenceArchitectureAdmissionRejection,
)


def enforce_reference_architecture_admission_context(
    request: ReferenceArchitectureEvidenceAdmissionRequestV1,
) -> None:
    policy = request.policy
    if request.purpose not in policy.allowed_purposes:
        raise ReferenceArchitectureAdmissionRejection(
            ReferenceArchitectureAdmissionReasonCode.PURPOSE_NOT_ALLOWED
        )
    if request.target_environment not in policy.allowed_environments:
        raise ReferenceArchitectureAdmissionRejection(
            ReferenceArchitectureAdmissionReasonCode.ENVIRONMENT_NOT_ALLOWED
        )


__all__ = ["enforce_reference_architecture_admission_context"]
