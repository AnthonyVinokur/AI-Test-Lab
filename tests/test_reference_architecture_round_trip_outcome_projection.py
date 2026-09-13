from __future__ import annotations

from pydantic import ValidationError
import pytest

from src.public_contract import serialize_public_contract
from src.reference_architecture_compatibility_contract import (
    supported_reference_architecture_compatibility_contract,
)
from src.reference_architecture_round_trip_failure_normalization import (
    FailureNormalizingReferenceArchitectureRoundTripOrchestrator,
)
from src.reference_architecture_round_trip_outcome_projection import (
    REFERENCE_ARCHITECTURE_ROUND_TRIP_OUTCOME_CONTRACT_NAME,
    PublicReferenceArchitectureRoundTripOrchestrator,
    ReferenceArchitectureRoundTripOutcomeV1,
    execute_public_reference_architecture_round_trip,
    project_reference_architecture_round_trip_outcome,
)


def compatibility_payload() -> dict[str, object]:
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


def test_success_projects_only_the_validated_public_response() -> None:
    outcome = PublicReferenceArchitectureRoundTripOrchestrator(Port()).execute(
        compatibility_payload(), identity()
    )
    assert outcome.succeeded is True
    assert outcome.response is not None
    assert outcome.failure is None
    assert outcome.response.integration_id == "integration-7"
    assert outcome.response.correlation_id == "correlation-11"


def test_failure_projects_only_the_normalized_public_failure() -> None:
    outcome = execute_public_reference_architecture_round_trip(
        compatibility_payload(), identity(), Port(error=RuntimeError("secret-token"))
    )
    assert outcome.succeeded is False
    assert outcome.response is None
    assert outcome.failure is not None
    assert outcome.failure.code.value == "provider_invocation_failed"
    assert "secret-token" not in str(outcome.model_dump(mode="json"))


def test_projection_accepts_an_a017_normalized_result() -> None:
    normalized = FailureNormalizingReferenceArchitectureRoundTripOrchestrator(
        Port()
    ).execute(compatibility_payload(), identity())
    outcome = project_reference_architecture_round_trip_outcome(normalized)
    assert outcome.response is not None
    assert outcome.response.status.value == "completed"


def test_projection_rejects_an_unrecognized_internal_value() -> None:
    with pytest.raises(TypeError, match="A.01.7"):
        project_reference_architecture_round_trip_outcome(object())  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "payload",
    [
        {"succeeded": True},
        {"succeeded": False},
        {"succeeded": False, "response": response()},
        {
            "succeeded": True,
            "response": response(),
            "failure": {
                "stage": "provider_invocation",
                "code": "provider_invocation_failed",
                "message": "The provider could not complete the integration request.",
                "retryable": True,
            },
        },
    ],
)
def test_public_outcome_fails_closed_on_inconsistent_branches(
    payload: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        ReferenceArchitectureRoundTripOutcomeV1.model_validate(payload)


def test_public_schema_and_contract_identity_are_stable() -> None:
    outcome = PublicReferenceArchitectureRoundTripOrchestrator(Port()).execute(
        compatibility_payload(), identity()
    )
    serialized = serialize_public_contract(outcome)
    assert serialized["contract_name"] == (
        REFERENCE_ARCHITECTURE_ROUND_TRIP_OUTCOME_CONTRACT_NAME
    )
    assert serialized["outcome_contract_version"] == "1.0"
    assert set(serialized) == {
        "contract_name",
        "outcome_contract_version",
        "succeeded",
        "response",
        "failure",
    }


def test_extra_public_fields_are_rejected() -> None:
    with pytest.raises(ValidationError):
        ReferenceArchitectureRoundTripOutcomeV1.model_validate(
            {"succeeded": True, "response": response(), "internal_trace": "secret"}
        )


def test_input_mappings_are_not_mutated() -> None:
    compatibility = compatibility_payload()
    request_identity = identity()
    compatibility_before = compatibility.copy()
    identity_before = request_identity.copy()
    PublicReferenceArchitectureRoundTripOrchestrator(Port()).execute(
        compatibility, request_identity
    )
    assert compatibility == compatibility_before
    assert request_identity == identity_before


def test_control_flow_exceptions_still_propagate() -> None:
    class InterruptingPort:
        def integrate(self, request: object):
            raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        PublicReferenceArchitectureRoundTripOrchestrator(
            InterruptingPort()
        ).execute(compatibility_payload(), identity())
