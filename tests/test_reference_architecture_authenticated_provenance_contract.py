from __future__ import annotations

import ast
import base64
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.public_contract import PublicContractModel, serialize_public_contract
from src.reference_architecture_authenticated_provenance_contract import (
    REFERENCE_ARCHITECTURE_AUTHENTICATED_PROVENANCE_CONTRACT_NAME,
    REFERENCE_ARCHITECTURE_AUTHENTICATED_PROVENANCE_CONTRACT_VERSION,
    REFERENCE_ARCHITECTURE_AUTHENTICATED_PROVENANCE_SIGNATURE_ALGORITHM,
    ReferenceArchitectureAuthenticatedProvenanceV1,
    reference_architecture_authenticated_provenance_contract,
)


EVIDENCE_SHA256 = "a" * 64
SIGNATURE_BASE64 = base64.b64encode(bytes(range(64))).decode("ascii")


def public_document() -> dict[str, object]:
    return {
        "contract_name": (
            "ai-test-lab.reference-architecture-authenticated-provenance"
        ),
        "contract_version": "1.0",
        "claims": {
            "attestation_id": "attestation-20260914-001",
            "producer_id": "aquagear-reference-app",
            "evidence_sha256": EVIDENCE_SHA256,
            "issued_at": "2026-09-14T19:30:00Z",
        },
        "proof": {
            "algorithm": "ed25519",
            "key_id": "aquagear-reference-app:key:2026-01",
            "signature_base64": SIGNATURE_BASE64,
        },
    }


def test_contract_identity_and_algorithm_are_frozen() -> None:
    assert REFERENCE_ARCHITECTURE_AUTHENTICATED_PROVENANCE_CONTRACT_NAME == (
        "ai-test-lab.reference-architecture-authenticated-provenance"
    )
    assert REFERENCE_ARCHITECTURE_AUTHENTICATED_PROVENANCE_CONTRACT_VERSION == "1.0"
    assert REFERENCE_ARCHITECTURE_AUTHENTICATED_PROVENANCE_SIGNATURE_ALGORITHM == (
        "ed25519"
    )


def test_exact_public_document_is_accepted_and_serialized() -> None:
    document = public_document()
    contract = ReferenceArchitectureAuthenticatedProvenanceV1.model_validate(document)

    assert isinstance(contract, PublicContractModel)
    assert serialize_public_contract(contract) == document


def test_factory_builds_the_supported_contract() -> None:
    contract = reference_architecture_authenticated_provenance_contract(
        attestation_id="attestation-20260914-001",
        producer_id="aquagear-reference-app",
        evidence_sha256=EVIDENCE_SHA256,
        issued_at="2026-09-14T19:30:00Z",
        key_id="aquagear-reference-app:key:2026-01",
        signature_base64=SIGNATURE_BASE64,
    )

    assert contract.contract_name == (
        REFERENCE_ARCHITECTURE_AUTHENTICATED_PROVENANCE_CONTRACT_NAME
    )
    assert contract.claims.evidence_sha256 == EVIDENCE_SHA256
    assert contract.proof.algorithm == "ed25519"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("contract_name", "unknown-contract"),
        ("contract_version", "2.0"),
    ],
)
def test_unknown_contract_identity_is_rejected(field: str, value: str) -> None:
    document = public_document()
    document[field] = value

    with pytest.raises(ValidationError):
        ReferenceArchitectureAuthenticatedProvenanceV1.model_validate(document)


@pytest.mark.parametrize(
    "field", ["contract_name", "contract_version", "claims", "proof"]
)
def test_required_top_level_fields_cannot_be_omitted(field: str) -> None:
    document = public_document()
    del document[field]

    with pytest.raises(ValidationError):
        ReferenceArchitectureAuthenticatedProvenanceV1.model_validate(document)


@pytest.mark.parametrize(
    ("location", "field"),
    [
        ("top", "internal_trust_score"),
        ("claims", "provider_state"),
        ("proof", "private_key"),
    ],
)
def test_unknown_and_private_fields_are_rejected(location: str, field: str) -> None:
    document = public_document()
    target = document if location == "top" else document[location]
    target[field] = "must-not-cross-boundary"  # type: ignore[index]

    with pytest.raises(ValidationError):
        ReferenceArchitectureAuthenticatedProvenanceV1.model_validate(document)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("attestation_id", ""),
        ("attestation_id", "contains whitespace"),
        ("attestation_id", b"attestation-20260914-001"),
        ("producer_id", "producer\nidentity"),
        ("producer_id", 7),
        ("producer_id", "p" * 257),
        ("evidence_sha256", "A" * 64),
        ("evidence_sha256", "a" * 63),
        ("issued_at", "2026-09-14T15:30:00-04:00"),
        ("issued_at", "2026-02-30T19:30:00Z"),
        ("issued_at", b"2026-09-14T19:30:00Z"),
    ],
)
def test_invalid_claims_are_rejected(field: str, value: object) -> None:
    document = public_document()
    document["claims"][field] = value  # type: ignore[index]

    with pytest.raises(ValidationError):
        ReferenceArchitectureAuthenticatedProvenanceV1.model_validate(document)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("algorithm", "rsa-pss"),
        ("algorithm", "Ed25519"),
        ("key_id", ""),
        ("key_id", "key with spaces"),
        ("key_id", b"key-1"),
        ("signature_base64", "not-base64"),
        ("signature_base64", base64.b64encode(b"short").decode("ascii")),
        ("signature_base64", SIGNATURE_BASE64.rstrip("=")),
        ("signature_base64", SIGNATURE_BASE64.encode("ascii")),
    ],
)
def test_invalid_proof_is_rejected(field: str, value: object) -> None:
    document = public_document()
    document["proof"][field] = value  # type: ignore[index]

    with pytest.raises(ValidationError):
        ReferenceArchitectureAuthenticatedProvenanceV1.model_validate(document)


@pytest.mark.parametrize("field", ["algorithm", "key_id", "signature_base64"])
def test_required_proof_fields_cannot_be_omitted(field: str) -> None:
    document = public_document()
    del document["proof"][field]  # type: ignore[index]

    with pytest.raises(ValidationError):
        ReferenceArchitectureAuthenticatedProvenanceV1.model_validate(document)


@pytest.mark.parametrize(
    "field", ["attestation_id", "producer_id", "evidence_sha256", "issued_at"]
)
def test_required_claim_fields_cannot_be_omitted(field: str) -> None:
    document = public_document()
    del document["claims"][field]  # type: ignore[index]

    with pytest.raises(ValidationError):
        ReferenceArchitectureAuthenticatedProvenanceV1.model_validate(document)


def test_contract_is_detached_and_immutable() -> None:
    document = public_document()
    contract = ReferenceArchitectureAuthenticatedProvenanceV1.model_validate(document)
    document["claims"]["producer_id"] = "substituted"  # type: ignore[index]

    assert contract.claims.producer_id == "aquagear-reference-app"
    with pytest.raises(ValidationError):
        contract.claims.producer_id = "substituted"  # type: ignore[misc]


def test_contract_module_has_no_provider_crypto_or_transport_dependency() -> None:
    module_path = (
        Path(__file__).parents[1]
        / "src"
        / "reference_architecture_authenticated_provenance_contract.py"
    )
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    imported_roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".")[0])

    assert imported_roots.isdisjoint(
        {"reference_app", "cryptography", "nacl", "requests", "httpx"}
    )
