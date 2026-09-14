from __future__ import annotations

from typing import Any, Literal

from pydantic import model_validator

from src.public_contract import PublicContractModel, serialize_public_contract
from src.reference_architecture_conformance_evidence_binding_failure_normalization import (
    ReferenceArchitectureConformanceEvidenceBindingFailureV1,
    ReferenceArchitectureNormalizedConformanceEvidenceBindingV1,
    bind_reference_architecture_conformance_evidence_with_normalized_failure,
)
from src.reference_architecture_conformance_evidence_intake_contract import (
    ReferenceArchitectureConformanceEvidenceIntakeV1,
)
from src.reference_architecture_round_trip_orchestration import (
    ReferenceArchitectureRoundTripResultV1,
)


REFERENCE_ARCHITECTURE_CONFORMANCE_EVIDENCE_BINDING_OUTCOME_CONTRACT_NAME = (
    "ai-test-lab.reference-architecture-conformance-evidence-binding-outcome"
)
REFERENCE_ARCHITECTURE_CONFORMANCE_EVIDENCE_BINDING_OUTCOME_CONTRACT_VERSION = "1.0"


class ReferenceArchitectureConformanceEvidenceBindingSuccessV1(PublicContractModel):
    """Minimal public proof that verified evidence was bound to one response."""

    integration_id: str
    correlation_id: str
    evidence: ReferenceArchitectureConformanceEvidenceIntakeV1


class ReferenceArchitectureConformanceEvidenceBindingOutcomeV1(PublicContractModel):
    """Frozen public projection of one normalized evidence-binding attempt."""

    contract_name: Literal[
        "ai-test-lab.reference-architecture-conformance-evidence-binding-outcome"
    ] = REFERENCE_ARCHITECTURE_CONFORMANCE_EVIDENCE_BINDING_OUTCOME_CONTRACT_NAME
    outcome_contract_version: Literal["1.0"] = (
        REFERENCE_ARCHITECTURE_CONFORMANCE_EVIDENCE_BINDING_OUTCOME_CONTRACT_VERSION
    )
    succeeded: bool
    binding: ReferenceArchitectureConformanceEvidenceBindingSuccessV1 | None = None
    failure: ReferenceArchitectureConformanceEvidenceBindingFailureV1 | None = None

    @model_validator(mode="after")
    def validate_outcome_branch(
        self,
    ) -> "ReferenceArchitectureConformanceEvidenceBindingOutcomeV1":
        has_binding = self.binding is not None
        has_failure = self.failure is not None
        if has_binding == has_failure:
            raise ValueError("Exactly one of binding or failure must be populated.")
        if self.succeeded != has_binding:
            raise ValueError("succeeded must be true exactly when binding is populated.")
        return self


def project_reference_architecture_conformance_evidence_binding_outcome(
    normalized: ReferenceArchitectureNormalizedConformanceEvidenceBindingV1,
) -> ReferenceArchitectureConformanceEvidenceBindingOutcomeV1:
    """Project an internal A.02.06 result onto the public A.02.07 boundary."""

    if not isinstance(
        normalized, ReferenceArchitectureNormalizedConformanceEvidenceBindingV1
    ):
        raise TypeError("normalized must be an A.02.06 normalized binding result.")

    if normalized.binding is not None:
        response = normalized.binding.response
        evidence = ReferenceArchitectureConformanceEvidenceIntakeV1.model_validate(
            serialize_public_contract(normalized.binding.evidence)
        )
        return ReferenceArchitectureConformanceEvidenceBindingOutcomeV1(
            succeeded=True,
            binding=ReferenceArchitectureConformanceEvidenceBindingSuccessV1(
                integration_id=response.integration_id,
                correlation_id=response.correlation_id,
                evidence=evidence,
            ),
        )

    failure = normalized.failure
    if failure is None:
        raise ValueError("Normalized evidence-binding result has no outcome branch.")
    return ReferenceArchitectureConformanceEvidenceBindingOutcomeV1(
        succeeded=False,
        failure=failure.model_copy(deep=True),
    )


def bind_public_reference_architecture_conformance_evidence(
    round_trip: ReferenceArchitectureRoundTripResultV1[Any] | object,
) -> ReferenceArchitectureConformanceEvidenceBindingOutcomeV1:
    """Bind one A.01 result and return only the stable public A.02.07 outcome."""

    normalized = (
        bind_reference_architecture_conformance_evidence_with_normalized_failure(
            round_trip
        )
    )
    return project_reference_architecture_conformance_evidence_binding_outcome(
        normalized
    )


__all__ = [
    "REFERENCE_ARCHITECTURE_CONFORMANCE_EVIDENCE_BINDING_OUTCOME_CONTRACT_NAME",
    "REFERENCE_ARCHITECTURE_CONFORMANCE_EVIDENCE_BINDING_OUTCOME_CONTRACT_VERSION",
    "ReferenceArchitectureConformanceEvidenceBindingOutcomeV1",
    "ReferenceArchitectureConformanceEvidenceBindingSuccessV1",
    "bind_public_reference_architecture_conformance_evidence",
    "project_reference_architecture_conformance_evidence_binding_outcome",
]
