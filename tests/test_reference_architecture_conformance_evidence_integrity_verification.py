from __future__ import annotations

import hashlib
import json

import pytest

from src.public_contract import serialize_public_contract
from src.reference_architecture_conformance_evidence_document_translation import (
    translate_untrusted_reference_architecture_conformance_evidence_document,
)
from src.reference_architecture_conformance_evidence_integrity_verification import (
    REFERENCE_ARCHITECTURE_CONFORMANCE_EVIDENCE_INTEGRITY_VERIFICATION_CONTRACT_NAME,
    REFERENCE_ARCHITECTURE_CONFORMANCE_EVIDENCE_INTEGRITY_VERIFICATION_CONTRACT_VERSION,
    verify_reference_architecture_conformance_evidence_integrity,
)
from src.reference_architecture_conformance_evidence_intake_contract import (
    ReferenceArchitectureConformanceEvidenceIntakeV1,
)


def canonical_sha256(value: object) -> str:
    canonical_json = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


def producer_export(
    evaluation: dict[str, object] | None = None,
) -> dict[str, object]:
    evaluation = evaluation or {
        "conforms": True,
        "requirements": [
            {"requirement_id": "provider_neutral_contract", "passed": True}
        ],
    }
    evaluation_sha256 = canonical_sha256(evaluation)
    unsigned_evidence = {
        "schema_version": "1.0",
        "architecture_version": "v1",
        "evaluation": evaluation,
        "evaluation_sha256": evaluation_sha256,
    }
    return {
        "schema": "aquagear.reference-architecture-conformance-evidence",
        "version": "1",
        "evidence": {
            **unsigned_evidence,
            "evidence_sha256": canonical_sha256(unsigned_evidence),
        },
    }


def intake(
    payload: dict[str, object],
) -> ReferenceArchitectureConformanceEvidenceIntakeV1:
    return ReferenceArchitectureConformanceEvidenceIntakeV1.model_validate(payload)


def test_integrity_verification_contract_identity_is_frozen() -> None:
    assert (
        REFERENCE_ARCHITECTURE_CONFORMANCE_EVIDENCE_INTEGRITY_VERIFICATION_CONTRACT_NAME
        == "ai-test-lab.reference-architecture-conformance-evidence-integrity-verification"
    )
    assert (
        REFERENCE_ARCHITECTURE_CONFORMANCE_EVIDENCE_INTEGRITY_VERIFICATION_CONTRACT_VERSION
        == "1.0"
    )


def test_unchanged_a433_evidence_verifies() -> None:
    assert verify_reference_architecture_conformance_evidence_integrity(
        intake(producer_export())
    )


def test_translated_a434_document_verifies_end_to_end() -> None:
    document = json.dumps(
        producer_export(),
        ensure_ascii=False,
        indent=2,
    ).encode("utf-8")
    translated = (
        translate_untrusted_reference_architecture_conformance_evidence_document(
            document
        )
    )

    assert verify_reference_architecture_conformance_evidence_integrity(translated)


def test_canonicalization_matches_producer_for_nested_unicode_data() -> None:
    evaluation = {
        "z_note": "válido 🌊",
        "nested": {"score": 0.75, "values": [None, True, 3]},
        "conforms": True,
    }

    assert verify_reference_architecture_conformance_evidence_integrity(
        intake(producer_export(evaluation))
    )


def test_evaluation_key_order_does_not_change_integrity() -> None:
    first = {"conforms": True, "summary": "valid"}
    payload = producer_export(first)
    reordered = {"summary": "valid", "conforms": True}
    payload["evidence"]["evaluation"] = reordered  # type: ignore[index]

    assert verify_reference_architecture_conformance_evidence_integrity(intake(payload))


def test_changed_evaluation_fails_even_when_published_hashes_are_unchanged() -> None:
    payload = producer_export()
    payload["evidence"]["evaluation"]["conforms"] = False  # type: ignore[index]

    assert not verify_reference_architecture_conformance_evidence_integrity(
        intake(payload)
    )


def test_changed_evaluation_digest_fails_even_when_evidence_digest_is_recomputed() -> None:
    payload = producer_export()
    evidence = payload["evidence"]  # type: ignore[assignment]
    evidence["evaluation_sha256"] = "0" * 64
    unsigned_evidence = {
        key: value for key, value in evidence.items() if key != "evidence_sha256"
    }
    evidence["evidence_sha256"] = canonical_sha256(unsigned_evidence)

    assert not verify_reference_architecture_conformance_evidence_integrity(
        intake(payload)
    )


def test_changed_evidence_digest_fails() -> None:
    payload = producer_export()
    payload["evidence"]["evidence_sha256"] = "0" * 64  # type: ignore[index]

    assert not verify_reference_architecture_conformance_evidence_integrity(
        intake(payload)
    )


def test_outer_export_envelope_is_not_part_of_producer_integrity_hashes() -> None:
    payload = producer_export()
    contract = intake(payload)

    assert verify_reference_architecture_conformance_evidence_integrity(contract)
    assert contract.export_schema == payload["schema"]
    assert contract.version == payload["version"]


def test_verification_does_not_mutate_the_intake_contract() -> None:
    contract = intake(producer_export())
    before = serialize_public_contract(contract)

    verify_reference_architecture_conformance_evidence_integrity(contract)

    assert serialize_public_contract(contract) == before


@pytest.mark.parametrize("value", [None, {}, object()])
def test_non_intake_values_are_rejected(value: object) -> None:
    with pytest.raises(
        TypeError,
        match="ReferenceArchitectureConformanceEvidenceIntakeV1",
    ):
        verify_reference_architecture_conformance_evidence_integrity(value)  # type: ignore[arg-type]
