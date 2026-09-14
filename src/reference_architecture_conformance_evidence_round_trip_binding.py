from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass
from typing import Any

from src.reference_architecture_compatibility_contract import (
    ReferenceArchitectureCompatibility,
)
from src.reference_architecture_conformance_evidence_compatibility_verification import (
    verify_reference_architecture_conformance_evidence_compatibility,
)
from src.reference_architecture_conformance_evidence_document_translation import (
    ReferenceArchitectureConformanceEvidenceDocumentTranslationError,
    translate_untrusted_reference_architecture_conformance_evidence_document,
)
from src.reference_architecture_conformance_evidence_intake_contract import (
    ReferenceArchitectureConformanceEvidenceIntakeV1,
)
from src.reference_architecture_conformance_evidence_integrity_verification import (
    verify_reference_architecture_conformance_evidence_integrity,
)
from src.reference_architecture_response_translation import (
    ProviderNeutralIntegrationResponseV1,
    ProviderNeutralIntegrationStatusV1,
)
from src.reference_architecture_round_trip_orchestration import (
    ReferenceArchitectureRoundTripResultV1,
)


REFERENCE_ARCHITECTURE_CONFORMANCE_EVIDENCE_ROUND_TRIP_BINDING_CONTRACT_NAME = (
    "ai-test-lab.reference-architecture-conformance-evidence-round-trip-binding"
)
REFERENCE_ARCHITECTURE_CONFORMANCE_EVIDENCE_ROUND_TRIP_BINDING_CONTRACT_VERSION = (
    "1.0"
)

_CONFORMANCE_EVIDENCE_ARTIFACT_TYPE = "conformance-evidence"
_CONFORMANCE_EVIDENCE_CONTENT_TYPE = "application/json"
_CONFORMANCE_EVIDENCE_ARTIFACT_SCHEMA_VERSION = "1.0"


class ReferenceArchitectureConformanceEvidenceBindingError(ValueError):
    """Raised when evidence cannot be bound to its correlated A.01 response."""


@dataclass(frozen=True, slots=True)
class ReferenceArchitectureConformanceEvidenceBindingV1:
    """Internal accepted binding with no raw provider or adapter state."""

    response: ProviderNeutralIntegrationResponseV1
    evidence: ReferenceArchitectureConformanceEvidenceIntakeV1


def bind_reference_architecture_conformance_evidence(
    round_trip: ReferenceArchitectureRoundTripResultV1[Any],
) -> ReferenceArchitectureConformanceEvidenceBindingV1:
    """Accept and bind the evidence carried by one correlated A.01 result.

    The artifact is decoded directly from the validated response. It must match
    the frozen transport identity, translate into the A.02.01 contract, pass
    both digest checks, and target the exact supported A.01 contract.
    """

    if not isinstance(round_trip, ReferenceArchitectureRoundTripResultV1):
        raise TypeError("round_trip must be an A.01 correlated round-trip result.")
    if not round_trip.correlation.correlated:
        raise ReferenceArchitectureConformanceEvidenceBindingError(
            "Evidence cannot be bound to an uncorrelated response."
        )

    response = round_trip.response
    if response.status is not ProviderNeutralIntegrationStatusV1.COMPLETED:
        raise ReferenceArchitectureConformanceEvidenceBindingError(
            "Evidence requires a completed A.01 response."
        )

    artifact = response.artifact
    if artifact is None:
        raise ReferenceArchitectureConformanceEvidenceBindingError(
            "The completed A.01 response does not carry an evidence artifact."
        )
    if (
        artifact.artifact_type != _CONFORMANCE_EVIDENCE_ARTIFACT_TYPE
        or artifact.content_type != _CONFORMANCE_EVIDENCE_CONTENT_TYPE
        or artifact.schema_version != _CONFORMANCE_EVIDENCE_ARTIFACT_SCHEMA_VERSION
    ):
        raise ReferenceArchitectureConformanceEvidenceBindingError(
            "The response artifact does not match the frozen conformance-evidence transport."
        )

    try:
        document = base64.b64decode(artifact.payload_base64, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise ReferenceArchitectureConformanceEvidenceBindingError(
            "The response evidence artifact is not valid base64."
        ) from exc

    try:
        evidence = (
            translate_untrusted_reference_architecture_conformance_evidence_document(
                document
            )
        )
    except ReferenceArchitectureConformanceEvidenceDocumentTranslationError as exc:
        raise ReferenceArchitectureConformanceEvidenceBindingError(
            "The response artifact is not a valid conformance-evidence document."
        ) from exc

    if not verify_reference_architecture_conformance_evidence_integrity(evidence):
        raise ReferenceArchitectureConformanceEvidenceBindingError(
            "The response evidence failed integrity verification."
        )
    compatibility = (
        verify_reference_architecture_conformance_evidence_compatibility(evidence)
    )
    if compatibility is not ReferenceArchitectureCompatibility.EXACT:
        raise ReferenceArchitectureConformanceEvidenceBindingError(
            "The response evidence is incompatible with the supported contract."
        )

    return ReferenceArchitectureConformanceEvidenceBindingV1(
        response=response.model_copy(deep=True),
        evidence=evidence,
    )


__all__ = [
    "REFERENCE_ARCHITECTURE_CONFORMANCE_EVIDENCE_ROUND_TRIP_BINDING_CONTRACT_NAME",
    "REFERENCE_ARCHITECTURE_CONFORMANCE_EVIDENCE_ROUND_TRIP_BINDING_CONTRACT_VERSION",
    "ReferenceArchitectureConformanceEvidenceBindingError",
    "ReferenceArchitectureConformanceEvidenceBindingV1",
    "bind_reference_architecture_conformance_evidence",
]
