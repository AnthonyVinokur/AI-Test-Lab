from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Any, Generic, Literal, TypeVar

from src.public_contract import PublicContractModel
from src.reference_architecture_integration_adapter import (
    ReferenceArchitectureIncompatibleError,
    ReferenceArchitectureIntegrationPort,
)
from src.reference_architecture_request_response_correlation import (
    ReferenceArchitectureRequestResponseCorrelationError,
)
from src.reference_architecture_request_translation import (
    ReferenceArchitectureRequestTranslationError,
)
from src.reference_architecture_response_translation import (
    ReferenceArchitectureResponseTranslationError,
)
from src.reference_architecture_round_trip_orchestration import (
    CorrelatedReferenceArchitectureRoundTripOrchestrator,
    ReferenceArchitectureRoundTripResultV1,
    ReferenceArchitectureUncorrelatedResponseError,
)


REFERENCE_ARCHITECTURE_FAILURE_NORMALIZATION_CONTRACT_NAME = (
    "ai-test-lab.reference-architecture-round-trip-failure"
)
REFERENCE_ARCHITECTURE_FAILURE_NORMALIZATION_CONTRACT_VERSION = "1.0"

RawResponseT = TypeVar("RawResponseT", bound=Mapping[str, Any])


class ReferenceArchitectureFailureStage(str, Enum):
    REQUEST_VALIDATION = "request_validation"
    COMPATIBILITY = "compatibility"
    PROVIDER_INVOCATION = "provider_invocation"
    RESPONSE_TRANSLATION = "response_translation"
    CORRELATION = "correlation"


class ReferenceArchitectureFailureCode(str, Enum):
    INVALID_REQUEST_IDENTITY = "invalid_request_identity"
    INVALID_COMPATIBILITY_REQUEST = "invalid_compatibility_request"
    INCOMPATIBLE_REFERENCE_ARCHITECTURE = "incompatible_reference_architecture"
    PROVIDER_INVOCATION_FAILED = "provider_invocation_failed"
    INVALID_PROVIDER_RESPONSE = "invalid_provider_response"
    UNCORRELATED_PROVIDER_RESPONSE = "uncorrelated_provider_response"


class ReferenceArchitectureRoundTripFailureV1(PublicContractModel):
    """Safe public description of one failed round trip.

    The raw exception, provider payload, traceback, and proprietary integration
    state are deliberately excluded from this DTO.
    """

    contract_name: Literal[
        "ai-test-lab.reference-architecture-round-trip-failure"
    ] = REFERENCE_ARCHITECTURE_FAILURE_NORMALIZATION_CONTRACT_NAME
    failure_contract_version: Literal["1.0"] = (
        REFERENCE_ARCHITECTURE_FAILURE_NORMALIZATION_CONTRACT_VERSION
    )
    stage: ReferenceArchitectureFailureStage
    code: ReferenceArchitectureFailureCode
    message: str
    retryable: bool
    integration_id: str | None = None
    correlation_id: str | None = None


@dataclass(frozen=True, slots=True)
class ReferenceArchitectureNormalizedRoundTripResultV1(Generic[RawResponseT]):
    """Internal success/failure union with exactly one populated branch."""

    result: ReferenceArchitectureRoundTripResultV1[RawResponseT] | None = None
    failure: ReferenceArchitectureRoundTripFailureV1 | None = None

    def __post_init__(self) -> None:
        if (self.result is None) == (self.failure is None):
            raise ValueError("Exactly one of result or failure must be populated.")

    @property
    def succeeded(self) -> bool:
        return self.result is not None


def _safe_identifiers(
    request_identity: object,
) -> tuple[str | None, str | None]:
    if not isinstance(request_identity, Mapping):
        return None, None
    integration_id = request_identity.get("integration_id")
    correlation_id = request_identity.get("correlation_id")
    return (
        integration_id if isinstance(integration_id, str) and integration_id else None,
        correlation_id if isinstance(correlation_id, str) and correlation_id else None,
    )


def normalize_reference_architecture_round_trip_failure(
    error: Exception,
    request_identity: object = None,
) -> ReferenceArchitectureRoundTripFailureV1:
    """Map a round-trip exception to one deterministic, provider-neutral DTO."""

    if isinstance(error, ReferenceArchitectureRequestResponseCorrelationError):
        stage = ReferenceArchitectureFailureStage.REQUEST_VALIDATION
        code = ReferenceArchitectureFailureCode.INVALID_REQUEST_IDENTITY
        message = "The round-trip request identity is invalid."
    elif isinstance(error, ReferenceArchitectureIncompatibleError):
        stage = ReferenceArchitectureFailureStage.COMPATIBILITY
        code = ReferenceArchitectureFailureCode.INCOMPATIBLE_REFERENCE_ARCHITECTURE
        message = "The reference architecture is not compatible with the frozen v1 contract."
    elif isinstance(error, ReferenceArchitectureRequestTranslationError):
        stage = ReferenceArchitectureFailureStage.COMPATIBILITY
        code = ReferenceArchitectureFailureCode.INVALID_COMPATIBILITY_REQUEST
        message = "The compatibility request is invalid."
    elif isinstance(error, ReferenceArchitectureResponseTranslationError):
        stage = ReferenceArchitectureFailureStage.RESPONSE_TRANSLATION
        code = ReferenceArchitectureFailureCode.INVALID_PROVIDER_RESPONSE
        message = "The provider response is invalid."
    elif isinstance(error, ReferenceArchitectureUncorrelatedResponseError):
        stage = ReferenceArchitectureFailureStage.CORRELATION
        code = ReferenceArchitectureFailureCode.UNCORRELATED_PROVIDER_RESPONSE
        message = "The provider response does not belong to this request."
    else:
        stage = ReferenceArchitectureFailureStage.PROVIDER_INVOCATION
        code = ReferenceArchitectureFailureCode.PROVIDER_INVOCATION_FAILED
        message = "The provider could not complete the integration request."

    integration_id, correlation_id = _safe_identifiers(request_identity)
    return ReferenceArchitectureRoundTripFailureV1(
        stage=stage,
        code=code,
        message=message,
        retryable=code is ReferenceArchitectureFailureCode.PROVIDER_INVOCATION_FAILED,
        integration_id=integration_id,
        correlation_id=correlation_id,
    )


class FailureNormalizingReferenceArchitectureRoundTripOrchestrator(
    Generic[RawResponseT]
):
    """Execute A.01.6 and convert every ordinary failure at the outer boundary."""

    __slots__ = ("_orchestrator",)

    def __init__(
        self, port: ReferenceArchitectureIntegrationPort[RawResponseT]
    ) -> None:
        self._orchestrator = CorrelatedReferenceArchitectureRoundTripOrchestrator(port)

    def execute(
        self,
        compatibility_payload: object,
        request_identity: Mapping[str, Any],
    ) -> ReferenceArchitectureNormalizedRoundTripResultV1[RawResponseT]:
        try:
            result = self._orchestrator.execute(
                compatibility_payload, request_identity
            )
        except Exception as error:
            return ReferenceArchitectureNormalizedRoundTripResultV1(
                failure=normalize_reference_architecture_round_trip_failure(
                    error, request_identity
                )
            )
        return ReferenceArchitectureNormalizedRoundTripResultV1(result=result)


def orchestrate_reference_architecture_round_trip_with_normalized_failure(
    compatibility_payload: object,
    request_identity: Mapping[str, Any],
    port: ReferenceArchitectureIntegrationPort[RawResponseT],
) -> ReferenceArchitectureNormalizedRoundTripResultV1[RawResponseT]:
    return FailureNormalizingReferenceArchitectureRoundTripOrchestrator(port).execute(
        compatibility_payload, request_identity
    )
