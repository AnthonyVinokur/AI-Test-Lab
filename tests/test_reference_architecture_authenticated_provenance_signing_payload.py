from __future__ import annotations

import base64
import json

import pytest

from src.reference_architecture_authenticated_provenance_contract import (
    ReferenceArchitectureAuthenticatedProvenanceV1,
)
from src.reference_architecture_authenticated_provenance_signing_payload import (
    REFERENCE_ARCHITECTURE_AUTHENTICATED_PROVENANCE_SIGNING_PAYLOAD_CONTRACT_NAME,
    REFERENCE_ARCHITECTURE_AUTHENTICATED_PROVENANCE_SIGNING_PAYLOAD_CONTRACT_VERSION,
    canonical_reference_architecture_authenticated_provenance_signing_payload,
)


SIGNATURE_BASE64 = base64.b64encode(bytes(range(64))).decode("ascii")


def provenance(
    *,
    attestation_id: str = "attestation-20260914-001",
    producer_id: str = "aquagear-reference-app",
    evidence_sha256: str = "a" * 64,
    issued_at: str = "2026-09-14T19:30:00Z",
    key_id: str = "aquagear-reference-app:key:2026-01",
    signature_base64: str = SIGNATURE_BASE64,
) -> ReferenceArchitectureAuthenticatedProvenanceV1:
    return ReferenceArchitectureAuthenticatedProvenanceV1.model_validate(
        {
            "contract_name": (
                "ai-test-lab.reference-architecture-authenticated-provenance"
            ),
            "contract_version": "1.0",
            "claims": {
                "attestation_id": attestation_id,
                "producer_id": producer_id,
                "evidence_sha256": evidence_sha256,
                "issued_at": issued_at,
            },
            "proof": {
                "algorithm": "ed25519",
                "key_id": key_id,
                "signature_base64": signature_base64,
            },
        }
    )


def test_signing_payload_contract_identity_is_frozen() -> None:
    assert (
        REFERENCE_ARCHITECTURE_AUTHENTICATED_PROVENANCE_SIGNING_PAYLOAD_CONTRACT_NAME
        == "ai-test-lab.reference-architecture-authenticated-provenance-signing-payload"
    )
    assert (
        REFERENCE_ARCHITECTURE_AUTHENTICATED_PROVENANCE_SIGNING_PAYLOAD_CONTRACT_VERSION
        == "1.0"
    )


def test_payload_is_exact_canonical_utf8_json() -> None:
    result = canonical_reference_architecture_authenticated_provenance_signing_payload(
        provenance(producer_id="aquagear-潜水")
    )

    expected = (
        '{"claims":{"attestation_id":"attestation-20260914-001",'
        '"evidence_sha256":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
        'aaaaaaaaaaaaaaaa","issued_at":"2026-09-14T19:30:00Z",'
        '"producer_id":"aquagear-潜水"},"contract_name":"ai-test-lab.'
        'reference-architecture-authenticated-provenance","contract_version":"1.0",'
        '"proof":{"algorithm":"ed25519","key_id":"aquagear-reference-app:'
        'key:2026-01"}}'
    ).encode("utf-8")

    assert result == expected
    assert json.loads(result.decode("utf-8"))["claims"]["producer_id"] == (
        "aquagear-潜水"
    )


def test_equivalent_contracts_produce_identical_payloads() -> None:
    assert canonical_reference_architecture_authenticated_provenance_signing_payload(
        provenance()
    ) == canonical_reference_architecture_authenticated_provenance_signing_payload(
        provenance()
    )


@pytest.mark.parametrize(
    ("field", "changed"),
    [
        ("attestation_id", "attestation-20260914-002"),
        ("producer_id", "different-producer"),
        ("evidence_sha256", "b" * 64),
        ("issued_at", "2026-09-14T19:30:01Z"),
        ("key_id", "aquagear-reference-app:key:2026-02"),
    ],
)
def test_each_variable_signed_field_changes_payload(
    field: str, changed: str
) -> None:
    original = canonical_reference_architecture_authenticated_provenance_signing_payload(
        provenance()
    )
    modified = canonical_reference_architecture_authenticated_provenance_signing_payload(
        provenance(**{field: changed})
    )

    assert modified != original


def test_signature_is_detached_and_does_not_change_payload() -> None:
    another_signature = base64.b64encode(bytes(reversed(range(64)))).decode("ascii")

    assert canonical_reference_architecture_authenticated_provenance_signing_payload(
        provenance()
    ) == canonical_reference_architecture_authenticated_provenance_signing_payload(
        provenance(signature_base64=another_signature)
    )


def test_payload_binds_contract_identity_algorithm_and_key_reference() -> None:
    decoded = json.loads(
        canonical_reference_architecture_authenticated_provenance_signing_payload(
            provenance()
        )
    )

    assert decoded["contract_name"] == (
        "ai-test-lab.reference-architecture-authenticated-provenance"
    )
    assert decoded["contract_version"] == "1.0"
    assert decoded["proof"] == {
        "algorithm": "ed25519",
        "key_id": "aquagear-reference-app:key:2026-01",
    }
    assert "signature_base64" not in decoded["proof"]


def test_payload_generation_does_not_mutate_contract() -> None:
    contract = provenance()
    before = contract.model_dump(mode="json")

    canonical_reference_architecture_authenticated_provenance_signing_payload(contract)

    assert contract.model_dump(mode="json") == before


@pytest.mark.parametrize("invalid", [None, {}, b"{}", "provenance"])
def test_non_contract_inputs_are_rejected(invalid: object) -> None:
    with pytest.raises(TypeError, match="ReferenceArchitectureAuthenticatedProvenanceV1"):
        canonical_reference_architecture_authenticated_provenance_signing_payload(
            invalid  # type: ignore[arg-type]
        )
