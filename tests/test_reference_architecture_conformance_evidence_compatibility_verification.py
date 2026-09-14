from __future__ import annotations

import pytest

from src.reference_architecture_compatibility_contract import (
    ReferenceArchitectureCompatibility,
)
from src.reference_architecture_conformance_evidence_compatibility_verification import (
    REFERENCE_ARCHITECTURE_CONFORMANCE_EVIDENCE_COMPATIBILITY_VERIFICATION_CONTRACT_NAME,
    REFERENCE_ARCHITECTURE_CONFORMANCE_EVIDENCE_COMPATIBILITY_VERIFICATION_CONTRACT_VERSION,
    verify_reference_architecture_conformance_evidence_compatibility,
)
from src.reference_architecture_conformance_evidence_intake_contract import (
    ReferenceArchitectureConformanceEvidenceIntakeV1,
    ReferenceArchitectureConformanceEvidenceV1,
)


def supported_intake() -> ReferenceArchitectureConformanceEvidenceIntakeV1:
    return ReferenceArchitectureConformanceEvidenceIntakeV1(
        schema="aquagear.reference-architecture-conformance-evidence",
        version="1",
        evidence=ReferenceArchitectureConformanceEvidenceV1(
            schema_version="1.0",
            architecture_version="v1",
            evaluation={"conforms": True},
            evaluation_sha256="0" * 64,
            evidence_sha256="1" * 64,
        ),
    )


def unsupported_target(
    *, schema_version: str = "1.0", architecture_version: str = "v1"
) -> ReferenceArchitectureConformanceEvidenceIntakeV1:
    """Build an impossible-through-intake value to exercise fail-closed logic."""

    evidence = ReferenceArchitectureConformanceEvidenceV1.model_construct(
        schema_version=schema_version,
        architecture_version=architecture_version,
        evaluation={},
        evaluation_sha256="0" * 64,
        evidence_sha256="1" * 64,
    )
    return ReferenceArchitectureConformanceEvidenceIntakeV1.model_construct(
        export_schema="aquagear.reference-architecture-conformance-evidence",
        version="1",
        evidence=evidence,
    )


def test_compatibility_verification_contract_identity_is_frozen() -> None:
    assert (
        REFERENCE_ARCHITECTURE_CONFORMANCE_EVIDENCE_COMPATIBILITY_VERIFICATION_CONTRACT_NAME
        == "ai-test-lab.reference-architecture-conformance-evidence-compatibility-verification"
    )
    assert (
        REFERENCE_ARCHITECTURE_CONFORMANCE_EVIDENCE_COMPATIBILITY_VERIFICATION_CONTRACT_VERSION
        == "1.0"
    )


def test_supported_frozen_targets_are_an_exact_match() -> None:
    assert (
        verify_reference_architecture_conformance_evidence_compatibility(
            supported_intake()
        )
        is ReferenceArchitectureCompatibility.EXACT
    )


@pytest.mark.parametrize(
    ("schema_version", "architecture_version"),
    [
        ("2.0", "v1"),
        ("1.0", "v2"),
        ("2.0", "v2"),
        ("1.1", "v1"),
    ],
)
def test_unsupported_targets_fail_closed(
    schema_version: str, architecture_version: str
) -> None:
    result = verify_reference_architecture_conformance_evidence_compatibility(
        unsupported_target(
            schema_version=schema_version,
            architecture_version=architecture_version,
        )
    )

    assert result is ReferenceArchitectureCompatibility.INCOMPATIBLE


def test_no_undeclared_cross_version_compatibility_is_inferred() -> None:
    result = verify_reference_architecture_conformance_evidence_compatibility(
        unsupported_target(schema_version="1.1")
    )

    assert result is not ReferenceArchitectureCompatibility.COMPATIBLE


def test_integrity_identity_is_not_reinterpreted_as_compatibility() -> None:
    intake = supported_intake()

    assert intake.evidence.evaluation_sha256 == "0" * 64
    assert (
        verify_reference_architecture_conformance_evidence_compatibility(intake)
        is ReferenceArchitectureCompatibility.EXACT
    )


def test_malformed_nested_evidence_fails_closed() -> None:
    intake = ReferenceArchitectureConformanceEvidenceIntakeV1.model_construct(
        export_schema="aquagear.reference-architecture-conformance-evidence",
        version="1",
        evidence={"schema_version": "1.0", "architecture_version": "v1"},
    )

    assert (
        verify_reference_architecture_conformance_evidence_compatibility(intake)
        is ReferenceArchitectureCompatibility.INCOMPATIBLE
    )


@pytest.mark.parametrize("value", [None, {}, object()])
def test_non_intake_values_are_rejected(value: object) -> None:
    with pytest.raises(
        TypeError,
        match="ReferenceArchitectureConformanceEvidenceIntakeV1",
    ):
        verify_reference_architecture_conformance_evidence_compatibility(value)  # type: ignore[arg-type]
