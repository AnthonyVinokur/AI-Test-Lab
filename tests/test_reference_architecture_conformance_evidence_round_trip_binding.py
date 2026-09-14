from __future__ import annotations

import hashlib
import json
from dataclasses import FrozenInstanceError, replace

import pytest

from src.public_contract import serialize_public_contract
from src.reference_architecture_compatibility_contract import (
    supported_reference_architecture_compatibility_contract,
)
from src.reference_architecture_conformance_evidence_round_trip_binding import (
    REFERENCE_ARCHITECTURE_CONFORMANCE_EVIDENCE_ROUND_TRIP_BINDING_CONTRACT_NAME,
    REFERENCE_ARCHITECTURE_CONFORMANCE_EVIDENCE_ROUND_TRIP_BINDING_CONTRACT_VERSION,
    ReferenceArchitectureConformanceEvidenceBindingError,
    ReferenceArchitectureConformanceEvidenceBindingV1,
    bind_reference_architecture_conformance_evidence,
)
from src.reference_architecture_request_response_correlation import (
    ReferenceArchitectureRequestResponseCorrelationResultV1,
)
from src.reference_architecture_round_trip_orchestration import (
    CorrelatedReferenceArchitectureRoundTripOrchestrator,
)


def canonical_sha256(value: object) -> str:
    document = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(document).hexdigest()


def evidence_document(*, corrupt_digest: bool = False) -> bytes:
    evaluation = {"conforms": True, "violations": []}
    evaluation_sha256 = canonical_sha256(evaluation)
    unsigned = {
        "schema_version": "1.0",
        "architecture_version": "v1",
        "evaluation": evaluation,
        "evaluation_sha256": evaluation_sha256,
    }
    evidence = {
        **unsigned,
        "evidence_sha256": (
            "0" * 64 if corrupt_digest else canonical_sha256(unsigned)
        ),
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


def compatibility_payload() -> dict[str, object]:
    return serialize_public_contract(
        supported_reference_architecture_compatibility_contract()
    )


def request_identity() -> dict[str, object]:
    return {
        "contract_version": "v1",
        "integration_id": "integration-7",
        "correlation_id": "correlation-11",
        "source_system": "ai-test-lab",
        "operation": "enforce",
    }


def response_payload(
    *,
    document: bytes | None = None,
    status: str = "completed",
    artifact_type: str = "conformance-evidence",
    content_type: str = "application/json",
    schema_version: str | None = "1.0",
    include_artifact: bool = True,
) -> dict[str, object]:
    artifact: dict[str, object] | None = None
    if include_artifact:
        artifact = {
            "artifact_id": "conformance-evidence-7",
            "artifact_type": artifact_type,
            "content_type": content_type,
            "payload": document if document is not None else evidence_document(),
            "schema_version": schema_version,
        }
    return {
        "contract_version": "v1",
        "integration_id": "integration-7",
        "correlation_id": "correlation-11",
        "source_system": "aquagear-reference-app",
        "operation": "enforce",
        "status": status,
        "artifact": artifact,
        "metadata": (),
    }


class Port:
    def __init__(self, response: dict[str, object]) -> None:
        self.response = response

    def integrate(self, request: object) -> dict[str, object]:
        return self.response


def round_trip(**response_changes: object):
    response = response_payload(**response_changes)  # type: ignore[arg-type]
    return CorrelatedReferenceArchitectureRoundTripOrchestrator(Port(response)).execute(
        compatibility_payload(), request_identity()
    )


def test_binding_contract_identity_is_frozen() -> None:
    assert REFERENCE_ARCHITECTURE_CONFORMANCE_EVIDENCE_ROUND_TRIP_BINDING_CONTRACT_NAME == (
        "ai-test-lab.reference-architecture-conformance-evidence-round-trip-binding"
    )
    assert (
        REFERENCE_ARCHITECTURE_CONFORMANCE_EVIDENCE_ROUND_TRIP_BINDING_CONTRACT_VERSION
        == "1.0"
    )


def test_binds_verified_evidence_to_its_correlated_completed_response() -> None:
    result = round_trip()

    binding = bind_reference_architecture_conformance_evidence(result)

    assert isinstance(binding, ReferenceArchitectureConformanceEvidenceBindingV1)
    assert binding.response.integration_id == "integration-7"
    assert binding.response.correlation_id == "correlation-11"
    assert binding.evidence.evidence.evaluation["conforms"] is True


def test_binding_is_frozen() -> None:
    binding = bind_reference_architecture_conformance_evidence(round_trip())

    with pytest.raises(FrozenInstanceError):
        binding.evidence = binding.evidence  # type: ignore[misc]


def test_runtime_altered_uncorrelated_result_fails_closed() -> None:
    result = round_trip()
    uncorrelated = replace(
        result,
        correlation=ReferenceArchitectureRequestResponseCorrelationResultV1.model_construct(
            correlated=False,
            request=result.correlation.request,
            response=result.correlation.response,
            mismatches=(),
        ),
    )

    with pytest.raises(
        ReferenceArchitectureConformanceEvidenceBindingError,
        match="uncorrelated response",
    ):
        bind_reference_architecture_conformance_evidence(uncorrelated)


@pytest.mark.parametrize("value", [None, {}, object()])
def test_non_round_trip_values_are_rejected(value: object) -> None:
    with pytest.raises(TypeError, match="A.01 correlated round-trip result"):
        bind_reference_architecture_conformance_evidence(value)  # type: ignore[arg-type]


@pytest.mark.parametrize("status", ["accepted", "rejected", "failed"])
def test_only_completed_responses_can_bind_evidence(status: str) -> None:
    with pytest.raises(
        ReferenceArchitectureConformanceEvidenceBindingError,
        match="completed A.01 response",
    ):
        bind_reference_architecture_conformance_evidence(round_trip(status=status))


def test_missing_artifact_fails_closed() -> None:
    with pytest.raises(
        ReferenceArchitectureConformanceEvidenceBindingError,
        match="does not carry an evidence artifact",
    ):
        bind_reference_architecture_conformance_evidence(
            round_trip(include_artifact=False)
        )


@pytest.mark.parametrize(
    "changes",
    [
        {"artifact_type": "evidence-bundle"},
        {"content_type": "application/octet-stream"},
        {"schema_version": "2.0"},
        {"schema_version": None},
    ],
)
def test_transport_identity_mismatch_fails_closed(changes: dict[str, object]) -> None:
    with pytest.raises(
        ReferenceArchitectureConformanceEvidenceBindingError,
        match="frozen conformance-evidence transport",
    ):
        bind_reference_architecture_conformance_evidence(round_trip(**changes))


def test_invalid_evidence_document_fails_closed() -> None:
    with pytest.raises(
        ReferenceArchitectureConformanceEvidenceBindingError,
        match="not a valid conformance-evidence document",
    ):
        bind_reference_architecture_conformance_evidence(
            round_trip(document=b'{"not":"evidence"}')
        )


def test_corrupt_evidence_digest_fails_closed() -> None:
    with pytest.raises(
        ReferenceArchitectureConformanceEvidenceBindingError,
        match="failed integrity verification",
    ):
        bind_reference_architecture_conformance_evidence(
            round_trip(document=evidence_document(corrupt_digest=True))
        )


def test_artifact_payload_is_the_only_bound_evidence_source() -> None:
    document = evidence_document()
    result = round_trip(document=document)

    binding = bind_reference_architecture_conformance_evidence(result)

    assert serialize_public_contract(binding.evidence) == json.loads(document)
