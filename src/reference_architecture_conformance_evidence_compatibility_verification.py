from __future__ import annotations

from src.reference_architecture_compatibility_contract import (
    AQUAGEAR_REFERENCE_ARCHITECTURE_CONFORMANCE_CONTRACT_VERSION,
    AQUAGEAR_REFERENCE_ARCHITECTURE_CONTRACT_VERSION,
    ReferenceArchitectureCompatibility,
)
from src.reference_architecture_conformance_evidence_intake_contract import (
    ReferenceArchitectureConformanceEvidenceIntakeV1,
    ReferenceArchitectureConformanceEvidenceV1,
)


REFERENCE_ARCHITECTURE_CONFORMANCE_EVIDENCE_COMPATIBILITY_VERIFICATION_CONTRACT_NAME = (
    "ai-test-lab.reference-architecture-conformance-evidence-compatibility-verification"
)
REFERENCE_ARCHITECTURE_CONFORMANCE_EVIDENCE_COMPATIBILITY_VERIFICATION_CONTRACT_VERSION = (
    "1.0"
)


def verify_reference_architecture_conformance_evidence_compatibility(
    intake: ReferenceArchitectureConformanceEvidenceIntakeV1,
) -> ReferenceArchitectureCompatibility:
    """Compare evidence targets with ATL's deliberately supported contract.

    The current policy recognizes only an exact match. No relationship is
    inferred from similar, adjacent, or future version strings. Digest
    integrity is a separate A.02.03 decision and is intentionally not repeated
    here.
    """

    if not isinstance(intake, ReferenceArchitectureConformanceEvidenceIntakeV1):
        raise TypeError(
            "intake must be a ReferenceArchitectureConformanceEvidenceIntakeV1."
        )

    evidence = intake.evidence
    if not isinstance(evidence, ReferenceArchitectureConformanceEvidenceV1):
        return ReferenceArchitectureCompatibility.INCOMPATIBLE

    exact_match = (
        evidence.architecture_version
        == AQUAGEAR_REFERENCE_ARCHITECTURE_CONTRACT_VERSION
        and evidence.schema_version
        == AQUAGEAR_REFERENCE_ARCHITECTURE_CONFORMANCE_CONTRACT_VERSION
    )
    if exact_match:
        return ReferenceArchitectureCompatibility.EXACT
    return ReferenceArchitectureCompatibility.INCOMPATIBLE


__all__ = [
    "REFERENCE_ARCHITECTURE_CONFORMANCE_EVIDENCE_COMPATIBILITY_VERIFICATION_CONTRACT_NAME",
    "REFERENCE_ARCHITECTURE_CONFORMANCE_EVIDENCE_COMPATIBILITY_VERIFICATION_CONTRACT_VERSION",
    "verify_reference_architecture_conformance_evidence_compatibility",
]
