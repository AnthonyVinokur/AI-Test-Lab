"""ATL-A.24 authentication for exact fresh ATL-A.23 readiness results."""
from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import fields, is_dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from src.reference_architecture_deployment_execution_contract import utc
from src.reference_architecture_deployment_readiness import verify_deployment_readiness_attestation
from src.reference_architecture_deployment_readiness_authentication_contract import *
from src.reference_architecture_deployment_readiness_contract import DeploymentReadinessStatus
from src.reference_architecture_deployment_readiness_revalidation import (
    ReadinessEvidenceBinding, ReadinessRevalidationResult,
)


_BINDING_DOMAIN = "ai-test-lab:atl-a.24:readiness-binding:v1"
_SIGNING_DOMAIN = "ai-test-lab:atl-a.24:readiness-authentication:v1"


def _time(value: datetime) -> str:
    return utc(value, "timestamp").strftime("%Y-%m-%dT%H:%M:%SZ")


def _canonical_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return _time(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, bytes):
        return base64.b64encode(value).decode("ascii")
    if is_dataclass(value):
        return {field.name: _canonical_value(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, (tuple, list)):
        return [_canonical_value(item) for item in value]
    if isinstance(value, (frozenset, set)):
        return sorted((_canonical_value(item) for item in value), key=lambda item: json.dumps(item, sort_keys=True))
    if isinstance(value, dict):
        return {str(key): _canonical_value(item) for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))}
    if value is None or type(value) in {str, int, float, bool}:
        return value
    raise ReadinessAuthenticationError("readiness binding contains unsupported data.")


def _canonical(document: dict[str, Any]) -> bytes:
    try:
        return json.dumps(document, ensure_ascii=False, allow_nan=False,
                          sort_keys=True, separators=(",", ":")).encode("utf-8")
    except (TypeError, ValueError):
        raise ReadinessAuthenticationError("readiness canonical payload is invalid.") from None


def _adapt(value: object) -> ReadinessRevalidationResult:
    if type(value) is not ReadinessRevalidationResult:
        raise ReadinessAuthenticationError("an exact ATL-A.23 revalidation result is required.")
    result = value
    binding = result.binding
    if (type(binding) is not ReadinessEvidenceBinding or result.attestation != binding.attestation or
            binding.evidence.deployment_id != result.attestation.deployment_id or
            not verify_deployment_readiness_attestation(result.attestation)):
        raise ReadinessAuthenticationError("ATL-A.23 readiness binding is invalid.")
    try:
        issued = utc(result.attestation.attested_at, "attested_at")
        expiry = utc(binding.expires_at, "expires_at")
    except (ValueError, OverflowError):
        raise ReadinessAuthenticationError("ATL-A.23 readiness binding is invalid.") from None
    if expiry <= issued:
        raise ReadinessAuthenticationError("ATL-A.23 readiness binding is invalid.")
    return result


def readiness_binding_fingerprint(value: ReadinessRevalidationResult) -> str:
    """Hash the exact fresh attestation and evidence binding from ATL-A.23."""
    result = _adapt(value)
    document = {
        "domain": _BINDING_DOMAIN,
        "deployment_id": result.attestation.deployment_id,
        "attestation": _canonical_value(result.attestation),
        "evidence": _canonical_value(result.binding.evidence),
        "evidence_revision": result.binding.evidence.revision,
        "issued_at": _time(result.attestation.attested_at),
        "expires_at": _time(result.binding.expires_at),
    }
    return hashlib.sha256(_canonical(document)).hexdigest()


def canonical_readiness_authentication_payload(claims: ReadinessAuthenticationClaims) -> bytes:
    if type(claims) is not ReadinessAuthenticationClaims:
        raise ReadinessAuthenticationError("readiness authentication claims are invalid.")
    return _canonical({"domain": _SIGNING_DOMAIN, "claims": _canonical_value(claims)})


def create_signed_readiness_envelope(
    value: ReadinessRevalidationResult, *, issuer_id: str, key_id: str,
    policy_id: str, policy_version: str, signer: Callable[[bytes], bytes],
) -> SignedReadinessEnvelope:
    """Build claims from A.23 and request a detached signature; no private key is retained."""
    result = _adapt(value)
    claims = ReadinessAuthenticationClaims(
        deployment_id=result.attestation.deployment_id,
        readiness_status=result.attestation.status,
        readiness_reason_codes=tuple(reason.value for reason in result.attestation.reason_codes),
        attestation_digest=result.attestation.attestation_digest,
        binding_fingerprint=readiness_binding_fingerprint(result),
        issuer_id=issuer_id, key_id=key_id, algorithm=READINESS_AUTHENTICATION_ALGORITHM,
        policy_id=policy_id, policy_version=policy_version,
        issued_at=result.attestation.attested_at, expires_at=result.binding.expires_at,
    )
    try:
        signature = signer(canonical_readiness_authentication_payload(claims))
    except Exception:
        raise ReadinessAuthenticationError("readiness signing failed.") from None
    if type(signature) is not bytes or len(signature) != 64:
        raise ReadinessAuthenticationError("readiness signer returned an invalid signature.")
    return SignedReadinessEnvelope(claims, base64.b64encode(signature).decode("ascii"))


def _outcome(result: ReadinessRevalidationResult, state: ReadinessAuthenticationState,
             public: tuple[ReadinessAuthenticationReasonCode, ...],
             internal: tuple[ReadinessAuthenticationInternalReason, ...], now: datetime,
             trusted: TrustedReadinessReference | None = None) -> ReadinessAuthenticationOutcome:
    return ReadinessAuthenticationOutcome(result.attestation.deployment_id, result.attestation.status,
                                          state, tuple(dict.fromkeys(public)),
                                          tuple(dict.fromkeys(internal)), now, trusted)


def _rejected(result: ReadinessRevalidationResult, now: datetime,
              public: ReadinessAuthenticationReasonCode,
              internal: ReadinessAuthenticationInternalReason) -> ReadinessAuthenticationOutcome:
    return _outcome(result, ReadinessAuthenticationState.REJECTED, (public,), (internal,), now)


def verify_readiness_authentication(
    value: ReadinessRevalidationResult, *, envelope: SignedReadinessEnvelope,
    policy: ReadinessAuthenticationPolicy | None,
    resolved_key: ResolvedReadinessVerificationKey | None,
    verification_time: datetime,
) -> ReadinessAuthenticationOutcome:
    """Authenticate A.23 without rerunning ATL-A.22 or exposing crypto diagnostics."""
    now = utc(verification_time, "verification_time")
    try:
        result = _adapt(value)
    except ReadinessAuthenticationError:
        # A non-result has no safe identifier to project and is a programmer-boundary error.
        raise
    if type(envelope) is not SignedReadinessEnvelope:
        return _rejected(result, now, ReadinessAuthenticationReasonCode.AUTHENTICITY_NOT_VERIFIED,
                         ReadinessAuthenticationInternalReason.INVALID_SIGNATURE)
    claims = envelope.claims
    try:
        expected = (
            claims.deployment_id == result.attestation.deployment_id and
            claims.readiness_status is result.attestation.status and
            claims.readiness_reason_codes == tuple(reason.value for reason in result.attestation.reason_codes) and
            claims.attestation_digest == result.attestation.attestation_digest and
            claims.binding_fingerprint == readiness_binding_fingerprint(result) and
            claims.issued_at == result.attestation.attested_at and
            claims.expires_at == result.binding.expires_at
        )
    except ReadinessAuthenticationError:
        expected = False
    if not expected:
        return _rejected(result, now, ReadinessAuthenticationReasonCode.BINDING_INVALID,
                         ReadinessAuthenticationInternalReason.CLAIMS_MISMATCH)
    if now < claims.issued_at:
        return _rejected(result, now, ReadinessAuthenticationReasonCode.BINDING_INVALID,
                         ReadinessAuthenticationInternalReason.INVALID_BINDING_TIME)
    if now >= claims.expires_at:
        return _rejected(result, now, ReadinessAuthenticationReasonCode.RECORD_EXPIRED,
                         ReadinessAuthenticationInternalReason.BINDING_EXPIRED)
    if policy is None:
        return _outcome(result, ReadinessAuthenticationState.REVIEW_REQUIRED,
                        (ReadinessAuthenticationReasonCode.VERIFICATION_MATERIAL_UNAVAILABLE,),
                        (ReadinessAuthenticationInternalReason.POLICY_UNAVAILABLE,), now)
    if type(policy) is not ReadinessAuthenticationPolicy:
        return _rejected(result, now, ReadinessAuthenticationReasonCode.AUTHORITY_NOT_TRUSTED,
                         ReadinessAuthenticationInternalReason.POLICY_MISMATCH)
    if resolved_key is None:
        return _outcome(result, ReadinessAuthenticationState.REVIEW_REQUIRED,
                        (ReadinessAuthenticationReasonCode.VERIFICATION_MATERIAL_UNAVAILABLE,),
                        (ReadinessAuthenticationInternalReason.KEY_UNAVAILABLE,), now)
    if type(resolved_key) is not ResolvedReadinessVerificationKey:
        return _rejected(result, now, ReadinessAuthenticationReasonCode.AUTHORITY_NOT_TRUSTED,
                         ReadinessAuthenticationInternalReason.KEY_INVALID)
    if (claims.policy_id != policy.policy_id or claims.policy_version != policy.policy_version or
            claims.contract_version not in policy.accepted_contract_versions):
        return _rejected(result, now, ReadinessAuthenticationReasonCode.AUTHORITY_NOT_TRUSTED,
                         ReadinessAuthenticationInternalReason.POLICY_MISMATCH)
    grant = next((item for item in policy.authorizations
                  if item.issuer_id == claims.issuer_id and item.key_id == claims.key_id), None)
    if grant is None or (claims.deployment_id not in grant.permitted_deployments and
                         "*" not in grant.permitted_deployments) or grant.algorithm != claims.algorithm:
        return _rejected(result, now, ReadinessAuthenticationReasonCode.AUTHORITY_NOT_TRUSTED,
                         ReadinessAuthenticationInternalReason.ISSUER_NOT_AUTHORIZED)
    if (grant.status is not ReadinessAuthorityStatus.ACTIVE or now < grant.active_from or
            (grant.expires_at is not None and now >= grant.expires_at)):
        return _rejected(result, now, ReadinessAuthenticationReasonCode.AUTHORITY_NOT_TRUSTED,
                         ReadinessAuthenticationInternalReason.AUTHORITY_NOT_ACTIVE)
    if (resolved_key.issuer_id != claims.issuer_id or resolved_key.key_id != claims.key_id or
            resolved_key.algorithm != claims.algorithm):
        return _rejected(result, now, ReadinessAuthenticationReasonCode.AUTHORITY_NOT_TRUSTED,
                         ReadinessAuthenticationInternalReason.KEY_MISMATCH)
    if (resolved_key.status is not ReadinessAuthorityStatus.ACTIVE or now < resolved_key.active_from or
            (resolved_key.expires_at is not None and now >= resolved_key.expires_at)):
        return _rejected(result, now, ReadinessAuthenticationReasonCode.AUTHORITY_NOT_TRUSTED,
                         ReadinessAuthenticationInternalReason.KEY_NOT_ACTIVE)
    try:
        Ed25519PublicKey.from_public_bytes(resolved_key.public_key).verify(
            base64.b64decode(envelope.signature_base64, validate=True),
            canonical_readiness_authentication_payload(claims),
        )
    except (InvalidSignature, ValueError, TypeError):
        return _rejected(result, now, ReadinessAuthenticationReasonCode.AUTHENTICITY_NOT_VERIFIED,
                         ReadinessAuthenticationInternalReason.INVALID_SIGNATURE)
    trusted = None
    if result.attestation.status is DeploymentReadinessStatus.READY:
        trusted = TrustedReadinessReference(
            claims.deployment_id, claims.attestation_digest, claims.binding_fingerprint,
            claims.issuer_id, claims.key_id, now, claims.expires_at,
        )
    return _outcome(result, ReadinessAuthenticationState.VERIFIED, (), (), now, trusted)


def public_readiness_authentication_outcome(
    value: ReadinessAuthenticationOutcome,
) -> PublicReadinessAuthenticationOutcomeV1:
    if type(value) is not ReadinessAuthenticationOutcome:
        raise ReadinessAuthenticationError("readiness authentication outcome is invalid.")
    return PublicReadinessAuthenticationOutcomeV1(
        deployment_id=value.deployment_id, readiness_status=value.readiness_status,
        authentication_state=value.authentication_state, reason_codes=value.public_reason_codes,
        verified_at=value.verified_at,
    )


__all__ = ["canonical_readiness_authentication_payload", "create_signed_readiness_envelope",
           "public_readiness_authentication_outcome", "readiness_binding_fingerprint",
           "verify_readiness_authentication"]
