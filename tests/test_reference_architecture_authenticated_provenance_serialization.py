from __future__ import annotations

import json

import pytest

from src.reference_architecture_authenticated_provenance_outcome import (
    authenticate_public_reference_architecture_provenance,
)
from src.reference_architecture_authenticated_provenance_serialization import (
    ReferenceArchitectureAuthenticatedProvenanceSerializationError,
    decode_reference_architecture_authenticated_provenance_outcome,
    encode_reference_architecture_authenticated_provenance_outcome,
    serialize_reference_architecture_authenticated_provenance_outcome,
)
from tests.authenticated_provenance_test_support import signed_document


def outcomes():
    document, binding = signed_document()
    return (
        authenticate_public_reference_architecture_provenance(document, binding),
        authenticate_public_reference_architecture_provenance(b"bad-json", binding),
    )


@pytest.mark.parametrize("outcome", outcomes())
def test_success_and_failure_round_trip_deterministically(outcome) -> None:
    encoded = encode_reference_architecture_authenticated_provenance_outcome(outcome)
    assert decode_reference_architecture_authenticated_provenance_outcome(encoded) == outcome
    assert encode_reference_architecture_authenticated_provenance_outcome(outcome) == encoded


def test_encoding_is_compact_sorted_utf8_and_detached() -> None:
    success, _ = outcomes()
    encoded = encode_reference_architecture_authenticated_provenance_outcome(success)
    assert encoded.decode() == json.dumps(
        json.loads(encoded), ensure_ascii=False, allow_nan=False,
        separators=(",", ":"), sort_keys=True
    )
    payload = serialize_reference_architecture_authenticated_provenance_outcome(success)
    payload["succeeded"] = False
    assert success.succeeded is True


@pytest.mark.parametrize(
    "document",
    [b"not-json", b"[]", b"{}", b'{"succeeded":true,"succeeded":false}',
     b'{"succeeded":NaN}', b"\xff"],
)
def test_decoder_fails_closed_for_ambiguous_or_invalid_documents(document: bytes) -> None:
    with pytest.raises(ReferenceArchitectureAuthenticatedProvenanceSerializationError):
        decode_reference_architecture_authenticated_provenance_outcome(document)


def test_serializer_accepts_only_a0307_public_outcome() -> None:
    with pytest.raises(TypeError, match="A.03.07"):
        serialize_reference_architecture_authenticated_provenance_outcome(object())  # type: ignore[arg-type]


def test_wire_documents_exclude_authentication_secrets() -> None:
    for outcome in outcomes():
        encoded = encode_reference_architecture_authenticated_provenance_outcome(outcome).lower()
        for forbidden in (b"signature", b"public_key", b"private", b"canonical", b"traceback", b"secret"):
            assert forbidden not in encoded
