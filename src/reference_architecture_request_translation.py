from __future__ import annotations

from collections.abc import Mapping
from enum import Enum
from typing import Annotated, Any, Literal, Self

from pydantic import StringConstraints, ValidationError, model_validator

from src.public_contract import PublicContractModel
from src.reference_architecture_compatibility_contract import (
    REFERENCE_ARCHITECTURE_COMPATIBILITY_CONTRACT_NAME,
    REFERENCE_ARCHITECTURE_COMPATIBILITY_CONTRACT_VERSION,
    ReferenceArchitectureCompatibility,
    ReferenceArchitectureCompatibilityContractV1,
    supported_reference_architecture_compatibility_contract,
)


REFERENCE_ARCHITECTURE_REQUEST_TRANSLATION_CONTRACT_NAME = (
    "ai-test-lab.reference-architecture-request-translation"
)
REFERENCE_ARCHITECTURE_REQUEST_TRANSLATION_CONTRACT_VERSION = "1.0"

IdentityString = Annotated[
    str,
    StringConstraints(strict=True, min_length=1),
]


class ReferenceArchitectureCompatibilityField(str, Enum):
    """Stable names of version-bearing fields compared by the translator."""

    CONTRACT_NAME = "contract_name"
    COMPATIBILITY_CONTRACT_VERSION = "compatibility_contract_version"
    REFERENCE_INTERFACE_VERSION = "reference_interface_version"
    CONTRACT_VERSION = "contract_version"
    PROVIDER_NEUTRAL_INTEGRATION_CONTRACT_VERSION = (
        "provider_neutral_integration_contract_version"
    )
    REFERENCE_ROUND_TRIP_CLIENT_CONTRACT_VERSION = (
        "reference_round_trip_client_contract_version"
    )
    REFERENCE_ARCHITECTURE_CONFORMANCE_CONTRACT_VERSION = (
        "reference_architecture_conformance_contract_version"
    )
    COMPATIBILITY_POLICY = "compatibility_policy"


class ReferenceArchitectureCompatibilityRequestV1(PublicContractModel):
    """Untrusted public identity request before compatibility is decided."""

    contract_name: IdentityString
    compatibility_contract_version: IdentityString
    reference_interface_version: IdentityString
    contract_version: IdentityString
    provider_neutral_integration_contract_version: IdentityString
    reference_round_trip_client_contract_version: IdentityString
    reference_architecture_conformance_contract_version: IdentityString
    compatibility_policy: IdentityString


class ReferenceArchitectureCompatibilityMismatchV1(PublicContractModel):
    """One deterministic difference from the supported Aquagear v1 identity."""

    field: ReferenceArchitectureCompatibilityField
    expected: IdentityString
    actual: IdentityString


class ReferenceArchitectureRequestTranslationResultV1(PublicContractModel):
    """Public result of translating and comparing one compatibility request."""

    contract_name: Literal[
        "ai-test-lab.reference-architecture-request-translation"
    ] = REFERENCE_ARCHITECTURE_REQUEST_TRANSLATION_CONTRACT_NAME
    translation_contract_version: Literal["1.0"] = (
        REFERENCE_ARCHITECTURE_REQUEST_TRANSLATION_CONTRACT_VERSION
    )
    compatibility: ReferenceArchitectureCompatibility
    compatible: bool
    request: ReferenceArchitectureCompatibilityRequestV1
    supported: ReferenceArchitectureCompatibilityContractV1
    mismatches: tuple[ReferenceArchitectureCompatibilityMismatchV1, ...] = ()

    @model_validator(mode="after")
    def validate_decision_consistency(self) -> Self:
        exact = self.compatibility is ReferenceArchitectureCompatibility.EXACT
        if self.compatible is not exact:
            raise ValueError(
                "compatible must be true exactly when compatibility is exact"
            )
        if exact == bool(self.mismatches):
            raise ValueError(
                "exact results cannot contain mismatches and incompatible "
                "results require at least one mismatch"
            )
        if self.compatibility is ReferenceArchitectureCompatibility.COMPATIBLE:
            raise ValueError(
                "compatible relationship is not defined by translation v1"
            )
        return self


class ReferenceArchitectureRequestTranslationError(ValueError):
    """Raised when an incoming request cannot be translated structurally."""


_IDENTITY_FIELDS = tuple(
    field.value for field in ReferenceArchitectureCompatibilityField
)


def translate_reference_architecture_compatibility_request(
    payload: Mapping[str, Any],
) -> ReferenceArchitectureRequestTranslationResultV1:
    """Translate an external identity request and compare it with frozen v1.

    Structural failures raise ``ReferenceArchitectureRequestTranslationError``.
    Well-formed but unsupported identities return an ``incompatible`` result.
    The function does not import or execute Aquagear code.
    """

    if not isinstance(payload, Mapping):
        raise ReferenceArchitectureRequestTranslationError(
            "Compatibility request must be a mapping."
        )

    try:
        request = ReferenceArchitectureCompatibilityRequestV1.model_validate(
            dict(payload)
        )
    except ValidationError as exc:
        raise ReferenceArchitectureRequestTranslationError(
            "Compatibility request does not match the public request schema."
        ) from exc

    supported = supported_reference_architecture_compatibility_contract()
    mismatches: list[ReferenceArchitectureCompatibilityMismatchV1] = []

    for field_name in _IDENTITY_FIELDS:
        expected = getattr(supported, field_name)
        actual = getattr(request, field_name)
        if actual != expected:
            mismatches.append(
                ReferenceArchitectureCompatibilityMismatchV1(
                    field=ReferenceArchitectureCompatibilityField(field_name),
                    expected=expected,
                    actual=actual,
                )
            )

    compatibility = (
        ReferenceArchitectureCompatibility.EXACT
        if not mismatches
        else ReferenceArchitectureCompatibility.INCOMPATIBLE
    )
    return ReferenceArchitectureRequestTranslationResultV1(
        compatibility=compatibility,
        compatible=compatibility is ReferenceArchitectureCompatibility.EXACT,
        request=request,
        supported=supported,
        mismatches=tuple(mismatches),
    )
