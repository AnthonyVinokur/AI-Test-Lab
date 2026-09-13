from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from src.public_contract import serialize_public_contract
from src.reference_architecture_compatibility_contract import (
    supported_reference_architecture_compatibility_contract,
)
from src.reference_architecture_integration_adapter import (
    ReferenceArchitectureIncompatibleError,
)
from src.reference_architecture_request_response_correlation import (
    ReferenceArchitectureRequestResponseCorrelationError,
)
from src.reference_architecture_response_translation import (
    ReferenceArchitectureResponseTranslationError,
)
from src.reference_architecture_round_trip_orchestration import (
    REFERENCE_ARCHITECTURE_ROUND_TRIP_ORCHESTRATION_CONTRACT_NAME,
    REFERENCE_ARCHITECTURE_ROUND_TRIP_ORCHESTRATION_CONTRACT_VERSION,
    CorrelatedReferenceArchitectureRoundTripOrchestrator,
    ReferenceArchitectureRoundTripResultV1,
    ReferenceArchitectureUncorrelatedResponseError,
    orchestrate_correlated_reference_architecture_round_trip,
)


def compatibility_payload() -> dict[str, str]:
    return serialize_public_contract(
        supported_reference_architecture_compatibility_contract()
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
        "artifact": {
            "artifact_id": "evidence-1",
            "artifact_type": "evidence-bundle",
            "content_type": "application/json",
            "payload": b'{"passed":true}',
            "schema_version": "1.0",
        },
        "metadata": ({"key": "provider", "value": "reference"},),
    }
    value.update(changes)
    return value


class RecordingPort:
    def __init__(self, response: object | None = None) -> None:
        self.response = response if response is not None else response_payload()
        self.requests: list[object] = []

    def integrate(self, request: object):
        self.requests.append(request)
        return self.response


def test_executes_complete_correlated_round_trip_once() -> None:
    port = RecordingPort()
    result = CorrelatedReferenceArchitectureRoundTripOrchestrator(port).execute(
        compatibility_payload(), request_identity()
    )

    assert len(port.requests) == 1
    assert result.integration.translation.compatible is True
    assert result.correlation.correlated is True
    assert result.response is result.response_translation.response
    assert result.response.integration_id == "integration-7"
    assert result.response.artifact is not None
    assert result.response.artifact.payload_base64 == "eyJwYXNzZWQiOnRydWV9"


def test_functional_entry_point_uses_same_contract() -> None:
    result = orchestrate_correlated_reference_architecture_round_trip(
        compatibility_payload(), request_identity(), RecordingPort()
    )
    assert isinstance(result, ReferenceArchitectureRoundTripResultV1)
    assert result.correlation.correlated is True


def test_contract_identity_is_stable() -> None:
    assert REFERENCE_ARCHITECTURE_ROUND_TRIP_ORCHESTRATION_CONTRACT_NAME == (
        "ai-test-lab.reference-architecture-correlated-round-trip-orchestration"
    )
    assert REFERENCE_ARCHITECTURE_ROUND_TRIP_ORCHESTRATION_CONTRACT_VERSION == "1.0"


@pytest.mark.parametrize(
    "invalid_identity",
    [
        None,
        {},
        request_identity(extra="private"),
        request_identity(correlation_id=""),
        request_identity(contract_version="v2"),
    ],
)
def test_invalid_correlation_identity_stops_before_provider(
    invalid_identity: object,
) -> None:
    port = RecordingPort()
    with pytest.raises(ReferenceArchitectureRequestResponseCorrelationError):
        CorrelatedReferenceArchitectureRoundTripOrchestrator(port).execute(
            compatibility_payload(), invalid_identity  # type: ignore[arg-type]
        )
    assert port.requests == []


def test_incompatible_handshake_stops_before_provider() -> None:
    payload = compatibility_payload()
    payload["contract_version"] = "v2"
    port = RecordingPort()

    with pytest.raises(ReferenceArchitectureIncompatibleError):
        CorrelatedReferenceArchitectureRoundTripOrchestrator(port).execute(
            payload, request_identity()
        )
    assert port.requests == []


@pytest.mark.parametrize(
    ("change", "field"),
    [
        ({"integration_id": "wrong"}, "integration_id"),
        ({"correlation_id": "wrong"}, "correlation_id"),
        ({"operation": "return"}, "operation"),
    ],
)
def test_mismatched_response_fails_closed(
    change: dict[str, object], field: str
) -> None:
    port = RecordingPort(response_payload(**change))
    with pytest.raises(
        ReferenceArchitectureUncorrelatedResponseError,
        match=field,
    ) as caught:
        CorrelatedReferenceArchitectureRoundTripOrchestrator(port).execute(
            compatibility_payload(), request_identity()
        )

    assert len(port.requests) == 1
    assert caught.value.correlation.correlated is False
    assert [m.field.value for m in caught.value.correlation.mismatches] == [field]


def test_malformed_provider_response_preserves_translation_error() -> None:
    port = RecordingPort({"provider_private": "must-not-cross"})
    with pytest.raises(ReferenceArchitectureResponseTranslationError):
        CorrelatedReferenceArchitectureRoundTripOrchestrator(port).execute(
            compatibility_payload(), request_identity()
        )
    assert len(port.requests) == 1


class FailingPort:
    def integrate(self, request: object):
        raise RuntimeError("provider unavailable")


def test_provider_error_is_preserved() -> None:
    with pytest.raises(RuntimeError, match="provider unavailable"):
        CorrelatedReferenceArchitectureRoundTripOrchestrator(FailingPort()).execute(
            compatibility_payload(), request_identity()
        )


def test_inputs_are_not_mutated() -> None:
    compatibility = compatibility_payload()
    identity = request_identity()
    original_compatibility = dict(compatibility)
    original_identity = dict(identity)

    CorrelatedReferenceArchitectureRoundTripOrchestrator(RecordingPort()).execute(
        compatibility, identity
    )

    assert compatibility == original_compatibility
    assert identity == original_identity


def test_result_is_immutable_and_not_implicitly_public() -> None:
    result = CorrelatedReferenceArchitectureRoundTripOrchestrator(
        RecordingPort()
    ).execute(compatibility_payload(), request_identity())

    with pytest.raises(FrozenInstanceError):
        result.correlation = result.correlation  # type: ignore[misc]
    assert not hasattr(result, "model_dump")


def test_error_exposes_only_stable_mismatch_names() -> None:
    port = RecordingPort(
        response_payload(
            integration_id="wrong-integration",
            correlation_id="wrong-correlation",
        )
    )
    with pytest.raises(
        ReferenceArchitectureUncorrelatedResponseError,
        match=r"integration_id, correlation_id$",
    ):
        CorrelatedReferenceArchitectureRoundTripOrchestrator(port).execute(
            compatibility_payload(), request_identity()
        )
