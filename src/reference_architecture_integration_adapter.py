from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, Protocol, TypeVar

from src.reference_architecture_request_translation import (
    ReferenceArchitectureCompatibilityRequestV1,
    ReferenceArchitectureRequestTranslationResultV1,
    translate_reference_architecture_compatibility_request,
)


REFERENCE_ARCHITECTURE_INTEGRATION_ADAPTER_CONTRACT_NAME = (
    "ai-test-lab.provider-neutral-reference-integration-adapter"
)
REFERENCE_ARCHITECTURE_INTEGRATION_ADAPTER_CONTRACT_VERSION = "1.0"

ResponseT = TypeVar("ResponseT")


class ReferenceArchitectureIntegrationPort(Protocol[ResponseT]):
    """Provider-neutral port used after the public request is accepted."""

    def integrate(
        self,
        request: ReferenceArchitectureCompatibilityRequestV1,
    ) -> ResponseT:
        """Integrate one validated, exactly compatible reference request."""


@dataclass(frozen=True, slots=True)
class ReferenceArchitectureIntegrationResult(Generic[ResponseT]):
    """Internal pairing of the compatibility decision and provider response."""

    translation: ReferenceArchitectureRequestTranslationResultV1
    response: ResponseT


class ReferenceArchitectureIntegrationError(ValueError):
    """Base error raised before a provider-neutral integration can run."""


class ReferenceArchitectureIncompatibleError(
    ReferenceArchitectureIntegrationError
):
    """Raised when a valid request does not identify frozen Aquagear v1."""

    def __init__(
        self,
        translation: ReferenceArchitectureRequestTranslationResultV1,
    ) -> None:
        self.translation = translation
        fields = ", ".join(item.field.value for item in translation.mismatches)
        super().__init__(
            "Reference architecture request is incompatible"
            + (f": {fields}" if fields else ".")
        )


class ProviderNeutralReferenceIntegrationAdapter(Generic[ResponseT]):
    """Guard an injected integration port with the frozen v1 handshake."""

    __slots__ = ("_port",)

    def __init__(
        self,
        port: ReferenceArchitectureIntegrationPort[ResponseT],
    ) -> None:
        integrate = getattr(port, "integrate", None)
        if not callable(integrate):
            raise TypeError("Integration port must define a callable integrate method.")
        self._port = port

    def integrate(
        self,
        payload: object,
    ) -> ReferenceArchitectureIntegrationResult[ResponseT]:
        """Validate compatibility, reject mismatches, then invoke the port once.

        Structural translation errors pass through unchanged. Provider errors are
        also deliberately preserved; normalization belongs to a later contract.
        """

        translation = translate_reference_architecture_compatibility_request(
            payload  # type: ignore[arg-type]
        )
        if not translation.compatible:
            raise ReferenceArchitectureIncompatibleError(translation)

        response = self._port.integrate(translation.request)
        return ReferenceArchitectureIntegrationResult(
            translation=translation,
            response=response,
        )
