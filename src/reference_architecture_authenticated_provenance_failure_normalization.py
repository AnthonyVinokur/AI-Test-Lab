from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Literal

from src.public_contract import PublicContractModel
from src.reference_architecture_authenticated_provenance_contract import (
    ReferenceArchitectureAuthenticatedProvenanceV1,
)
from src.reference_architecture_authenticated_provenance_document_translation import (
    ReferenceArchitectureAuthenticatedProvenanceDocumentTranslationError,
    translate_untrusted_reference_architecture_authenticated_provenance_document,
)
from src.reference_architecture_authenticated_provenance_signer_key_binding import (
    ReferenceArchitectureResolvedSignerKeyBindingV1,
    verify_reference_architecture_authenticated_provenance_signer_key_binding,
)


REFERENCE_ARCHITECTURE_AUTHENTICATED_PROVENANCE_FAILURE_CONTRACT_NAME = (
    "ai-test-lab.reference-architecture-authenticated-provenance-failure"
)
REFERENCE_ARCHITECTURE_AUTHENTICATED_PROVENANCE_FAILURE_CONTRACT_VERSION = "1.0"


class ReferenceArchitectureAuthenticatedProvenanceFailureStage(str, Enum):
    DOCUMENT_TRANSLATION = "document_translation"
    BINDING_VALIDATION = "binding_validation"
    AUTHENTICATION = "authentication"


class ReferenceArchitectureAuthenticatedProvenanceFailureCode(str, Enum):
    INVALID_PROVENANCE_DOCUMENT = "invalid_provenance_document"
    INVALID_SIGNER_KEY_BINDING = "invalid_signer_key_binding"
    AUTHENTICATION_FAILED = "authentication_failed"
    PROVENANCE_VERIFICATION_FAILED = "provenance_verification_failed"


class ReferenceArchitectureAuthenticatedProvenanceFailureV1(PublicContractModel):
    """Safe public description of one rejected authentication attempt."""

    contract_name: Literal[
        "ai-test-lab.reference-architecture-authenticated-provenance-failure"
    ] = REFERENCE_ARCHITECTURE_AUTHENTICATED_PROVENANCE_FAILURE_CONTRACT_NAME
    failure_contract_version: Literal["1.0"] = (
        REFERENCE_ARCHITECTURE_AUTHENTICATED_PROVENANCE_FAILURE_CONTRACT_VERSION
    )
    stage: ReferenceArchitectureAuthenticatedProvenanceFailureStage
    code: ReferenceArchitectureAuthenticatedProvenanceFailureCode
    message: str
    retryable: bool = False
    attestation_id: str | None = None
    producer_id: str | None = None
    key_id: str | None = None


@dataclass(frozen=True, slots=True)
class ReferenceArchitectureNormalizedAuthenticatedProvenanceV1:
    """Internal authentication result with exactly one populated branch."""

    provenance: ReferenceArchitectureAuthenticatedProvenanceV1 | None = None
    failure: ReferenceArchitectureAuthenticatedProvenanceFailureV1 | None = None

    def __post_init__(self) -> None:
        if (self.provenance is None) == (self.failure is None):
            raise ValueError("Exactly one of provenance or failure must be populated.")

    @property
    def succeeded(self) -> bool:
        return self.provenance is not None


def _safe_claim_identifiers(
    provenance: object,
) -> tuple[str | None, str | None, str | None]:
    if not isinstance(provenance, ReferenceArchitectureAuthenticatedProvenanceV1):
        return None, None, None
    return (
        provenance.claims.attestation_id,
        provenance.claims.producer_id,
        provenance.proof.key_id,
    )


def normalize_reference_architecture_authenticated_provenance_failure(
    error: Exception,
    provenance: object = None,
    *,
    stage: ReferenceArchitectureAuthenticatedProvenanceFailureStage | None = None,
) -> ReferenceArchitectureAuthenticatedProvenanceFailureV1:
    """Map an authentication exception to one deterministic, redacted DTO."""

    if isinstance(
        error, ReferenceArchitectureAuthenticatedProvenanceDocumentTranslationError
    ) or stage is ReferenceArchitectureAuthenticatedProvenanceFailureStage.DOCUMENT_TRANSLATION:
        normalized_stage = (
            ReferenceArchitectureAuthenticatedProvenanceFailureStage.DOCUMENT_TRANSLATION
        )
        code = (
            ReferenceArchitectureAuthenticatedProvenanceFailureCode.INVALID_PROVENANCE_DOCUMENT
        )
        message = "The authenticated provenance document is invalid."
    elif stage is ReferenceArchitectureAuthenticatedProvenanceFailureStage.BINDING_VALIDATION:
        normalized_stage = (
            ReferenceArchitectureAuthenticatedProvenanceFailureStage.BINDING_VALIDATION
        )
        code = (
            ReferenceArchitectureAuthenticatedProvenanceFailureCode.INVALID_SIGNER_KEY_BINDING
        )
        message = "The signer-key binding is invalid."
    else:
        normalized_stage = (
            ReferenceArchitectureAuthenticatedProvenanceFailureStage.AUTHENTICATION
        )
        code = (
            ReferenceArchitectureAuthenticatedProvenanceFailureCode.PROVENANCE_VERIFICATION_FAILED
        )
        message = "The authenticated provenance could not be verified."

    attestation_id, producer_id, key_id = _safe_claim_identifiers(provenance)
    return ReferenceArchitectureAuthenticatedProvenanceFailureV1(
        stage=normalized_stage,
        code=code,
        message=message,
        retryable=False,
        attestation_id=attestation_id,
        producer_id=producer_id,
        key_id=key_id,
    )


def authenticate_reference_architecture_provenance_with_normalized_failure(
    document: bytes,
    binding: ReferenceArchitectureResolvedSignerKeyBindingV1,
) -> ReferenceArchitectureNormalizedAuthenticatedProvenanceV1:
    """Translate and authenticate provenance while normalizing ordinary failures."""

    try:
        provenance = (
            translate_untrusted_reference_architecture_authenticated_provenance_document(
                document
            )
        )
    except Exception as error:
        return ReferenceArchitectureNormalizedAuthenticatedProvenanceV1(
            failure=normalize_reference_architecture_authenticated_provenance_failure(
                error,
                stage=ReferenceArchitectureAuthenticatedProvenanceFailureStage.DOCUMENT_TRANSLATION,
            )
        )

    if not isinstance(binding, ReferenceArchitectureResolvedSignerKeyBindingV1):
        return ReferenceArchitectureNormalizedAuthenticatedProvenanceV1(
            failure=normalize_reference_architecture_authenticated_provenance_failure(
                TypeError("invalid signer-key binding"),
                provenance,
                stage=ReferenceArchitectureAuthenticatedProvenanceFailureStage.BINDING_VALIDATION,
            )
        )

    try:
        authenticated = (
            verify_reference_architecture_authenticated_provenance_signer_key_binding(
                provenance, binding
            )
        )
    except Exception as error:
        return ReferenceArchitectureNormalizedAuthenticatedProvenanceV1(
            failure=normalize_reference_architecture_authenticated_provenance_failure(
                error, provenance
            )
        )

    if not authenticated:
        attestation_id, producer_id, key_id = _safe_claim_identifiers(provenance)
        return ReferenceArchitectureNormalizedAuthenticatedProvenanceV1(
            failure=ReferenceArchitectureAuthenticatedProvenanceFailureV1(
                stage=ReferenceArchitectureAuthenticatedProvenanceFailureStage.AUTHENTICATION,
                code=ReferenceArchitectureAuthenticatedProvenanceFailureCode.AUTHENTICATION_FAILED,
                message="The authenticated provenance could not be authenticated.",
                retryable=False,
                attestation_id=attestation_id,
                producer_id=producer_id,
                key_id=key_id,
            )
        )

    return ReferenceArchitectureNormalizedAuthenticatedProvenanceV1(
        provenance=provenance
    )


__all__ = [
    "REFERENCE_ARCHITECTURE_AUTHENTICATED_PROVENANCE_FAILURE_CONTRACT_NAME",
    "REFERENCE_ARCHITECTURE_AUTHENTICATED_PROVENANCE_FAILURE_CONTRACT_VERSION",
    "ReferenceArchitectureAuthenticatedProvenanceFailureCode",
    "ReferenceArchitectureAuthenticatedProvenanceFailureStage",
    "ReferenceArchitectureAuthenticatedProvenanceFailureV1",
    "ReferenceArchitectureNormalizedAuthenticatedProvenanceV1",
    "authenticate_reference_architecture_provenance_with_normalized_failure",
    "normalize_reference_architecture_authenticated_provenance_failure",
]
