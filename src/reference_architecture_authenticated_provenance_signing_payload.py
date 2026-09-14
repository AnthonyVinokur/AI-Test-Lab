from __future__ import annotations

import json

from src.public_contract import serialize_public_contract
from src.reference_architecture_authenticated_provenance_contract import (
    ReferenceArchitectureAuthenticatedProvenanceV1,
)


REFERENCE_ARCHITECTURE_AUTHENTICATED_PROVENANCE_SIGNING_PAYLOAD_CONTRACT_NAME = (
    "ai-test-lab.reference-architecture-authenticated-provenance-signing-payload"
)
REFERENCE_ARCHITECTURE_AUTHENTICATED_PROVENANCE_SIGNING_PAYLOAD_CONTRACT_VERSION = (
    "1.0"
)


def canonical_reference_architecture_authenticated_provenance_signing_payload(
    provenance: ReferenceArchitectureAuthenticatedProvenanceV1,
) -> bytes:
    """Return the deterministic bytes covered by an A.03 provenance signature.

    The detached signature value is deliberately excluded. Contract identity,
    claims, algorithm, and key reference are included so none can be
    substituted while retaining a valid signature over the original payload.
    """

    if not isinstance(provenance, ReferenceArchitectureAuthenticatedProvenanceV1):
        raise TypeError(
            "provenance must be a "
            "ReferenceArchitectureAuthenticatedProvenanceV1."
        )

    payload = {
        "claims": serialize_public_contract(provenance.claims),
        "contract_name": provenance.contract_name,
        "contract_version": provenance.contract_version,
        "proof": {
            "algorithm": provenance.proof.algorithm,
            "key_id": provenance.proof.key_id,
        },
    }
    return json.dumps(
        payload,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


__all__ = [
    "REFERENCE_ARCHITECTURE_AUTHENTICATED_PROVENANCE_SIGNING_PAYLOAD_CONTRACT_NAME",
    "REFERENCE_ARCHITECTURE_AUTHENTICATED_PROVENANCE_SIGNING_PAYLOAD_CONTRACT_VERSION",
    "canonical_reference_architecture_authenticated_provenance_signing_payload",
]
