from __future__ import annotations

import json

from src.reference_architecture_authenticated_provenance_outcome import (
    authenticate_public_reference_architecture_provenance,
)
from src.reference_architecture_authenticated_provenance_serialization import (
    decode_reference_architecture_authenticated_provenance_outcome,
    encode_reference_architecture_authenticated_provenance_outcome,
)
from src.reference_architecture_authenticated_provenance_signer_key_binding import (
    ReferenceArchitectureResolvedSignerKeyBindingV1,
)
from tests.authenticated_provenance_test_support import signed_document


def test_valid_document_authenticates_and_round_trips_publicly() -> None:
    document, binding = signed_document()
    outcome = authenticate_public_reference_architecture_provenance(document, binding)
    restored = decode_reference_architecture_authenticated_provenance_outcome(
        encode_reference_architecture_authenticated_provenance_outcome(outcome)
    )
    assert restored == outcome
    assert restored.authentication is not None
    assert restored.authentication.evidence_sha256 == "a" * 64


def test_tampering_after_signing_fails_closed_without_oracle_detail() -> None:
    document, binding = signed_document()
    payload = json.loads(document)
    payload["claims"]["evidence_sha256"] = "b" * 64
    tampered = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    outcome = authenticate_public_reference_architecture_provenance(tampered, binding)
    assert outcome.failure is not None
    assert outcome.failure.code.value == "authentication_failed"


def test_wrong_authorized_key_and_malformed_input_share_safe_boundary_shape() -> None:
    document, binding = signed_document()
    wrong = ReferenceArchitectureResolvedSignerKeyBindingV1(
        producer_id=binding.producer_id, key_id=binding.key_id,
        algorithm="ed25519", public_key=bytes(range(1, 33))
    )
    wrong_key = authenticate_public_reference_architecture_provenance(document, wrong)
    malformed = authenticate_public_reference_architecture_provenance(b"bad", binding)
    assert wrong_key.succeeded is malformed.succeeded is False
    for outcome in (wrong_key, malformed):
        wire = encode_reference_architecture_authenticated_provenance_outcome(outcome)
        assert b"signature" not in wire and b"public_key" not in wire
