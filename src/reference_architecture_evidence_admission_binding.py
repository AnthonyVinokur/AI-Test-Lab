from __future__ import annotations

from datetime import datetime

from src.reference_architecture_evidence_admission_contract import (
    ReferenceArchitectureAdmissionReasonCode,
    ReferenceArchitectureEvidenceAdmissionRequestV1,
)
from src.reference_architecture_evidence_admission_prerequisites import (
    ReferenceArchitectureAdmissionRejection,
)


def enforce_reference_architecture_evidence_provenance_binding(
    request: ReferenceArchitectureEvidenceAdmissionRequestV1,
) -> None:
    """Require exact equality across every binding fact exposed by A.02 and A.03."""
    if not isinstance(request, ReferenceArchitectureEvidenceAdmissionRequestV1):
        raise TypeError("request must be an evidence-admission request.")
    integrity = request.integrity_result.binding
    authentication = request.authenticated_provenance_result.authentication
    if integrity is None or authentication is None:
        raise ReferenceArchitectureAdmissionRejection(
            ReferenceArchitectureAdmissionReasonCode.EVIDENCE_BINDING_MISMATCH
        )
    issued_at = datetime.fromisoformat(authentication.issued_at[:-1] + "+00:00")
    binding_facts_agree = (
        request.evidence_sha256 == integrity.evidence.evidence.evidence_sha256
        == authentication.evidence_sha256
        and request.producer_id == authentication.producer_id
        and request.evidence_id == authentication.attestation_id
        and request.run_id == integrity.correlation_id
        and request.evidence_contract_version == integrity.evidence.evidence.schema_version
        and request.created_at == issued_at
    )
    if not binding_facts_agree:
        raise ReferenceArchitectureAdmissionRejection(
            ReferenceArchitectureAdmissionReasonCode.EVIDENCE_BINDING_MISMATCH
        )


__all__ = ["enforce_reference_architecture_evidence_provenance_binding"]
