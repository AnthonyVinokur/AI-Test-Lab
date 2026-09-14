from __future__ import annotations

import hashlib
import json
from dataclasses import FrozenInstanceError, replace

import pytest

from src.public_contract import serialize_public_contract
from src.reference_architecture_compatibility_contract import (
    supported_reference_architecture_compatibility_contract,
)
from src.reference_architecture_conformance_evidence_binding_failure_normalization import (
    REFERENCE_ARCHITECTURE_CONFORMANCE_EVIDENCE_BINDING_FAILURE_CONTRACT_NAME,
    ReferenceArchitectureNormalizedConformanceEvidenceBindingV1,
    bind_reference_architecture_conformance_evidence_with_normalized_failure,
)
from src.reference_architecture_request_response_correlation import (
    ReferenceArchitectureRequestResponseCorrelationResultV1,
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


def evidence_document(*, corrupt_digest: bool = False) -> bytes:
    evaluation = {"conforms": True, "violations": []}
    unsigned = {
        "schema_version": "1.0",
        "architecture_version": "v1",
        "evaluation": evaluation,
        "evaluation_sha256": canonical_sha256(evaluation),
    }
    evidence = {
        **unsigned,
        "evidence_sha256": "0" * 64 if corrupt_digest else canonical_sha256(unsigned),
    }
    return json.dumps(
        {
            "schema": "aquagear.reference-architecture-conformance-evidence",
            "version": "1",
            "evidence": evidence,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def response(**changes: object) -> dict[str, object]:
    value: dict[str, object] = {
        "contract_version": "v1",
        "integration_id": "integration-7",
        "correlation_id": "correlation-11",
        "source_system": "aquagear-reference-app",
        "operation": "enforce",
        "status": "completed",
        "artifact": {
            "artifact_id": "evidence-7",
            "artifact_type": "conformance-evidence",
            "content_type": "application/json",
            "payload": evidence_document(),
            "schema_version": "1.0",
        },
        "metadata": (),
    }
    value.update(changes)
    return value


class Port:
    def __init__(self, output: dict[str, object]) -> None:
        self.output = output

    def integrate(self, request: object) -> dict[str, object]:
        return self.output


def round_trip(**changes: object):
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
        Port(response(**changes))
    ).execute(compatibility, identity)


def test_success_preserves_verified_binding() -> None:
    outcome = bind_reference_architecture_conformance_evidence_with_normalized_failure(
        round_trip()
    )

    assert outcome.succeeded is True
    assert outcome.binding is not None
    assert outcome.failure is None
    assert outcome.binding.evidence.evidence.evaluation["conforms"] is True


@pytest.mark.parametrize(
    ("value", "stage", "code"),
    [
        (None, "round_trip_validation", "invalid_round_trip"),
        ({}, "round_trip_validation", "invalid_round_trip"),
    ],
)
def test_invalid_inputs_are_normalized(value: object, stage: str, code: str) -> None:
    outcome = bind_reference_architecture_conformance_evidence_with_normalized_failure(
        value
    )

    assert outcome.failure is not None
    assert outcome.failure.stage.value == stage
    assert outcome.failure.code.value == code
    assert outcome.failure.integration_id is None
    assert outcome.failure.correlation_id is None


def test_uncorrelated_response_is_normalized() -> None:
    result = round_trip()
    result = replace(
        result,
        correlation=ReferenceArchitectureRequestResponseCorrelationResultV1.model_construct(
            correlated=False,
            request=result.correlation.request,
            response=result.correlation.response,
            mismatches=(),
        ),
    )

    outcome = bind_reference_architecture_conformance_evidence_with_normalized_failure(
        result
    )

    assert outcome.failure is not None
    assert outcome.failure.stage.value == "round_trip_validation"
    assert outcome.failure.code.value == "uncorrelated_response"


@pytest.mark.parametrize(
    ("changes", "stage", "code"),
    [
        ({"status": "failed"}, "response_acceptance", "response_not_completed"),
        ({"artifact": None}, "artifact_validation", "missing_evidence_artifact"),
        (
            {
                "artifact": {
                    "artifact_id": "evidence-7",
                    "artifact_type": "wrong",
                    "content_type": "application/json",
                    "payload": evidence_document(),
                    "schema_version": "1.0",
                }
            },
            "artifact_validation",
            "invalid_evidence_transport",
        ),
        (
            {
                "artifact": {
                    "artifact_id": "evidence-7",
                    "artifact_type": "conformance-evidence",
                    "content_type": "application/json",
                    "payload": b'{"not":"evidence"}',
                    "schema_version": "1.0",
                }
            },
            "document_translation",
            "invalid_evidence_document",
        ),
        (
            {
                "artifact": {
                    "artifact_id": "evidence-7",
                    "artifact_type": "conformance-evidence",
                    "content_type": "application/json",
                    "payload": evidence_document(corrupt_digest=True),
                    "schema_version": "1.0",
                }
            },
            "integrity",
            "evidence_integrity_failed",
        ),
    ],
)
def test_binding_rejections_have_stable_stage_and_code(
    changes: dict[str, object],
    stage: str,
    code: str,
) -> None:
    outcome = bind_reference_architecture_conformance_evidence_with_normalized_failure(
        round_trip(**changes)
    )

    assert outcome.failure is not None
    assert outcome.failure.stage.value == stage
    assert outcome.failure.code.value == code
    assert outcome.failure.retryable is False
    assert outcome.failure.integration_id == "integration-7"
    assert outcome.failure.correlation_id == "correlation-11"


def test_public_failure_is_frozen_minimal_and_redacted() -> None:
    outcome = bind_reference_architecture_conformance_evidence_with_normalized_failure(
        round_trip(artifact=None)
    )
    assert outcome.failure is not None
    failure = outcome.failure
    assert failure.contract_name == (
        REFERENCE_ARCHITECTURE_CONFORMANCE_EVIDENCE_BINDING_FAILURE_CONTRACT_NAME
    )
    assert failure.failure_contract_version == "1.0"
    serialized = failure.model_dump(mode="json")
    assert set(serialized) == {
        "contract_name",
        "failure_contract_version",
        "stage",
        "code",
        "message",
        "retryable",
        "integration_id",
        "correlation_id",
    }
    assert "artifact" not in str(serialized)
    with pytest.raises((TypeError, ValueError)):
        failure.message = "changed"  # type: ignore[misc]


def test_internal_outcome_requires_exactly_one_branch_and_is_frozen() -> None:
    with pytest.raises(ValueError, match="Exactly one"):
        ReferenceArchitectureNormalizedConformanceEvidenceBindingV1()
    outcome = bind_reference_architecture_conformance_evidence_with_normalized_failure(
        round_trip()
    )
    with pytest.raises(FrozenInstanceError):
        outcome.binding = None  # type: ignore[misc]


def test_control_flow_exceptions_are_not_normalized(monkeypatch: pytest.MonkeyPatch) -> None:
    import src.reference_architecture_conformance_evidence_binding_failure_normalization as module

    def interrupt(value: object) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr(
        module, "bind_reference_architecture_conformance_evidence", interrupt
    )
    with pytest.raises(KeyboardInterrupt):
        bind_reference_architecture_conformance_evidence_with_normalized_failure(
            round_trip()
        )
