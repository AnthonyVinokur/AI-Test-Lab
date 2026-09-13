from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Generic, Literal, TypeVar

from pydantic import model_validator

from src.public_contract import PublicContractModel
from src.reference_architecture_integration_adapter import (
    ReferenceArchitectureIntegrationPort,
)
from src.reference_architecture_response_translation import (
    ProviderNeutralIntegrationResponseV1,
)
from src.reference_architecture_round_trip_failure_normalization import (
    FailureNormalizingReferenceArchitectureRoundTripOrchestrator,
    ReferenceArchitectureNormalizedRoundTripResultV1,
    ReferenceArchitectureRoundTripFailureV1,
)


REFERENCE_ARCHITECTURE_ROUND_TRIP_OUTCOME_CONTRACT_NAME = (
    "ai-test-lab.reference-architecture-round-trip-outcome"
)
REFERENCE_ARCHITECTURE_ROUND_TRIP_OUTCOME_CONTRACT_VERSION = "1.0"

RawResponseT = TypeVar("RawResponseT", bound=Mapping[str, Any])


class ReferenceArchitectureRoundTripOutcomeV1(PublicContractModel):
    """Frozen public projection of one normalized reference round trip.

    Exactly one public branch is present. Internal adapter, raw-response,
    translation, correlation, and exception state never enters this DTO.
    """

    contract_name: Literal[
        "ai-test-lab.reference-architecture-round-trip-outcome"
    ] = REFERENCE_ARCHITECTURE_ROUND_TRIP_OUTCOME_CONTRACT_NAME
    outcome_contract_version: Literal["1.0"] = (
        REFERENCE_ARCHITECTURE_ROUND_TRIP_OUTCOME_CONTRACT_VERSION
    )
    succeeded: bool
    response: ProviderNeutralIntegrationResponseV1 | None = None
    failure: ReferenceArchitectureRoundTripFailureV1 | None = None

    @model_validator(mode="after")
    def validate_outcome_branch(self) -> "ReferenceArchitectureRoundTripOutcomeV1":
        has_response = self.response is not None
        has_failure = self.failure is not None
        if has_response == has_failure:
            raise ValueError("Exactly one of response or failure must be populated.")
        if self.succeeded != has_response:
            raise ValueError("succeeded must be true exactly when response is populated.")
        return self


def project_reference_architecture_round_trip_outcome(
    normalized: ReferenceArchitectureNormalizedRoundTripResultV1[Any],
) -> ReferenceArchitectureRoundTripOutcomeV1:
    """Project an internal A.01.7 result onto the frozen public v1 boundary."""

    if not isinstance(normalized, ReferenceArchitectureNormalizedRoundTripResultV1):
        raise TypeError("normalized must be an A.01.7 normalized round-trip result.")

    if normalized.result is not None:
        return ReferenceArchitectureRoundTripOutcomeV1(
            succeeded=True,
            response=normalized.result.response.model_copy(deep=True),
        )

    failure = normalized.failure
    if failure is None:  # Defensive guard for untrusted/runtime-altered objects.
        raise ValueError("Normalized round-trip result has no outcome branch.")
    return ReferenceArchitectureRoundTripOutcomeV1(
        succeeded=False,
        failure=failure.model_copy(deep=True),
    )


class PublicReferenceArchitectureRoundTripOrchestrator(Generic[RawResponseT]):
    """Execute A.01.7 and return only the stable public A.01.8 projection."""

    __slots__ = ("_orchestrator",)

    def __init__(
        self, port: ReferenceArchitectureIntegrationPort[RawResponseT]
    ) -> None:
        self._orchestrator = (
            FailureNormalizingReferenceArchitectureRoundTripOrchestrator(port)
        )

    def execute(
        self,
        compatibility_payload: object,
        request_identity: Mapping[str, Any],
    ) -> ReferenceArchitectureRoundTripOutcomeV1:
        normalized = self._orchestrator.execute(
            compatibility_payload, request_identity
        )
        return project_reference_architecture_round_trip_outcome(normalized)


def execute_public_reference_architecture_round_trip(
    compatibility_payload: object,
    request_identity: Mapping[str, Any],
    port: ReferenceArchitectureIntegrationPort[RawResponseT],
) -> ReferenceArchitectureRoundTripOutcomeV1:
    """Functional public entry point for the complete A.01 round trip."""

    return PublicReferenceArchitectureRoundTripOrchestrator(port).execute(
        compatibility_payload, request_identity
    )
