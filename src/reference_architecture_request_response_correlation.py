from __future__ import annotations

from collections.abc import Mapping
from enum import Enum
from typing import Annotated, Any, Literal, Self

from pydantic import StringConstraints, ValidationError, model_validator

from src.public_contract import PublicContractModel
from src.reference_architecture_response_translation import (
    ProviderNeutralIntegrationOperationV1,
    ProviderNeutralIntegrationResponseV1,
    ReferenceArchitectureResponseTranslationResultV1,
)


REFERENCE_ARCHITECTURE_CORRELATION_CONTRACT_NAME = (
    "ai-test-lab.reference-architecture-request-response-correlation"
)
REFERENCE_ARCHITECTURE_CORRELATION_CONTRACT_VERSION = "1.0"

NonEmptyString = Annotated[str, StringConstraints(strict=True, min_length=1)]


class ReferenceArchitectureCorrelationField(str, Enum):
    """Stable request fields used to associate a response with its request."""

    CONTRACT_VERSION = "contract_version"
    INTEGRATION_ID = "integration_id"
    CORRELATION_ID = "correlation_id"
    OPERATION = "operation"


class ProviderNeutralIntegrationRequestIdentityV1(PublicContractModel):
    """Minimum frozen request identity required for response correlation."""

    contract_version: Literal["v1"]
    integration_id: NonEmptyString
    correlation_id: NonEmptyString
    source_system: NonEmptyString
    operation: ProviderNeutralIntegrationOperationV1


class ReferenceArchitectureCorrelationMismatchV1(PublicContractModel):
    """One deterministic difference between request and response identity."""

    field: ReferenceArchitectureCorrelationField
    expected: NonEmptyString
    actual: NonEmptyString


class ReferenceArchitectureRequestResponseCorrelationResultV1(PublicContractModel):
    """Public, provider-neutral correlation decision for one response."""

    contract_name: Literal[
        "ai-test-lab.reference-architecture-request-response-correlation"
    ] = REFERENCE_ARCHITECTURE_CORRELATION_CONTRACT_NAME
    correlation_contract_version: Literal["1.0"] = (
        REFERENCE_ARCHITECTURE_CORRELATION_CONTRACT_VERSION
    )
    correlated: bool
    request: ProviderNeutralIntegrationRequestIdentityV1
    response: ProviderNeutralIntegrationResponseV1
    mismatches: tuple[ReferenceArchitectureCorrelationMismatchV1, ...] = ()

    @model_validator(mode="after")
    def validate_decision_consistency(self) -> Self:
        if self.correlated == bool(self.mismatches):
            raise ValueError(
                "correlated must be true exactly when mismatches is empty"
            )
        return self


class ReferenceArchitectureRequestResponseCorrelationError(ValueError):
    """Raised when correlation input does not match the public v1 schema."""


_REQUEST_IDENTITY_FIELDS = frozenset(
    {
        "contract_version",
        "integration_id",
        "correlation_id",
        "source_system",
        "operation",
    }
)
_CORRELATION_FIELDS = tuple(field.value for field in ReferenceArchitectureCorrelationField)


def _translate_request_identity(
    request: Mapping[str, Any],
) -> ProviderNeutralIntegrationRequestIdentityV1:
    if not isinstance(request, Mapping):
        raise ReferenceArchitectureRequestResponseCorrelationError(
            "Provider-neutral request identity must be a mapping."
        )
    copied = dict(request)
    if set(copied) != _REQUEST_IDENTITY_FIELDS:
        raise ReferenceArchitectureRequestResponseCorrelationError(
            "Provider-neutral request identity does not match the frozen v1 schema."
        )
    try:
        return ProviderNeutralIntegrationRequestIdentityV1.model_validate(copied)
    except ValidationError as exc:
        raise ReferenceArchitectureRequestResponseCorrelationError(
            "Provider-neutral request identity does not match the frozen v1 schema."
        ) from exc


def _unwrap_response(
    response: ProviderNeutralIntegrationResponseV1
    | ReferenceArchitectureResponseTranslationResultV1,
) -> ProviderNeutralIntegrationResponseV1:
    if isinstance(response, ReferenceArchitectureResponseTranslationResultV1):
        return response.response
    if isinstance(response, ProviderNeutralIntegrationResponseV1):
        return response
    raise ReferenceArchitectureRequestResponseCorrelationError(
        "Response must be a validated response-translation result or response DTO."
    )


def correlate_reference_architecture_request_response(
    request: Mapping[str, Any],
    response: ProviderNeutralIntegrationResponseV1
    | ReferenceArchitectureResponseTranslationResultV1,
) -> ReferenceArchitectureRequestResponseCorrelationResultV1:
    """Determine whether one validated v1 response belongs to one v1 request.

    Structural failures raise the stable correlation error. Well-formed identity
    differences return ``correlated=False`` with mismatches in contract order.
    ``source_system`` is intentionally not compared: request and response may be
    produced by different provider-neutral systems.
    """

    validated_request = _translate_request_identity(request)
    validated_response = _unwrap_response(response)
    mismatches: list[ReferenceArchitectureCorrelationMismatchV1] = []

    for field_name in _CORRELATION_FIELDS:
        expected_value = getattr(validated_request, field_name)
        actual_value = getattr(validated_response, field_name)
        expected = (
            expected_value.value if isinstance(expected_value, Enum) else expected_value
        )
        actual = actual_value.value if isinstance(actual_value, Enum) else actual_value
        if actual != expected:
            mismatches.append(
                ReferenceArchitectureCorrelationMismatchV1(
                    field=ReferenceArchitectureCorrelationField(field_name),
                    expected=expected,
                    actual=actual,
                )
            )

    return ReferenceArchitectureRequestResponseCorrelationResultV1(
        correlated=not mismatches,
        request=validated_request,
        response=validated_response,
        mismatches=tuple(mismatches),
    )
