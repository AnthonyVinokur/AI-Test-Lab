from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from src.public_contract import serialize_public_contract
from src.reference_architecture_compatibility_contract import (
    ReferenceArchitectureCompatibility,
    supported_reference_architecture_compatibility_contract,
)
from src.reference_architecture_integration_adapter import (
    ProviderNeutralReferenceIntegrationAdapter,
    ReferenceArchitectureIncompatibleError,
    ReferenceArchitectureIntegrationResult,
)
from src.reference_architecture_request_translation import (
    ReferenceArchitectureCompatibilityRequestV1,
    ReferenceArchitectureRequestTranslationError,
)


def supported_payload() -> dict[str, str]:
    return serialize_public_contract(
        supported_reference_architecture_compatibility_contract()
    )


class RecordingPort:
    def __init__(self, response: object = "accepted") -> None:
        self.response = response
        self.requests: list[ReferenceArchitectureCompatibilityRequestV1] = []

    def integrate(
        self,
        request: ReferenceArchitectureCompatibilityRequestV1,
    ) -> object:
        self.requests.append(request)
        return self.response


def test_exact_request_invokes_port_once_with_validated_request() -> None:
    port = RecordingPort({"reference_id": "ref-001"})
    adapter = ProviderNeutralReferenceIntegrationAdapter(port)

    result = adapter.integrate(supported_payload())

    assert len(port.requests) == 1
    assert port.requests[0] == result.translation.request
    assert result.translation.compatibility is ReferenceArchitectureCompatibility.EXACT
    assert result.response == {"reference_id": "ref-001"}


def test_adapter_returns_provider_response_without_rewriting_it() -> None:
    response = object()
    result = ProviderNeutralReferenceIntegrationAdapter(
        RecordingPort(response)
    ).integrate(supported_payload())

    assert result.response is response


def test_incompatible_request_stops_before_port_invocation() -> None:
    port = RecordingPort()
    payload = supported_payload()
    payload["contract_version"] = "v2"

    with pytest.raises(ReferenceArchitectureIncompatibleError) as caught:
        ProviderNeutralReferenceIntegrationAdapter(port).integrate(payload)

    assert port.requests == []
    assert caught.value.translation.compatible is False
    assert tuple(
        mismatch.field.value for mismatch in caught.value.translation.mismatches
    ) == ("contract_version",)


def test_incompatible_error_contains_only_stable_mismatch_field_names() -> None:
    payload = supported_payload()
    payload["contract_name"] = "unsupported.contract"
    payload["compatibility_policy"] = "future-policy"

    with pytest.raises(
        ReferenceArchitectureIncompatibleError,
        match=r"contract_name, compatibility_policy$",
    ):
        ProviderNeutralReferenceIntegrationAdapter(RecordingPort()).integrate(
            payload
        )


@pytest.mark.parametrize("payload", [None, [], {}, {"unknown": "value"}])
def test_malformed_request_preserves_translation_error(payload: object) -> None:
    port = RecordingPort()

    with pytest.raises(ReferenceArchitectureRequestTranslationError):
        ProviderNeutralReferenceIntegrationAdapter(port).integrate(payload)

    assert port.requests == []


class FailingPort:
    def integrate(
        self,
        request: ReferenceArchitectureCompatibilityRequestV1,
    ) -> object:
        raise RuntimeError("provider unavailable")


def test_port_error_is_not_reclassified_or_exposed_as_compatibility_error() -> None:
    with pytest.raises(RuntimeError, match="provider unavailable"):
        ProviderNeutralReferenceIntegrationAdapter(FailingPort()).integrate(
            supported_payload()
        )


@pytest.mark.parametrize("port", [None, object(), lambda: None])
def test_constructor_rejects_objects_without_integration_port(port: object) -> None:
    with pytest.raises(TypeError, match="callable integrate"):
        ProviderNeutralReferenceIntegrationAdapter(port)  # type: ignore[arg-type]


def test_result_is_immutable() -> None:
    result = ProviderNeutralReferenceIntegrationAdapter(
        RecordingPort()
    ).integrate(supported_payload())

    with pytest.raises(FrozenInstanceError):
        result.response = "changed"  # type: ignore[misc]


def test_result_type_does_not_claim_to_be_a_public_contract() -> None:
    result = ProviderNeutralReferenceIntegrationAdapter(
        RecordingPort()
    ).integrate(supported_payload())

    assert isinstance(result, ReferenceArchitectureIntegrationResult)
    assert not hasattr(result, "model_dump")


def test_adapter_does_not_mutate_input_mapping() -> None:
    payload = supported_payload()
    original = dict(payload)

    ProviderNeutralReferenceIntegrationAdapter(RecordingPort()).integrate(payload)

    assert payload == original
