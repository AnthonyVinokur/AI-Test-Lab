from __future__ import annotations

from types import MappingProxyType

import pytest
from pydantic import ValidationError

from src.public_contract import serialize_public_contract
from src.reference_architecture_request_response_correlation import (
    REFERENCE_ARCHITECTURE_CORRELATION_CONTRACT_NAME,
    REFERENCE_ARCHITECTURE_CORRELATION_CONTRACT_VERSION,
    ReferenceArchitectureCorrelationField,
    ReferenceArchitectureRequestResponseCorrelationError,
    ReferenceArchitectureRequestResponseCorrelationResultV1,
    correlate_reference_architecture_request_response,
)
from src.reference_architecture_response_translation import (
    ProviderNeutralIntegrationResponseV1,
    translate_reference_architecture_response,
)


def request_identity(**changes: object) -> dict[str, object]:
    value: dict[str, object] = {
        "contract_version": "v1",
        "integration_id": "integration-7",
        "correlation_id": "correlation-11",
        "source_system": "ai-test-lab",
        "operation": "enforce",
    }
    value.update(changes)
    return value


def response_payload(**changes: object) -> dict[str, object]:
    value: dict[str, object] = {
        "contract_version": "v1",
        "integration_id": "integration-7",
        "correlation_id": "correlation-11",
        "source_system": "aquagear-reference-app",
        "operation": "enforce",
        "status": "completed",
        "artifact": None,
        "metadata": (),
    }
    value.update(changes)
    return value


def translated_response(**changes: object):
    return translate_reference_architecture_response(response_payload(**changes))


def test_correlates_translated_response_to_originating_request() -> None:
    result = correlate_reference_architecture_request_response(
        request_identity(), translated_response()
    )

    assert result.correlated is True
    assert result.mismatches == ()
    assert result.contract_name == REFERENCE_ARCHITECTURE_CORRELATION_CONTRACT_NAME
    assert (
        result.correlation_contract_version
        == REFERENCE_ARCHITECTURE_CORRELATION_CONTRACT_VERSION
    )


def test_accepts_validated_response_dto_directly() -> None:
    response = translated_response().response
    result = correlate_reference_architecture_request_response(
        request_identity(), response
    )
    assert result.response is response
    assert result.correlated is True


@pytest.mark.parametrize(
    ("response_change", "expected_field"),
    [
        ({"integration_id": "other-integration"}, "integration_id"),
        ({"correlation_id": "other-correlation"}, "correlation_id"),
        ({"operation": "return"}, "operation"),
    ],
)
def test_returns_deterministic_mismatch_for_well_formed_identity_difference(
    response_change: dict[str, object], expected_field: str
) -> None:
    result = correlate_reference_architecture_request_response(
        request_identity(), translated_response(**response_change)
    )
    assert result.correlated is False
    assert [mismatch.field.value for mismatch in result.mismatches] == [
        expected_field
    ]


def test_reports_multiple_mismatches_in_contract_order() -> None:
    result = correlate_reference_architecture_request_response(
        request_identity(),
        translated_response(
            integration_id="other-integration",
            correlation_id="other-correlation",
            operation="return",
        ),
    )
    assert tuple(mismatch.field for mismatch in result.mismatches) == (
        ReferenceArchitectureCorrelationField.INTEGRATION_ID,
        ReferenceArchitectureCorrelationField.CORRELATION_ID,
        ReferenceArchitectureCorrelationField.OPERATION,
    )


def test_source_systems_may_differ() -> None:
    result = correlate_reference_architecture_request_response(
        request_identity(source_system="caller"),
        translated_response(source_system="provider"),
    )
    assert result.correlated is True


def test_mapping_proxy_request_is_supported_without_mutation() -> None:
    original = request_identity()
    request = MappingProxyType(original)
    correlate_reference_architecture_request_response(request, translated_response())
    assert dict(request) == original


@pytest.mark.parametrize(
    "candidate",
    [
        None,
        [],
        {},
        request_identity(extra="not-public"),
        request_identity(correlation_id=""),
        request_identity(integration_id=7),
        request_identity(contract_version="v2"),
        request_identity(operation="unknown"),
    ],
)
def test_rejects_malformed_request_identity(candidate: object) -> None:
    with pytest.raises(
        ReferenceArchitectureRequestResponseCorrelationError,
        match="request identity",
    ):
        correlate_reference_architecture_request_response(  # type: ignore[arg-type]
            candidate, translated_response()
        )


def test_rejects_untranslated_response_mapping() -> None:
    with pytest.raises(
        ReferenceArchitectureRequestResponseCorrelationError,
        match="validated response",
    ):
        correlate_reference_architecture_request_response(
            request_identity(), response_payload()  # type: ignore[arg-type]
        )


def test_public_models_are_immutable_and_forbid_extra_fields() -> None:
    result = correlate_reference_architecture_request_response(
        request_identity(), translated_response()
    )
    with pytest.raises((ValidationError, TypeError)):
        result.correlated = False  # type: ignore[misc]
    with pytest.raises(ValidationError):
        ReferenceArchitectureRequestResponseCorrelationResultV1.model_validate(
            {
                **serialize_public_contract(result),
                "internal_provider_state": "must-not-cross-boundary",
            }
        )


def test_result_consistency_is_enforced() -> None:
    response: ProviderNeutralIntegrationResponseV1 = translated_response().response
    with pytest.raises(ValidationError, match="correlated must be true"):
        ReferenceArchitectureRequestResponseCorrelationResultV1(
            correlated=False,
            request=request_identity(),
            response=response,
            mismatches=(),
        )


def test_public_serialization_contains_no_provider_internals() -> None:
    result = correlate_reference_architecture_request_response(
        request_identity(), translated_response()
    )
    assert serialize_public_contract(result) == {
        "contract_name": REFERENCE_ARCHITECTURE_CORRELATION_CONTRACT_NAME,
        "correlation_contract_version": "1.0",
        "correlated": True,
        "request": request_identity(),
        "response": {
            **response_payload(),
            "metadata": [],
        },
        "mismatches": [],
    }
