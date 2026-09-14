from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Literal

from src.public_contract import PublicContractModel
from src.reference_architecture_conformance_evidence_round_trip_binding import (
    ReferenceArchitectureConformanceEvidenceBindingError,
    ReferenceArchitectureConformanceEvidenceBindingFailureReason,
    ReferenceArchitectureConformanceEvidenceBindingV1,
    bind_reference_architecture_conformance_evidence,
)
from src.reference_architecture_round_trip_orchestration import (
    ReferenceArchitectureRoundTripResultV1,
)


REFERENCE_ARCHITECTURE_CONFORMANCE_EVIDENCE_BINDING_FAILURE_CONTRACT_NAME = (
    "ai-test-lab.reference-architecture-conformance-evidence-binding-failure"
)
REFERENCE_ARCHITECTURE_CONFORMANCE_EVIDENCE_BINDING_FAILURE_CONTRACT_VERSION = "1.0"


class ReferenceArchitectureConformanceEvidenceBindingFailureStage(str, Enum):
    ROUND_TRIP_VALIDATION = "round_trip_validation"
    RESPONSE_ACCEPTANCE = "response_acceptance"
    ARTIFACT_VALIDATION = "artifact_validation"
    DOCUMENT_TRANSLATION = "document_translation"
    INTEGRITY = "integrity"
    COMPATIBILITY = "compatibility"
    BINDING = "binding"


class ReferenceArchitectureConformanceEvidenceBindingFailureCode(str, Enum):
    INVALID_ROUND_TRIP = "invalid_round_trip"
    UNCORRELATED_RESPONSE = "uncorrelated_response"
    RESPONSE_NOT_COMPLETED = "response_not_completed"
    MISSING_EVIDENCE_ARTIFACT = "missing_evidence_artifact"
    INVALID_EVIDENCE_TRANSPORT = "invalid_evidence_transport"
    INVALID_EVIDENCE_DOCUMENT = "invalid_evidence_document"
    EVIDENCE_INTEGRITY_FAILED = "evidence_integrity_failed"
    INCOMPATIBLE_EVIDENCE = "incompatible_evidence"
    EVIDENCE_BINDING_FAILED = "evidence_binding_failed"


class ReferenceArchitectureConformanceEvidenceBindingFailureV1(PublicContractModel):
    """Safe public description of one rejected evidence-binding attempt."""

    contract_name: Literal[
        "ai-test-lab.reference-architecture-conformance-evidence-binding-failure"
    ] = REFERENCE_ARCHITECTURE_CONFORMANCE_EVIDENCE_BINDING_FAILURE_CONTRACT_NAME
    failure_contract_version: Literal["1.0"] = (
        REFERENCE_ARCHITECTURE_CONFORMANCE_EVIDENCE_BINDING_FAILURE_CONTRACT_VERSION
    )
    stage: ReferenceArchitectureConformanceEvidenceBindingFailureStage
    code: ReferenceArchitectureConformanceEvidenceBindingFailureCode
    message: str
    retryable: bool = False
    integration_id: str | None = None
    correlation_id: str | None = None


@dataclass(frozen=True, slots=True)
class ReferenceArchitectureNormalizedConformanceEvidenceBindingV1:
    """Internal success/failure union with exactly one populated branch."""

    binding: ReferenceArchitectureConformanceEvidenceBindingV1 | None = None
    failure: ReferenceArchitectureConformanceEvidenceBindingFailureV1 | None = None

    def __post_init__(self) -> None:
        if (self.binding is None) == (self.failure is None):
            raise ValueError("Exactly one of binding or failure must be populated.")

    @property
    def succeeded(self) -> bool:
        return self.binding is not None


_REASON_MAP = {
    ReferenceArchitectureConformanceEvidenceBindingFailureReason.UNCORRELATED_RESPONSE: (
        ReferenceArchitectureConformanceEvidenceBindingFailureStage.ROUND_TRIP_VALIDATION,
        ReferenceArchitectureConformanceEvidenceBindingFailureCode.UNCORRELATED_RESPONSE,
        "The evidence response is not correlated to the request.",
    ),
    ReferenceArchitectureConformanceEvidenceBindingFailureReason.RESPONSE_NOT_COMPLETED: (
        ReferenceArchitectureConformanceEvidenceBindingFailureStage.RESPONSE_ACCEPTANCE,
        ReferenceArchitectureConformanceEvidenceBindingFailureCode.RESPONSE_NOT_COMPLETED,
        "The evidence response is not completed.",
    ),
    ReferenceArchitectureConformanceEvidenceBindingFailureReason.MISSING_EVIDENCE_ARTIFACT: (
        ReferenceArchitectureConformanceEvidenceBindingFailureStage.ARTIFACT_VALIDATION,
        ReferenceArchitectureConformanceEvidenceBindingFailureCode.MISSING_EVIDENCE_ARTIFACT,
        "The completed response does not contain a conformance-evidence artifact.",
    ),
    ReferenceArchitectureConformanceEvidenceBindingFailureReason.INVALID_EVIDENCE_TRANSPORT: (
        ReferenceArchitectureConformanceEvidenceBindingFailureStage.ARTIFACT_VALIDATION,
        ReferenceArchitectureConformanceEvidenceBindingFailureCode.INVALID_EVIDENCE_TRANSPORT,
        "The evidence artifact transport identity is invalid.",
    ),
    ReferenceArchitectureConformanceEvidenceBindingFailureReason.INVALID_EVIDENCE_BASE64: (
        ReferenceArchitectureConformanceEvidenceBindingFailureStage.ARTIFACT_VALIDATION,
        ReferenceArchitectureConformanceEvidenceBindingFailureCode.INVALID_EVIDENCE_TRANSPORT,
        "The evidence artifact payload is invalid.",
    ),
    ReferenceArchitectureConformanceEvidenceBindingFailureReason.INVALID_EVIDENCE_DOCUMENT: (
        ReferenceArchitectureConformanceEvidenceBindingFailureStage.DOCUMENT_TRANSLATION,
        ReferenceArchitectureConformanceEvidenceBindingFailureCode.INVALID_EVIDENCE_DOCUMENT,
        "The evidence document is invalid.",
    ),
    ReferenceArchitectureConformanceEvidenceBindingFailureReason.EVIDENCE_INTEGRITY_FAILED: (
        ReferenceArchitectureConformanceEvidenceBindingFailureStage.INTEGRITY,
        ReferenceArchitectureConformanceEvidenceBindingFailureCode.EVIDENCE_INTEGRITY_FAILED,
        "The evidence document failed integrity verification.",
    ),
    ReferenceArchitectureConformanceEvidenceBindingFailureReason.INCOMPATIBLE_EVIDENCE: (
        ReferenceArchitectureConformanceEvidenceBindingFailureStage.COMPATIBILITY,
        ReferenceArchitectureConformanceEvidenceBindingFailureCode.INCOMPATIBLE_EVIDENCE,
        "The evidence targets an unsupported contract.",
    ),
}


def _safe_response_identifiers(
    round_trip: object,
) -> tuple[str | None, str | None]:
    if not isinstance(round_trip, ReferenceArchitectureRoundTripResultV1):
        return None, None
    integration_id = round_trip.response.integration_id
    correlation_id = round_trip.response.correlation_id
    return (
        integration_id if isinstance(integration_id, str) and integration_id else None,
        correlation_id if isinstance(correlation_id, str) and correlation_id else None,
    )


def normalize_reference_architecture_conformance_evidence_binding_failure(
    error: Exception,
    round_trip: object = None,
) -> ReferenceArchitectureConformanceEvidenceBindingFailureV1:
    """Map a binding exception to one deterministic, redacted public DTO."""

    if isinstance(error, TypeError):
        stage = ReferenceArchitectureConformanceEvidenceBindingFailureStage.ROUND_TRIP_VALIDATION
        code = ReferenceArchitectureConformanceEvidenceBindingFailureCode.INVALID_ROUND_TRIP
        message = "The evidence binding input is not a valid A.01 round trip."
    elif isinstance(error, ReferenceArchitectureConformanceEvidenceBindingError):
        stage, code, message = _REASON_MAP.get(
            error.reason,
            (
                ReferenceArchitectureConformanceEvidenceBindingFailureStage.BINDING,
                ReferenceArchitectureConformanceEvidenceBindingFailureCode.EVIDENCE_BINDING_FAILED,
                "The conformance evidence could not be bound.",
            ),
        )
    else:
        stage = ReferenceArchitectureConformanceEvidenceBindingFailureStage.BINDING
        code = ReferenceArchitectureConformanceEvidenceBindingFailureCode.EVIDENCE_BINDING_FAILED
        message = "The conformance evidence could not be bound."

    integration_id, correlation_id = _safe_response_identifiers(round_trip)
    return ReferenceArchitectureConformanceEvidenceBindingFailureV1(
        stage=stage,
        code=code,
        message=message,
        retryable=False,
        integration_id=integration_id,
        correlation_id=correlation_id,
    )


def bind_reference_architecture_conformance_evidence_with_normalized_failure(
    round_trip: ReferenceArchitectureRoundTripResultV1[Any] | object,
) -> ReferenceArchitectureNormalizedConformanceEvidenceBindingV1:
    """Bind evidence and convert every ordinary failure at the outer boundary."""

    try:
        binding = bind_reference_architecture_conformance_evidence(round_trip)  # type: ignore[arg-type]
    except Exception as error:
        return ReferenceArchitectureNormalizedConformanceEvidenceBindingV1(
            failure=normalize_reference_architecture_conformance_evidence_binding_failure(
                error, round_trip
            )
        )
    return ReferenceArchitectureNormalizedConformanceEvidenceBindingV1(binding=binding)


__all__ = [
    "REFERENCE_ARCHITECTURE_CONFORMANCE_EVIDENCE_BINDING_FAILURE_CONTRACT_NAME",
    "REFERENCE_ARCHITECTURE_CONFORMANCE_EVIDENCE_BINDING_FAILURE_CONTRACT_VERSION",
    "ReferenceArchitectureConformanceEvidenceBindingFailureCode",
    "ReferenceArchitectureConformanceEvidenceBindingFailureStage",
    "ReferenceArchitectureConformanceEvidenceBindingFailureV1",
    "ReferenceArchitectureNormalizedConformanceEvidenceBindingV1",
    "bind_reference_architecture_conformance_evidence_with_normalized_failure",
    "normalize_reference_architecture_conformance_evidence_binding_failure",
]
