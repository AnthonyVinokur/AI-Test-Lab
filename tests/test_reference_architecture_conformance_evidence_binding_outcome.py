from __future__ import annotations

import hashlib
import json

import pytest
from pydantic import ValidationError

from src.public_contract import serialize_public_contract
from src.reference_architecture_compatibility_contract import (
    supported_reference_architecture_compatibility_contract,
)
from src.reference_architecture_conformance_evidence_binding_failure_normalization import (
    bind_reference_architecture_conformance_evidence_with_normalized_failure,
)
from src.reference_architecture_conformance_evidence_binding_outcome import (
    REFERENCE_ARCHITECTURE_CONFORMANCE_EVIDENCE_BINDING_OUTCOME_CONTRACT_NAME,
    ReferenceArchitectureConformanceEvidenceBindingOutcomeV1,
    bind_public_reference_architecture_conformance_evidence,
    project_reference_architecture_conformance_evidence_binding_outcome,
)
from src.reference_architecture_round_trip_orchestration import (
    CorrelatedReferenceArchitectureRoundTripOrchestrator,
)


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def evidence_document() -> bytes:
    evaluation = {"conforms": True, "violations": []}
    unsigned = {
        "schema_version": "1.0",
        "architecture_version": "v1",
        "evaluation": evaluation,
        "evaluation_sha256": canonical_sha256(evaluation),
    }
    evidence = {**unsigned, "evidence_sha256": canonical_sha256(unsigned)}
    return json.dumps(
        {
            "schema": "aquagear.reference-architecture-conformance-evidence",
            "version": "1",
            "evidence": evidence,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def response(*, artifact: object = ...) -> dict[str, object]:
    evidence_artifact: object = {
        "artifact_id": "evidence-7",
        "artifact_type": "conformance-evidence",
        "content_type": "application/json",
        "payload": evidence_document(),
        "schema_version": "1.0",
    }
    return {
        "contract_version": "v1",
        "integration_id": "integration-7",
        "correlation_id": "correlation-11",
        "source_system": "aquagear-reference-app",
        "operation": "enforce",
        "status": "completed",
        "artifact": evidence_artifact if artifact is ... else artifact,
        "metadata": (),
    }


class Port:
    def __init__(self, output: dict[str, object]) -> None:
        self.output = output

    def integrate(self, request: object) -> dict[str, object]:
        return self.output


def round_trip(*, artifact: object = ...):
    identity = {
        "contract_version": "v1",
        "integration_id": "integration-7",
        "correlation_id": "correlation-11",
        "source_system": "ai-test-lab",
        "operation": "enforce",
    }
    compatibility = serialize_public_contract(
        supported_reference_architecture_compatibility_contract()
    )
    return CorrelatedReferenceArchitectureRoundTripOrchestrator(
        Port(response(artifact=artifact))
    ).execute(compatibility, identity)


def test_success_projects_only_identifiers_and_verified_evidence() -> None:
    outcome = bind_public_reference_architecture_conformance_evidence(round_trip())

    assert outcome.succeeded is True
    assert outcome.failure is None
    assert outcome.binding is not None
    assert outcome.binding.integration_id == "integration-7"
    assert outcome.binding.correlation_id == "correlation-11"
    assert outcome.binding.evidence.evidence.evaluation["conforms"] is True


def test_failure_projects_only_the_normalized_public_failure() -> None:
    outcome = bind_public_reference_architecture_conformance_evidence(
        round_trip(artifact=None)
    )

    assert outcome.succeeded is False
    assert outcome.binding is None
    assert outcome.failure is not None
    assert outcome.failure.code.value == "missing_evidence_artifact"


def test_projection_accepts_an_a0206_normalized_result() -> None:
    normalized = (
        bind_reference_architecture_conformance_evidence_with_normalized_failure(
            round_trip()
        )
    )

    outcome = project_reference_architecture_conformance_evidence_binding_outcome(
        normalized
    )

    assert outcome.binding is not None
    assert outcome.binding.evidence.evidence.architecture_version == "v1"


def test_projection_rejects_an_unrecognized_internal_value() -> None:
    with pytest.raises(TypeError, match="A.02.06"):
        project_reference_architecture_conformance_evidence_binding_outcome(
            object()  # type: ignore[arg-type]
        )


@pytest.mark.parametrize(
    "payload",
    [
        {"succeeded": True},
        {"succeeded": False},
        {"succeeded": False, "binding": {}},
        {
            "succeeded": True,
            "binding": {
                "integration_id": "integration-7",
                "correlation_id": "correlation-11",
                "evidence": {},
            },
            "failure": {
                "stage": "binding",
                "code": "evidence_binding_failed",
                "message": "The conformance evidence could not be bound.",
            },
        },
    ],
)
def test_public_outcome_fails_closed_on_inconsistent_branches(
    payload: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        ReferenceArchitectureConformanceEvidenceBindingOutcomeV1.model_validate(
            payload
        )


def test_public_schema_and_contract_identity_are_stable() -> None:
    serialized = serialize_public_contract(
        bind_public_reference_architecture_conformance_evidence(round_trip())
    )

    assert serialized["contract_name"] == (
        REFERENCE_ARCHITECTURE_CONFORMANCE_EVIDENCE_BINDING_OUTCOME_CONTRACT_NAME
    )
    assert serialized["outcome_contract_version"] == "1.0"
    assert set(serialized) == {
        "contract_name",
        "outcome_contract_version",
        "succeeded",
        "binding",
        "failure",
    }
    assert set(serialized["binding"]) == {
        "integration_id",
        "correlation_id",
        "evidence",
    }


def test_success_excludes_response_transport_and_internal_state() -> None:
    serialized = serialize_public_contract(
        bind_public_reference_architecture_conformance_evidence(round_trip())
    )
    text = json.dumps(serialized, sort_keys=True)

    for forbidden in (
        "artifact",
        "payload",
        "response",
        "metadata",
        "source_system",
        "traceback",
        "provider",
        "secret",
    ):
        assert forbidden not in text


def test_extra_public_fields_are_rejected() -> None:
    outcome = serialize_public_contract(
        bind_public_reference_architecture_conformance_evidence(round_trip())
    )
    outcome["internal_trace"] = "secret"

    with pytest.raises(ValidationError):
        ReferenceArchitectureConformanceEvidenceBindingOutcomeV1.model_validate(
            outcome
        )


def test_projected_evidence_is_deeply_detached_and_immutable() -> None:
    normalized = (
        bind_reference_architecture_conformance_evidence_with_normalized_failure(
            round_trip()
        )
    )
    outcome = project_reference_architecture_conformance_evidence_binding_outcome(
        normalized
    )
    assert normalized.binding is not None
    assert outcome.binding is not None
    assert outcome.binding.evidence is not normalized.binding.evidence
    with pytest.raises(TypeError):
        outcome.binding.evidence.evidence.evaluation["conforms"] = False  # type: ignore[index]


def test_control_flow_exceptions_still_propagate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import src.reference_architecture_conformance_evidence_binding_outcome as module

    def interrupt(value: object) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr(
        module,
        "bind_reference_architecture_conformance_evidence_with_normalized_failure",
        interrupt,
    )
    with pytest.raises(KeyboardInterrupt):
        bind_public_reference_architecture_conformance_evidence(round_trip())
