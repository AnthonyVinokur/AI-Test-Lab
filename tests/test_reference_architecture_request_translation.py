from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.public_contract import serialize_public_contract
from src.reference_architecture_compatibility_contract import (
    ReferenceArchitectureCompatibility,
    supported_reference_architecture_compatibility_contract,
)
from src.reference_architecture_request_translation import (
    REFERENCE_ARCHITECTURE_REQUEST_TRANSLATION_CONTRACT_NAME,
    ReferenceArchitectureCompatibilityField,
    ReferenceArchitectureCompatibilityMismatchV1,
    ReferenceArchitectureRequestTranslationError,
    ReferenceArchitectureRequestTranslationResultV1,
    translate_reference_architecture_compatibility_request,
)


def supported_payload() -> dict[str, str]:
    return serialize_public_contract(
        supported_reference_architecture_compatibility_contract()
    )


def test_exact_request_translates_to_exact_compatible_result() -> None:
    result = translate_reference_architecture_compatibility_request(
        supported_payload()
    )

    assert result.compatibility is ReferenceArchitectureCompatibility.EXACT
    assert result.compatible is True
    assert result.mismatches == ()
    assert serialize_public_contract(result)["contract_name"] == (
        REFERENCE_ARCHITECTURE_REQUEST_TRANSLATION_CONTRACT_NAME
    )


@pytest.mark.parametrize(
    ("field", "actual"),
    [
        ("contract_name", "another.contract"),
        ("compatibility_contract_version", "2.0"),
        ("reference_interface_version", "v2"),
        ("contract_version", "v2"),
        ("provider_neutral_integration_contract_version", "v2"),
        ("reference_round_trip_client_contract_version", "v2"),
        ("reference_architecture_conformance_contract_version", "2.0"),
        ("compatibility_policy", "major-version-match"),
    ],
)
def test_each_identity_mismatch_returns_incompatible_result(
    field: str,
    actual: str,
) -> None:
    payload = supported_payload()
    expected = payload[field]
    payload[field] = actual

    result = translate_reference_architecture_compatibility_request(payload)

    assert result.compatibility is ReferenceArchitectureCompatibility.INCOMPATIBLE
    assert result.compatible is False
    assert result.mismatches == (
        ReferenceArchitectureCompatibilityMismatchV1(
            field=ReferenceArchitectureCompatibilityField(field),
            expected=expected,
            actual=actual,
        ),
    )


def test_multiple_mismatches_use_stable_contract_field_order() -> None:
    payload = supported_payload()
    payload["compatibility_policy"] = "future-policy"
    payload["contract_name"] = "wrong.contract"
    payload["reference_interface_version"] = "v2"

    result = translate_reference_architecture_compatibility_request(payload)

    assert tuple(item.field.value for item in result.mismatches) == (
        "contract_name",
        "reference_interface_version",
        "compatibility_policy",
    )


@pytest.mark.parametrize(
    "payload",
    [
        None,
        [],
        "not-a-request",
        {"contract_name": "incomplete"},
        {**supported_payload(), "unknown": "field"},
        {**supported_payload(), "contract_version": 1},
        {**supported_payload(), "contract_version": ""},
    ],
)
def test_malformed_requests_raise_translation_error(payload: object) -> None:
    with pytest.raises(
        ReferenceArchitectureRequestTranslationError,
        match="Compatibility request",
    ):
        translate_reference_architecture_compatibility_request(
            payload  # type: ignore[arg-type]
        )


def test_result_is_an_immutable_strict_public_contract() -> None:
    result = translate_reference_architecture_compatibility_request(
        supported_payload()
    )

    with pytest.raises(ValidationError):
        result.compatible = False  # type: ignore[misc]

    with pytest.raises(ValidationError):
        ReferenceArchitectureRequestTranslationResultV1(
            compatibility="exact",
            compatible=True,
            request=result.request,
            supported=result.supported,
            internal_score=0.99,
        )

    with pytest.raises(ValidationError):
        ReferenceArchitectureRequestTranslationResultV1(
            compatibility="exact",
            compatible=False,
            request=result.request,
            supported=result.supported,
        )


def test_translation_does_not_mutate_the_input_mapping() -> None:
    payload = supported_payload()
    original = dict(payload)

    translate_reference_architecture_compatibility_request(payload)

    assert payload == original
