from __future__ import annotations

from enum import Enum
from typing import Literal

from src.public_contract import PublicContractModel


REFERENCE_ARCHITECTURE_COMPATIBILITY_CONTRACT_NAME = (
    "ai-test-lab.reference-architecture-compatibility"
)
REFERENCE_ARCHITECTURE_COMPATIBILITY_CONTRACT_VERSION = "1.0"

AQUAGEAR_FROZEN_REFERENCE_INTERFACE_VERSION = "v1"
AQUAGEAR_REFERENCE_ARCHITECTURE_CONTRACT_VERSION = "v1"
AQUAGEAR_PROVIDER_NEUTRAL_INTEGRATION_CONTRACT_VERSION = "v1"
AQUAGEAR_REFERENCE_ROUND_TRIP_CLIENT_CONTRACT_VERSION = "v1"
AQUAGEAR_REFERENCE_ARCHITECTURE_CONFORMANCE_CONTRACT_VERSION = "1.0"


class ReferenceArchitectureCompatibility(str, Enum):
    """Possible relationships between two reference-architecture contracts."""

    EXACT = "exact"
    COMPATIBLE = "compatible"
    INCOMPATIBLE = "incompatible"


class ReferenceArchitectureCompatibilityPolicy(str, Enum):
    """Published compatibility policy supported by the initial contract."""

    EXACT_VERSION_MATCH = "exact-version-match"


class ReferenceArchitectureCompatibilityContractV1(PublicContractModel):
    """Public identity and compatibility boundary for Aquagear stable v1.

    This DTO declares only contract identity. Runtime comparison and validation
    belong to the compatibility-validation layer introduced after ATL-A.01.1.
    """

    contract_name: Literal[
        "ai-test-lab.reference-architecture-compatibility"
    ] = REFERENCE_ARCHITECTURE_COMPATIBILITY_CONTRACT_NAME
    compatibility_contract_version: Literal["1.0"] = (
        REFERENCE_ARCHITECTURE_COMPATIBILITY_CONTRACT_VERSION
    )
    reference_interface_version: Literal["v1"] = (
        AQUAGEAR_FROZEN_REFERENCE_INTERFACE_VERSION
    )
    contract_version: Literal["v1"] = (
        AQUAGEAR_REFERENCE_ARCHITECTURE_CONTRACT_VERSION
    )
    provider_neutral_integration_contract_version: Literal["v1"] = (
        AQUAGEAR_PROVIDER_NEUTRAL_INTEGRATION_CONTRACT_VERSION
    )
    reference_round_trip_client_contract_version: Literal["v1"] = (
        AQUAGEAR_REFERENCE_ROUND_TRIP_CLIENT_CONTRACT_VERSION
    )
    reference_architecture_conformance_contract_version: Literal["1.0"] = (
        AQUAGEAR_REFERENCE_ARCHITECTURE_CONFORMANCE_CONTRACT_VERSION
    )
    compatibility_policy: Literal["exact-version-match"] = (
        ReferenceArchitectureCompatibilityPolicy.EXACT_VERSION_MATCH.value
    )


def supported_reference_architecture_compatibility_contract(
) -> ReferenceArchitectureCompatibilityContractV1:
    """Return AI Test Lab's single deliberately supported contract identity."""

    return ReferenceArchitectureCompatibilityContractV1()
