from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

from pydantic import ValidationError

from src.reference_architecture_integration_adapter import (
    ProviderNeutralReferenceIntegrationAdapter,
    ReferenceArchitectureIntegrationPort,
    ReferenceArchitectureIntegrationResult,
)
from src.reference_architecture_request_response_correlation import (
    ProviderNeutralIntegrationRequestIdentityV1,
    ReferenceArchitectureRequestResponseCorrelationError,
    ReferenceArchitectureRequestResponseCorrelationResultV1,
    correlate_reference_architecture_request_response,
)
from src.reference_architecture_response_translation import (
    ProviderNeutralIntegrationResponseV1,
    ReferenceArchitectureResponseTranslationResultV1,
    translate_reference_architecture_response,
)


REFERENCE_ARCHITECTURE_ROUND_TRIP_ORCHESTRATION_CONTRACT_NAME = (
    "ai-test-lab.reference-architecture-correlated-round-trip-orchestration"
)
REFERENCE_ARCHITECTURE_ROUND_TRIP_ORCHESTRATION_CONTRACT_VERSION = "1.0"

RawResponseT = TypeVar("RawResponseT", bound=Mapping[str, Any])


@dataclass(frozen=True, slots=True)
class ReferenceArchitectureRoundTripResultV1(Generic[RawResponseT]):
    """Internal composition of the four verified round-trip stages.

    This is deliberately not a public contract model. Callers may explicitly
    serialize one of the contained public DTOs without exposing the injected
    port, raw provider state, or orchestration internals.
    """

    integration: ReferenceArchitectureIntegrationResult[RawResponseT]
    response_translation: ReferenceArchitectureResponseTranslationResultV1
    correlation: ReferenceArchitectureRequestResponseCorrelationResultV1

    @property
    def response(self) -> ProviderNeutralIntegrationResponseV1:
        """Return the validated, correlated public response DTO."""

        return self.response_translation.response


class ReferenceArchitectureRoundTripOrchestrationError(ValueError):
    """Base error for orchestration-specific failures."""


class ReferenceArchitectureUncorrelatedResponseError(
    ReferenceArchitectureRoundTripOrchestrationError
):
    """Raised when a structurally valid response belongs to another request."""

    def __init__(
        self,
        correlation: ReferenceArchitectureRequestResponseCorrelationResultV1,
    ) -> None:
        self.correlation = correlation
        fields = ", ".join(item.field.value for item in correlation.mismatches)
        super().__init__(
            "Reference architecture response is not correlated"
            + (f": {fields}" if fields else ".")
        )


_REQUEST_IDENTITY_FIELDS = frozenset(
    {
        "contract_version",
        "integration_id",
        "correlation_id",
        "source_system",
        "operation",
    }
)


def _validate_request_identity(
    request_identity: Mapping[str, Any],
) -> dict[str, Any]:
    """Fail before provider invocation when request correlation is malformed."""

    if not isinstance(request_identity, Mapping):
        raise ReferenceArchitectureRequestResponseCorrelationError(
            "Provider-neutral request identity must be a mapping."
        )
    copied = dict(request_identity)
    if set(copied) != _REQUEST_IDENTITY_FIELDS:
        raise ReferenceArchitectureRequestResponseCorrelationError(
            "Provider-neutral request identity does not match the frozen v1 schema."
        )
    try:
        ProviderNeutralIntegrationRequestIdentityV1.model_validate(copied)
    except ValidationError as exc:
        raise ReferenceArchitectureRequestResponseCorrelationError(
            "Provider-neutral request identity does not match the frozen v1 schema."
        ) from exc
    return copied


class CorrelatedReferenceArchitectureRoundTripOrchestrator(
    Generic[RawResponseT]
):
    """Compose compatibility, integration, translation, and correlation."""

    __slots__ = ("_adapter",)

    def __init__(
        self,
        port: ReferenceArchitectureIntegrationPort[RawResponseT],
    ) -> None:
        self._adapter = ProviderNeutralReferenceIntegrationAdapter(port)

    def execute(
        self,
        compatibility_payload: object,
        request_identity: Mapping[str, Any],
    ) -> ReferenceArchitectureRoundTripResultV1[RawResponseT]:
        """Run one provider-neutral round trip and return only if correlated.

        The request identity is validated before the port can run. Existing
        compatibility, provider, response-translation, and correlation errors
        intentionally pass through without being hidden by a generic wrapper.
        """

        validated_identity = _validate_request_identity(request_identity)
        integration = self._adapter.integrate(compatibility_payload)
        response_translation = translate_reference_architecture_response(
            integration.response
        )
        correlation = correlate_reference_architecture_request_response(
            validated_identity,
            response_translation,
        )
        if not correlation.correlated:
            raise ReferenceArchitectureUncorrelatedResponseError(correlation)

        return ReferenceArchitectureRoundTripResultV1(
            integration=integration,
            response_translation=response_translation,
            correlation=correlation,
        )


def orchestrate_correlated_reference_architecture_round_trip(
    compatibility_payload: object,
    request_identity: Mapping[str, Any],
    port: ReferenceArchitectureIntegrationPort[RawResponseT],
) -> ReferenceArchitectureRoundTripResultV1[RawResponseT]:
    """Functional entry point for one correlated reference round trip."""

    return CorrelatedReferenceArchitectureRoundTripOrchestrator(port).execute(
        compatibility_payload,
        request_identity,
    )
