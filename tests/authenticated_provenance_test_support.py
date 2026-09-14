from __future__ import annotations

import base64
import json

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from src.reference_architecture_authenticated_provenance_contract import (
    ReferenceArchitectureAuthenticatedProvenanceV1,
)
from src.reference_architecture_authenticated_provenance_signer_key_binding import (
    ReferenceArchitectureResolvedSignerKeyBindingV1,
)
from src.reference_architecture_authenticated_provenance_signing_payload import (
    canonical_reference_architecture_authenticated_provenance_signing_payload,
)


def signed_document() -> tuple[bytes, ReferenceArchitectureResolvedSignerKeyBindingV1]:
    private_key = Ed25519PrivateKey.from_private_bytes(bytes(range(32)))
    draft = ReferenceArchitectureAuthenticatedProvenanceV1.model_validate(
        {
            "contract_name": "ai-test-lab.reference-architecture-authenticated-provenance",
            "contract_version": "1.0",
            "claims": {
                "attestation_id": "attestation-3",
                "producer_id": "producer-7",
                "evidence_sha256": "a" * 64,
                "issued_at": "2026-09-14T20:00:00Z",
            },
            "proof": {
                "algorithm": "ed25519",
                "key_id": "key-11",
                "signature_base64": base64.b64encode(bytes(64)).decode("ascii"),
            },
        }
    )
    signature = private_key.sign(
        canonical_reference_architecture_authenticated_provenance_signing_payload(draft)
    )
    payload = draft.model_dump(mode="json")
    payload["proof"]["signature_base64"] = base64.b64encode(signature).decode("ascii")
    public_key = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
    )
    return (
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8"),
        ReferenceArchitectureResolvedSignerKeyBindingV1(
            producer_id="producer-7",
            key_id="key-11",
            algorithm="ed25519",
            public_key=public_key,
        ),
    )
