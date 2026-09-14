from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.public_contract import serialize_public_contract
from src.reference_architecture_compatibility_contract import (
    AQUAGEAR_FROZEN_REFERENCE_INTERFACE_VERSION,
    AQUAGEAR_PROVIDER_NEUTRAL_INTEGRATION_CONTRACT_VERSION,
    AQUAGEAR_REFERENCE_ARCHITECTURE_CONFORMANCE_CONTRACT_VERSION,
    AQUAGEAR_REFERENCE_ARCHITECTURE_CONTRACT_VERSION,
    AQUAGEAR_REFERENCE_ROUND_TRIP_CLIENT_CONTRACT_VERSION,
    REFERENCE_ARCHITECTURE_COMPATIBILITY_CONTRACT_NAME,
    REFERENCE_ARCHITECTURE_COMPATIBILITY_CONTRACT_VERSION,
    ReferenceArchitectureCompatibility,
    ReferenceArchitectureCompatibilityContractV1,
    ReferenceArchitectureCompatibilityPolicy,
    supported_reference_architecture_compatibility_contract,
)


def test_authoritative_contract_versions_are_frozen() -> None:
    assert REFERENCE_ARCHITECTURE_COMPATIBILITY_CONTRACT_VERSION == "1.0"
    assert AQUAGEAR_FROZEN_REFERENCE_INTERFACE_VERSION == "v1"
    assert AQUAGEAR_REFERENCE_ARCHITECTURE_CONTRACT_VERSION == "v1"
    assert AQUAGEAR_PROVIDER_NEUTRAL_INTEGRATION_CONTRACT_VERSION == "v1"
    assert AQUAGEAR_REFERENCE_ROUND_TRIP_CLIENT_CONTRACT_VERSION == "v1"
    assert (
        AQUAGEAR_REFERENCE_ARCHITECTURE_CONFORMANCE_CONTRACT_VERSION
        == "1.0"
    )


def test_supported_contract_contains_only_public_identity_data() -> None:
    contract = supported_reference_architecture_compatibility_contract()

    assert serialize_public_contract(contract) == {
        "contract_name": REFERENCE_ARCHITECTURE_COMPATIBILITY_CONTRACT_NAME,
        "compatibility_contract_version": "1.0",
        "reference_interface_version": "v1",
        "contract_version": "v1",
        "provider_neutral_integration_contract_version": "v1",
        "reference_round_trip_client_contract_version": "v1",
        "reference_architecture_conformance_contract_version": "1.0",
        "compatibility_policy": "exact-version-match",
    }


def test_compatibility_relationship_values_are_stable() -> None:
    assert tuple(item.value for item in ReferenceArchitectureCompatibility) == (
        "exact",
        "compatible",
        "incompatible",
    )


def test_initial_policy_requires_an_exact_version_match() -> None:
    assert (
        ReferenceArchitectureCompatibilityPolicy.EXACT_VERSION_MATCH.value
        == "exact-version-match"
    )


@pytest.mark.parametrize(
    ("field", "unsupported_value"),
    [
        ("compatibility_contract_version", "2.0"),
        ("reference_interface_version", "v2"),
        ("contract_version", "v2"),
        ("provider_neutral_integration_contract_version", "v2"),
        ("reference_round_trip_client_contract_version", "v2"),
        ("reference_architecture_conformance_contract_version", "2.0"),
        ("compatibility_policy", "major-version-match"),
    ],
)
def test_unsupported_or_mismatched_contract_values_are_rejected(
    field: str,
    unsupported_value: str,
) -> None:
    with pytest.raises(ValidationError):
        ReferenceArchitectureCompatibilityContractV1(
            **{field: unsupported_value}
        )


def test_wrong_contract_name_is_rejected() -> None:
    with pytest.raises(ValidationError):
        ReferenceArchitectureCompatibilityContractV1(
            contract_name="another.compatibility-contract"
        )


def test_unknown_fields_are_rejected() -> None:
    with pytest.raises(ValidationError):
        ReferenceArchitectureCompatibilityContractV1(
            internal_risk_score=0.98
        )


def test_contract_is_immutable() -> None:
    contract = supported_reference_architecture_compatibility_contract()

    with pytest.raises(ValidationError):
        contract.contract_version = "v2"  # type: ignore[misc]


def test_factory_returns_independent_contract_instances() -> None:
    first = supported_reference_architecture_compatibility_contract()
    second = supported_reference_architecture_compatibility_contract()

    assert first == second
    assert first is not second
