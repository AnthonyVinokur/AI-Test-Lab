from __future__ import annotations

from typing import Literal

from pydantic import model_validator

from src.public_contract import PublicContractModel
from src.reference_architecture_authenticated_provenance_failure_normalization import (
    ReferenceArchitectureAuthenticatedProvenanceFailureV1,
    ReferenceArchitectureNormalizedAuthenticatedProvenanceV1,
    authenticate_reference_architecture_provenance_with_normalized_failure,
)
from src.reference_architecture_authenticated_provenance_signer_key_binding import (
    ReferenceArchitectureResolvedSignerKeyBindingV1,
)


REFERENCE_ARCHITECTURE_AUTHENTICATED_PROVENANCE_OUTCOME_CONTRACT_NAME = (
    "ai-test-lab.reference-architecture-authenticated-provenance-outcome"
)
REFERENCE_ARCHITECTURE_AUTHENTICATED_PROVENANCE_OUTCOME_CONTRACT_VERSION = "1.0"


class ReferenceArchitectureAuthenticatedProvenanceSuccessV1(PublicContractModel):
    """Minimal public statement derived from an authenticated provenance claim."""

    attestation_id: str
    producer_id: str
    evidence_sha256: str
    issued_at: str
    key_id: str
    algorithm: Literal["ed25519"]


class ReferenceArchitectureAuthenticatedProvenanceOutcomeV1(PublicContractModel):
    """Frozen public projection of one normalized authentication attempt."""

    contract_name: Literal[
        "ai-test-lab.reference-architecture-authenticated-provenance-outcome"
    ] = REFERENCE_ARCHITECTURE_AUTHENTICATED_PROVENANCE_OUTCOME_CONTRACT_NAME
    outcome_contract_version: Literal["1.0"] = (
        REFERENCE_ARCHITECTURE_AUTHENTICATED_PROVENANCE_OUTCOME_CONTRACT_VERSION
    )
    succeeded: bool
    authentication: ReferenceArchitectureAuthenticatedProvenanceSuccessV1 | None = None
    failure: ReferenceArchitectureAuthenticatedProvenanceFailureV1 | None = None

    @model_validator(mode="after")
    def validate_outcome_branch(self) -> "ReferenceArchitectureAuthenticatedProvenanceOutcomeV1":
        has_authentication = self.authentication is not None
        if has_authentication == (self.failure is not None):
            raise ValueError("Exactly one of authentication or failure must be populated.")
        if self.succeeded != has_authentication:
            raise ValueError("succeeded must be true exactly when authentication is populated.")
        return self


def project_reference_architecture_authenticated_provenance_outcome(
    normalized: ReferenceArchitectureNormalizedAuthenticatedProvenanceV1,
) -> ReferenceArchitectureAuthenticatedProvenanceOutcomeV1:
    """Project an internal A.03.06 result onto the public A.03.07 boundary."""

    if not isinstance(normalized, ReferenceArchitectureNormalizedAuthenticatedProvenanceV1):
        raise TypeError("normalized must be an A.03.06 normalized authentication result.")
    if normalized.provenance is not None:
        provenance = normalized.provenance
        return ReferenceArchitectureAuthenticatedProvenanceOutcomeV1(
            succeeded=True,
            authentication=ReferenceArchitectureAuthenticatedProvenanceSuccessV1(
                attestation_id=provenance.claims.attestation_id,
                producer_id=provenance.claims.producer_id,
                evidence_sha256=provenance.claims.evidence_sha256,
                issued_at=provenance.claims.issued_at,
                key_id=provenance.proof.key_id,
                algorithm=provenance.proof.algorithm,
            ),
        )
    if normalized.failure is None:
        raise ValueError("Normalized authentication result has no outcome branch.")
    return ReferenceArchitectureAuthenticatedProvenanceOutcomeV1(
        succeeded=False, failure=normalized.failure.model_copy(deep=True)
    )


def authenticate_public_reference_architecture_provenance(
    document: bytes,
    binding: ReferenceArchitectureResolvedSignerKeyBindingV1,
) -> ReferenceArchitectureAuthenticatedProvenanceOutcomeV1:
    """Authenticate one document and expose only the stable A.03.07 outcome."""

    return project_reference_architecture_authenticated_provenance_outcome(
        authenticate_reference_architecture_provenance_with_normalized_failure(
            document, binding
        )
    )


__all__ = [
    "REFERENCE_ARCHITECTURE_AUTHENTICATED_PROVENANCE_OUTCOME_CONTRACT_NAME",
    "REFERENCE_ARCHITECTURE_AUTHENTICATED_PROVENANCE_OUTCOME_CONTRACT_VERSION",
    "ReferenceArchitectureAuthenticatedProvenanceOutcomeV1",
    "ReferenceArchitectureAuthenticatedProvenanceSuccessV1",
    "authenticate_public_reference_architecture_provenance",
    "project_reference_architecture_authenticated_provenance_outcome",
]
