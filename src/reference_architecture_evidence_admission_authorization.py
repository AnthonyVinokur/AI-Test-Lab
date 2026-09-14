from __future__ import annotations

from src.reference_architecture_evidence_admission_contract import (
    ReferenceArchitectureAdmissionReasonCode,
    ReferenceArchitectureEvidenceAdmissionRequestV1,
)
from src.reference_architecture_evidence_admission_prerequisites import (
    ReferenceArchitectureAdmissionRejection,
)


def enforce_reference_architecture_evidence_authorization(
    request: ReferenceArchitectureEvidenceAdmissionRequestV1,
) -> None:
    """Apply stable checks in a documented deterministic order."""
    policy = request.policy
    if request.evidence_type not in policy.supported_evidence_types:
        raise ReferenceArchitectureAdmissionRejection(
            ReferenceArchitectureAdmissionReasonCode.EVIDENCE_TYPE_NOT_SUPPORTED
        )
    if request.producer_id not in policy.authorized_producers:
        raise ReferenceArchitectureAdmissionRejection(
            ReferenceArchitectureAdmissionReasonCode.PRODUCER_NOT_AUTHORIZED
        )
    if (request.producer_id, request.evidence_type) not in policy.allowed_producer_evidence_types:
        raise ReferenceArchitectureAdmissionRejection(
            ReferenceArchitectureAdmissionReasonCode.PRODUCER_NOT_AUTHORIZED
        )
    if request.evidence_contract_version not in policy.acceptable_contract_versions:
        raise ReferenceArchitectureAdmissionRejection(
            ReferenceArchitectureAdmissionReasonCode.CONTRACT_VERSION_NOT_SUPPORTED
        )
    if request.workflow_id not in policy.permitted_workflows:
        raise ReferenceArchitectureAdmissionRejection(
            ReferenceArchitectureAdmissionReasonCode.WORKFLOW_NOT_ALLOWED
        )


__all__ = ["enforce_reference_architecture_evidence_authorization"]
