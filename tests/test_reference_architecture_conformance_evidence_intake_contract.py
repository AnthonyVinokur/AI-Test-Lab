from __future__ import annotations

from types import MappingProxyType

import pytest
from pydantic import ValidationError

from src.public_contract import PublicContractModel, serialize_public_contract
from src.reference_architecture_conformance_evidence_intake_contract import (
    AQUAGEAR_CONFORMANCE_EVIDENCE_EXPORT_SCHEMA,
    AQUAGEAR_CONFORMANCE_EVIDENCE_EXPORT_VERSION,
    AQUAGEAR_CONFORMANCE_EVIDENCE_SCHEMA_VERSION,
    AQUAGEAR_FROZEN_ARCHITECTURE_VERSION,
    REFERENCE_ARCHITECTURE_CONFORMANCE_EVIDENCE_INTAKE_CONTRACT_NAME,
    REFERENCE_ARCHITECTURE_CONFORMANCE_EVIDENCE_INTAKE_CONTRACT_VERSION,
    ReferenceArchitectureConformanceEvidenceIntakeV1,
    supported_reference_architecture_conformance_evidence_intake_contract,
)


EVALUATION_SHA256 = "1" * 64
EVIDENCE_SHA256 = "a" * 64


def producer_export() -> dict[str, object]:
    return {
        "schema": "aquagear.reference-architecture-conformance-evidence",
        "version": "1",
        "evidence": {
            "schema_version": "1.0",
            "architecture_version": "v1",
            "evaluation": {
                "conforms": True,
                "requirements": [
                    {"requirement_id": "provider_neutral_contract", "passed": True}
                ],
            },
            "evaluation_sha256": EVALUATION_SHA256,
            "evidence_sha256": EVIDENCE_SHA256,
        },
    }


def test_contract_identity_matches_frozen_aquagear_producer() -> None:
    assert REFERENCE_ARCHITECTURE_CONFORMANCE_EVIDENCE_INTAKE_CONTRACT_NAME == (
        "ai-test-lab.reference-architecture-conformance-evidence-intake"
    )
    assert REFERENCE_ARCHITECTURE_CONFORMANCE_EVIDENCE_INTAKE_CONTRACT_VERSION == "1.0"
    assert AQUAGEAR_CONFORMANCE_EVIDENCE_EXPORT_SCHEMA == (
        "aquagear.reference-architecture-conformance-evidence"
    )
    assert AQUAGEAR_CONFORMANCE_EVIDENCE_EXPORT_VERSION == "1"
    assert AQUAGEAR_CONFORMANCE_EVIDENCE_SCHEMA_VERSION == "1.0"
    assert AQUAGEAR_FROZEN_ARCHITECTURE_VERSION == "v1"


def test_frozen_a434_export_shape_is_accepted_exactly() -> None:
    contract = ReferenceArchitectureConformanceEvidenceIntakeV1.model_validate(
        producer_export()
    )

    assert isinstance(contract, PublicContractModel)
    assert serialize_public_contract(contract) == producer_export()


def test_factory_builds_the_supported_contract() -> None:
    contract = supported_reference_architecture_conformance_evidence_intake_contract(
        evaluation={"conforms": True},
        evaluation_sha256=EVALUATION_SHA256,
        evidence_sha256=EVIDENCE_SHA256,
    )

    assert contract.export_schema == AQUAGEAR_CONFORMANCE_EVIDENCE_EXPORT_SCHEMA
    assert contract.version == "1"
    assert contract.evidence.architecture_version == "v1"


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("schema",), "future-schema"),
        (("version",), "2"),
        (("evidence", "schema_version"), "2.0"),
        (("evidence", "architecture_version"), "v2"),
    ],
)
def test_unknown_contract_versions_are_rejected(
    path: tuple[str, ...], value: object
) -> None:
    payload = producer_export()
    target: dict[str, object] = payload
    for key in path[:-1]:
        target = target[key]  # type: ignore[assignment]
    target[path[-1]] = value

    with pytest.raises(ValidationError):
        ReferenceArchitectureConformanceEvidenceIntakeV1.model_validate(payload)


@pytest.mark.parametrize("field", ["schema", "version", "evidence"])
def test_required_envelope_fields_cannot_be_omitted(field: str) -> None:
    payload = producer_export()
    del payload[field]

    with pytest.raises(ValidationError):
        ReferenceArchitectureConformanceEvidenceIntakeV1.model_validate(payload)


@pytest.mark.parametrize(
    "field",
    [
        "schema_version",
        "architecture_version",
        "evaluation",
        "evaluation_sha256",
        "evidence_sha256",
    ],
)
def test_required_evidence_fields_cannot_be_omitted(field: str) -> None:
    payload = producer_export()
    del payload["evidence"][field]  # type: ignore[index]

    with pytest.raises(ValidationError):
        ReferenceArchitectureConformanceEvidenceIntakeV1.model_validate(payload)


@pytest.mark.parametrize(
    ("location", "field"),
    [("envelope", "internal_policy"), ("evidence", "private_score")],
)
def test_unknown_fields_are_rejected(location: str, field: str) -> None:
    payload = producer_export()
    target = payload if location == "envelope" else payload["evidence"]
    target[field] = "secret"  # type: ignore[index]

    with pytest.raises(ValidationError):
        ReferenceArchitectureConformanceEvidenceIntakeV1.model_validate(payload)


@pytest.mark.parametrize(
    "digest",
    ["", "a" * 63, "a" * 65, "A" * 64, "g" * 64, 7],
)
def test_digest_identity_must_be_lowercase_sha256(digest: object) -> None:
    payload = producer_export()
    payload["evidence"]["evidence_sha256"] = digest  # type: ignore[index]

    with pytest.raises(ValidationError):
        ReferenceArchitectureConformanceEvidenceIntakeV1.model_validate(payload)


@pytest.mark.parametrize(
    "evaluation",
    [[], "result", {1: "non-string-key"}, {"score": float("nan")}, {"raw": b"x"}],
)
def test_evaluation_must_be_a_deterministic_json_object(evaluation: object) -> None:
    payload = producer_export()
    payload["evidence"]["evaluation"] = evaluation  # type: ignore[index]

    with pytest.raises((ValidationError, ValueError)):
        ReferenceArchitectureConformanceEvidenceIntakeV1.model_validate(payload)


def test_input_and_nested_contract_state_are_detached_and_immutable() -> None:
    payload = producer_export()
    contract = ReferenceArchitectureConformanceEvidenceIntakeV1.model_validate(payload)
    payload["evidence"]["evaluation"]["conforms"] = False  # type: ignore[index]

    assert contract.evidence.evaluation["conforms"] is True
    assert isinstance(contract.evidence.evaluation, MappingProxyType)
    assert isinstance(contract.evidence.evaluation["requirements"], tuple)
    with pytest.raises(TypeError):
        contract.evidence.evaluation["conforms"] = False  # type: ignore[index]
    with pytest.raises(ValidationError):
        contract.version = "2"  # type: ignore[misc]


def test_public_serialization_is_detached_from_contract_state() -> None:
    contract = ReferenceArchitectureConformanceEvidenceIntakeV1.model_validate(
        producer_export()
    )
    exported = serialize_public_contract(contract)
    exported["evidence"]["evaluation"]["conforms"] = False

    assert contract.evidence.evaluation["conforms"] is True
