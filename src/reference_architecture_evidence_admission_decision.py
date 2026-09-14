from __future__ import annotations

from src.reference_architecture_evidence_admission_authorization import (
    enforce_reference_architecture_evidence_authorization,
)
from src.reference_architecture_evidence_admission_binding import (
    enforce_reference_architecture_evidence_provenance_binding,
)
from src.reference_architecture_evidence_admission_context import (
    enforce_reference_architecture_admission_context,
)
from src.reference_architecture_evidence_admission_contract import (
    ReferenceArchitectureAdmissionDecision,
    ReferenceArchitectureAdmissionReasonCode,
    ReferenceArchitectureEvidenceAdmissionRequestV1,
    ReferenceArchitectureInternalAdmissionResultV1,
)
from src.reference_architecture_evidence_admission_freshness import (
    enforce_reference_architecture_evidence_freshness,
)
from src.reference_architecture_evidence_admission_prerequisites import (
    ReferenceArchitectureAdmissionRejection,
    enforce_reference_architecture_admission_prerequisites,
)


def evaluate_reference_architecture_evidence_admission(
    request: ReferenceArchitectureEvidenceAdmissionRequestV1,
) -> ReferenceArchitectureInternalAdmissionResultV1:
    """Return the first stable rejection from the frozen evaluation sequence."""
    if not isinstance(request, ReferenceArchitectureEvidenceAdmissionRequestV1):
        raise TypeError("request must be an evidence-admission request.")
    try:
        enforce_reference_architecture_admission_prerequisites(request)
        enforce_reference_architecture_evidence_provenance_binding(request)
        enforce_reference_architecture_admission_context(request)
        enforce_reference_architecture_evidence_authorization(request)
        enforce_reference_architecture_evidence_freshness(request)
    except ReferenceArchitectureAdmissionRejection as rejection:
        return ReferenceArchitectureInternalAdmissionResultV1(
            decision=ReferenceArchitectureAdmissionDecision.REJECTED,
            reason_code=rejection.code,
        )
    return ReferenceArchitectureInternalAdmissionResultV1(
        decision=ReferenceArchitectureAdmissionDecision.ADMITTED,
        reason_code=ReferenceArchitectureAdmissionReasonCode.EVIDENCE_ADMITTED,
    )


__all__ = ["evaluate_reference_architecture_evidence_admission"]
