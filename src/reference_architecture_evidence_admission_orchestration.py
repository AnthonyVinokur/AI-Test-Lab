from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.reference_architecture_authenticated_provenance_outcome import (
    ReferenceArchitectureAuthenticatedProvenanceOutcomeV1,
)
from src.reference_architecture_conformance_evidence_binding_outcome import (
    ReferenceArchitectureConformanceEvidenceBindingOutcomeV1,
)
from src.reference_architecture_evidence_admission_decision import (
    evaluate_reference_architecture_evidence_admission,
)
from src.reference_architecture_evidence_admission_failure_normalization import (
    normalize_reference_architecture_admission_boundary_failure,
)
from src.reference_architecture_evidence_admission_outcome import (
    ReferenceArchitectureEvidenceAdmissionOutcomeV1,
    project_reference_architecture_evidence_admission_outcome,
)
from src.reference_architecture_evidence_admission_translation import (
    ReferenceArchitectureEvidenceAdmissionTranslationError,
    translate_untrusted_reference_architecture_admission_policy,
    translate_untrusted_reference_architecture_evidence_admission_request,
)
from src.reference_architecture_trusted_evidence_outcome import (
    ReferenceArchitectureTrustedEvidenceOutcomeV1,
)


def admit_public_reference_architecture_evidence(
    request_document: Mapping[str, Any],
    policy_document: Mapping[str, Any],
    *,
    integrity_result: ReferenceArchitectureConformanceEvidenceBindingOutcomeV1,
    authenticated_provenance_result: ReferenceArchitectureAuthenticatedProvenanceOutcomeV1,
    trust_result: ReferenceArchitectureTrustedEvidenceOutcomeV1,
) -> ReferenceArchitectureEvidenceAdmissionOutcomeV1:
    """ATL-A.05 public entry point with explicit stage-aware failure normalization."""
    try:
        policy = translate_untrusted_reference_architecture_admission_policy(policy_document)
    except ReferenceArchitectureEvidenceAdmissionTranslationError as error:
        return project_reference_architecture_evidence_admission_outcome(
            normalize_reference_architecture_admission_boundary_failure(error, policy_stage=True)
        )
    try:
        request = translate_untrusted_reference_architecture_evidence_admission_request(
            request_document, integrity_result=integrity_result,
            authenticated_provenance_result=authenticated_provenance_result,
            trust_result=trust_result, policy=policy,
        )
    except ReferenceArchitectureEvidenceAdmissionTranslationError as error:
        return project_reference_architecture_evidence_admission_outcome(
            normalize_reference_architecture_admission_boundary_failure(error)
        )
    return project_reference_architecture_evidence_admission_outcome(
        evaluate_reference_architecture_evidence_admission(request)
    )


__all__ = ["admit_public_reference_architecture_evidence"]
