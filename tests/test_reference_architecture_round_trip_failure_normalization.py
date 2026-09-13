from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from src.public_contract import serialize_public_contract
from src.reference_architecture_compatibility_contract import (
    supported_reference_architecture_compatibility_contract,
)
from src.reference_architecture_round_trip_failure_normalization import (
    REFERENCE_ARCHITECTURE_FAILURE_NORMALIZATION_CONTRACT_NAME,
    FailureNormalizingReferenceArchitectureRoundTripOrchestrator,
    ReferenceArchitectureFailureCode,
    ReferenceArchitectureFailureStage,
    ReferenceArchitectureNormalizedRoundTripResultV1,
    normalize_reference_architecture_round_trip_failure,
    orchestrate_reference_architecture_round_trip_with_normalized_failure,
)


def compatibility_payload() -> dict[str, str]:
    return serialize_public_contract(
        supported_reference_architecture_compatibility_contract()
    )


def identity(**changes: object) -> dict[str, object]:
    value: dict[str, object] = {
        "contract_version": "v1",
        "integration_id": "integration-7",
        "correlation_id": "correlation-11",
        "source_system": "ai-test-lab",
        "operation": "enforce",
    }
    value.update(changes)
    return value


def response(**changes: object) -> dict[str, object]:
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


class Port:
    def __init__(self, output: object = None, error: Exception | None = None) -> None:
        self.output = response() if output is None else output
        self.error = error
        self.calls = 0

    def integrate(self, request: object):
        self.calls += 1
        if self.error is not None:
            raise self.error
        return self.output


def test_success_is_preserved_without_public_failure() -> None:
    outcome = FailureNormalizingReferenceArchitectureRoundTripOrchestrator(
        Port()
    ).execute(compatibility_payload(), identity())
    assert outcome.succeeded is True
    assert outcome.result is not None
    assert outcome.failure is None
    assert outcome.result.correlation.correlated is True


@pytest.mark.parametrize(
    ("compatibility", "request_identity", "port", "stage", "code", "called"),
    [
        (None, identity(), Port(), "compatibility", "invalid_compatibility_request", 0),
        (compatibility_payload(), {}, Port(), "request_validation", "invalid_request_identity", 0),
        (compatibility_payload(), identity(), Port(error=RuntimeError("token=secret")), "provider_invocation", "provider_invocation_failed", 1),
        (compatibility_payload(), identity(), Port(output={"private": "secret"}), "response_translation", "invalid_provider_response", 1),
        (compatibility_payload(), identity(), Port(output=response(correlation_id="other")), "correlation", "uncorrelated_provider_response", 1),
    ],
)
def test_failures_have_stable_stage_and_code(
    compatibility: object,
    request_identity: dict[str, object],
    port: Port,
    stage: str,
    code: str,
    called: int,
) -> None:
    outcome = FailureNormalizingReferenceArchitectureRoundTripOrchestrator(
        port
    ).execute(compatibility, request_identity)
    assert outcome.succeeded is False
    assert outcome.failure is not None
    assert outcome.failure.stage.value == stage
    assert outcome.failure.code.value == code
    assert port.calls == called


def test_provider_failure_is_retryable_and_redacted() -> None:
    outcome = orchestrate_reference_architecture_round_trip_with_normalized_failure(
        compatibility_payload(), identity(), Port(error=RuntimeError("api-key-secret"))
    )
    assert outcome.failure is not None
    assert outcome.failure.retryable is True
    serialized = outcome.failure.model_dump(mode="json")
    assert "api-key-secret" not in str(serialized)
    assert set(serialized) == {
        "contract_name", "failure_contract_version", "stage", "code", "message",
        "retryable", "integration_id", "correlation_id",
    }


def test_contract_identity_and_safe_request_identifiers_are_stable() -> None:
    failure = normalize_reference_architecture_round_trip_failure(
        RuntimeError("private"), identity()
    )
    assert failure.contract_name == REFERENCE_ARCHITECTURE_FAILURE_NORMALIZATION_CONTRACT_NAME
    assert failure.failure_contract_version == "1.0"
    assert failure.integration_id == "integration-7"
    assert failure.correlation_id == "correlation-11"


def test_non_provider_failures_are_not_retryable() -> None:
    outcome = FailureNormalizingReferenceArchitectureRoundTripOrchestrator(
        Port(output=response(operation="return"))
    ).execute(compatibility_payload(), identity())
    assert outcome.failure is not None
    assert outcome.failure.retryable is False


def test_internal_outcome_requires_exactly_one_branch_and_is_immutable() -> None:
    with pytest.raises(ValueError, match="Exactly one"):
        ReferenceArchitectureNormalizedRoundTripResultV1()
    outcome = FailureNormalizingReferenceArchitectureRoundTripOrchestrator(
        Port()
    ).execute(compatibility_payload(), identity())
    with pytest.raises(FrozenInstanceError):
        outcome.result = None  # type: ignore[misc]


def test_control_flow_exceptions_are_not_normalized() -> None:
    class InterruptingPort:
        def integrate(self, request: object):
            raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        FailureNormalizingReferenceArchitectureRoundTripOrchestrator(
            InterruptingPort()
        ).execute(compatibility_payload(), identity())
