from __future__ import annotations

from src.reference_architecture_evidence_admission_contract import (
    ReferenceArchitectureAdmissionReasonCode,
    ReferenceArchitectureEvidenceAdmissionRequestV1,
)


class ReferenceArchitectureAdmissionRejection(ValueError):
    def __init__(self, code: ReferenceArchitectureAdmissionReasonCode):
        super().__init__(code.value)
        self.code = code


def enforce_reference_architecture_admission_prerequisites(
    request: ReferenceArchitectureEvidenceAdmissionRequestV1,
) -> None:
    """Consume frozen upstream outcomes in fixed fail-closed order."""
    if not isinstance(request, ReferenceArchitectureEvidenceAdmissionRequestV1):
        raise TypeError("request must be an evidence-admission request.")
    if not request.integrity_result.succeeded:
        raise ReferenceArchitectureAdmissionRejection(
            ReferenceArchitectureAdmissionReasonCode.INTEGRITY_NOT_VERIFIED
        )
    if not request.authenticated_provenance_result.succeeded:
        raise ReferenceArchitectureAdmissionRejection(
            ReferenceArchitectureAdmissionReasonCode.PROVENANCE_NOT_AUTHENTICATED
        )
    if not request.trust_result.trusted:
        raise ReferenceArchitectureAdmissionRejection(
            ReferenceArchitectureAdmissionReasonCode.PROVENANCE_NOT_TRUSTED
        )


__all__ = [
    "ReferenceArchitectureAdmissionRejection",
    "enforce_reference_architecture_admission_prerequisites",
]
