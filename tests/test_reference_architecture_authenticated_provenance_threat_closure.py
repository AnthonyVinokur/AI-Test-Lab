from __future__ import annotations

import json

from src.reference_architecture_authenticated_provenance_outcome import (
    authenticate_public_reference_architecture_provenance,
)
from src.reference_architecture_authenticated_provenance_serialization import (
    encode_reference_architecture_authenticated_provenance_outcome,
)
from tests.authenticated_provenance_test_support import signed_document


def test_a03_public_boundary_resists_tampering_and_secret_disclosure() -> None:
    document, binding = signed_document()
    original = json.loads(document)
    variants = [b"not-json"]
    for path, value in (
        (("claims", "producer_id"), "attacker"),
        (("claims", "evidence_sha256"), "b" * 64),
        (("proof", "key_id"), "attacker-key"),
    ):
        payload = json.loads(document)
        payload[path[0]][path[1]] = value
        variants.append(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode())

    assert json.loads(document) == original
    for attack in variants:
        outcome = authenticate_public_reference_architecture_provenance(attack, binding)
        assert outcome.succeeded is False
        wire = encode_reference_architecture_authenticated_provenance_outcome(outcome).lower()
        for forbidden in (b"signature", b"public_key", b"private", b"traceback", b"canonical"):
            assert forbidden not in wire
