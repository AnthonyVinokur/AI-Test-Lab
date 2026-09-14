from __future__ import annotations

import base64
import binascii
import re
from datetime import datetime
from typing import Literal

from pydantic import field_validator

from src.public_contract import PublicContractModel


REFERENCE_ARCHITECTURE_AUTHENTICATED_PROVENANCE_CONTRACT_NAME = (
    "ai-test-lab.reference-architecture-authenticated-provenance"
)
REFERENCE_ARCHITECTURE_AUTHENTICATED_PROVENANCE_CONTRACT_VERSION = "1.0"
REFERENCE_ARCHITECTURE_AUTHENTICATED_PROVENANCE_SIGNATURE_ALGORITHM = "ed25519"

_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
_UTC_TIMESTAMP_PATTERN = re.compile(
    r"[0-9]{4}-(?:0[1-9]|1[0-2])-"
    r"(?:0[1-9]|[12][0-9]|3[01])T"
    r"(?:[01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]Z"
)
_ED25519_SIGNATURE_BYTES = 64
_MAX_PUBLIC_IDENTITY_LENGTH = 256


class ReferenceArchitectureProvenanceClaimsV1(PublicContractModel):
    """Public provenance claims whose authenticity will be verified later."""

    attestation_id: str
    producer_id: str
    evidence_sha256: str
    issued_at: str

    @field_validator("attestation_id", "producer_id", mode="before")
    @classmethod
    def validate_public_identity(cls, value: object) -> str:
        if type(value) is not str or not value:
            raise ValueError("public provenance identities must be non-empty strings.")
        if len(value) > _MAX_PUBLIC_IDENTITY_LENGTH:
            raise ValueError("public provenance identities must not exceed 256 characters.")
        if any(character.isspace() or not character.isprintable() for character in value):
            raise ValueError(
                "public provenance identities must contain visible non-whitespace characters."
            )
        return value

    @field_validator("evidence_sha256", mode="before")
    @classmethod
    def validate_evidence_sha256(cls, value: object) -> str:
        if type(value) is not str or _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError(
                "evidence_sha256 must be 64 lowercase hexadecimal characters."
            )
        return value

    @field_validator("issued_at", mode="before")
    @classmethod
    def validate_issued_at(cls, value: object) -> str:
        if type(value) is not str or _UTC_TIMESTAMP_PATTERN.fullmatch(value) is None:
            raise ValueError("issued_at must be a canonical UTC timestamp in RFC 3339 form.")
        try:
            datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
        except ValueError as exc:
            raise ValueError("issued_at must be a valid UTC timestamp.") from exc
        return value


class ReferenceArchitectureProvenanceProofV1(PublicContractModel):
    """Public key reference and detached proof carried by the contract."""

    algorithm: Literal["ed25519"]
    key_id: str
    signature_base64: str

    @field_validator("key_id", mode="before")
    @classmethod
    def validate_key_id(cls, value: object) -> str:
        if type(value) is not str or not value:
            raise ValueError("key_id must be a non-empty string.")
        if len(value) > _MAX_PUBLIC_IDENTITY_LENGTH:
            raise ValueError("key_id must not exceed 256 characters.")
        if any(character.isspace() or not character.isprintable() for character in value):
            raise ValueError("key_id must contain visible non-whitespace characters.")
        return value

    @field_validator("signature_base64", mode="before")
    @classmethod
    def validate_signature_base64(cls, value: object) -> str:
        if type(value) is not str or not value:
            raise ValueError("signature_base64 must be a non-empty string.")
        try:
            decoded = base64.b64decode(value, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ValueError("signature_base64 must be canonical base64.") from exc
        if len(decoded) != _ED25519_SIGNATURE_BYTES:
            raise ValueError("signature_base64 must encode a 64-byte Ed25519 signature.")
        if base64.b64encode(decoded).decode("ascii") != value:
            raise ValueError("signature_base64 must be canonical base64.")
        return value


class ReferenceArchitectureAuthenticatedProvenanceV1(PublicContractModel):
    """ATL-A.03.01 public contract for producer-authentication evidence.

    This model validates only the immutable public shape. It does not verify
    the signature, trust the referenced key, bind the claims to an A.02
    outcome, or make freshness and replay decisions.
    """

    contract_name: Literal[
        "ai-test-lab.reference-architecture-authenticated-provenance"
    ]
    contract_version: Literal["1.0"]
    claims: ReferenceArchitectureProvenanceClaimsV1
    proof: ReferenceArchitectureProvenanceProofV1


def reference_architecture_authenticated_provenance_contract(
    *,
    attestation_id: str,
    producer_id: str,
    evidence_sha256: str,
    issued_at: str,
    key_id: str,
    signature_base64: str,
) -> ReferenceArchitectureAuthenticatedProvenanceV1:
    """Build the single authenticated-provenance contract ATL supports."""

    return ReferenceArchitectureAuthenticatedProvenanceV1(
        contract_name=REFERENCE_ARCHITECTURE_AUTHENTICATED_PROVENANCE_CONTRACT_NAME,
        contract_version=(
            REFERENCE_ARCHITECTURE_AUTHENTICATED_PROVENANCE_CONTRACT_VERSION
        ),
        claims=ReferenceArchitectureProvenanceClaimsV1(
            attestation_id=attestation_id,
            producer_id=producer_id,
            evidence_sha256=evidence_sha256,
            issued_at=issued_at,
        ),
        proof=ReferenceArchitectureProvenanceProofV1(
            algorithm=(
                REFERENCE_ARCHITECTURE_AUTHENTICATED_PROVENANCE_SIGNATURE_ALGORITHM
            ),
            key_id=key_id,
            signature_base64=signature_base64,
        ),
    )


__all__ = [
    "REFERENCE_ARCHITECTURE_AUTHENTICATED_PROVENANCE_CONTRACT_NAME",
    "REFERENCE_ARCHITECTURE_AUTHENTICATED_PROVENANCE_CONTRACT_VERSION",
    "REFERENCE_ARCHITECTURE_AUTHENTICATED_PROVENANCE_SIGNATURE_ALGORITHM",
    "ReferenceArchitectureAuthenticatedProvenanceV1",
    "ReferenceArchitectureProvenanceClaimsV1",
    "ReferenceArchitectureProvenanceProofV1",
    "reference_architecture_authenticated_provenance_contract",
]
