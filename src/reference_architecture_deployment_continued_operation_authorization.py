"""ATL-A.25 fail-closed authorization for continued operation of one deployment."""
from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import replace
from datetime import datetime, timezone
from typing import Any, Callable, Mapping

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from src.reference_architecture_deployment_continued_operation_authorization_contract import (
    CONTINUED_OPERATION_AUTHORIZATION_ALGORITHM,
    CONTINUED_OPERATION_AUTHORIZATION_CONTRACT_VERSION,
    AuthorizationSigningAuthority,
    ContinuedOperationAuthorization,
    ContinuedOperationAuthorizationError,
    ContinuedOperationAuthorizationInternalReason as Internal,
    ContinuedOperationAuthorizationOutcome,
    ContinuedOperationAuthorizationPolicy,
    ContinuedOperationAuthorizationReasonCode as PublicReason,
    ContinuedOperationAuthorizationState as State,
    ContinuedOperationAuthorizationVerification,
    ContinuedOperationGrant,
    ContinuedOperationLifecycleState,
    ContinuedOperationRequest,
    PublicContinuedOperationAuthorizationV1,
    ResolvedAuthorizationVerificationKey,
)
from src.reference_architecture_deployment_readiness_authentication import (
    verify_readiness_authentication,
)
from src.reference_architecture_deployment_readiness_authentication_contract import (
    READINESS_AUTHENTICATION_CONTRACT_VERSION,
    ReadinessAuthenticationPolicy,
    ReadinessAuthenticationState,
    ResolvedReadinessVerificationKey,
    SignedReadinessEnvelope,
    TrustedReadinessReference,
)
from src.reference_architecture_deployment_readiness_contract import DeploymentReadinessStatus
from src.reference_architecture_deployment_readiness_revalidation import ReadinessRevalidationResult
from src.reference_architecture_deployment_execution_contract import utc


_PROPOSITION_DOMAIN = "ai-test-lab:atl-a.25:continued-operation-proposition:v1"
_AUTHORIZATION_ID_DOMAIN = "ai-test-lab:atl-a.25:authorization-id:v1"
_SIGNING_DOMAIN = "ai-test-lab:atl-a.25:continued-operation-authorization:v1"


def _time(value: datetime) -> str:
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_time(value: object) -> datetime:
    if type(value) is not str or len(value) != 20 or not value.endswith("Z"):
        raise ValueError
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def _canonical(document: Mapping[str, Any]) -> bytes:
    try:
        return json.dumps(document, ensure_ascii=False, allow_nan=False, sort_keys=True,
                          separators=(",", ":")).encode("utf-8")
    except (TypeError, ValueError):
        raise ContinuedOperationAuthorizationError(
            "continued-operation canonical payload is invalid."
        ) from None


def continued_operation_request_document(value: ContinuedOperationRequest) -> dict[str, Any]:
    if type(value) is not ContinuedOperationRequest:
        raise ContinuedOperationAuthorizationError("an exact continued-operation request is required.")
    return {
        "consumer_id": value.consumer_id,
        "contract_version": value.contract_version,
        "deployment_id": value.deployment_id,
        "evaluation_time": _time(value.evaluation_time),
        "expected_readiness_contract_version": value.expected_readiness_contract_version,
        "policy_id": value.policy_id,
        "policy_version": value.policy_version,
        "purpose": value.purpose,
        "request_id": value.request_id,
        "requested_at": _time(value.requested_at),
        "requested_until": _time(value.requested_until),
    }


def translate_untrusted_continued_operation_request(
    value: bytes | str | Mapping[str, Any],
) -> ContinuedOperationRequest:
    """Strictly translate an untrusted request; unknown fields and noncanonical wire forms fail."""
    try:
        raw: bytes | None
        if type(value) is str:
            raw = value.encode("utf-8")
            document = json.loads(value)
        elif type(value) is bytes:
            raw = value
            document = json.loads(value)
        elif type(value) is dict:
            raw = None
            document = dict(value)
        else:
            raise ValueError
        fields = {
            "request_id", "deployment_id", "consumer_id", "purpose", "requested_at",
            "evaluation_time", "requested_until", "policy_id", "policy_version",
            "expected_readiness_contract_version", "contract_version",
        }
        if type(document) is not dict or set(document) != fields:
            raise ValueError
        for name in fields - {"requested_at", "evaluation_time", "requested_until"}:
            if type(document[name]) is not str:
                raise ValueError
        request = ContinuedOperationRequest(
            **{
                **document,
                "requested_at": _parse_time(document["requested_at"]),
                "evaluation_time": _parse_time(document["evaluation_time"]),
                "requested_until": _parse_time(document["requested_until"]),
            }
        )
        if raw is not None and raw != _canonical(continued_operation_request_document(request)):
            raise ValueError
        return request
    except Exception as error:
        raise ContinuedOperationAuthorizationError(
            "continued-operation request is invalid."
        ) from error


def _proposition_document(
    *, request_id: str, deployment_id: str, consumer_id: str, purpose: str,
    requested_at: datetime, issued_at: datetime, expires_at: datetime,
    readiness_attestation_digest: str, readiness_binding_fingerprint: str,
    readiness_issuer_id: str, readiness_key_id: str, readiness_contract_version: str,
    authorization_policy_id: str, authorization_policy_version: str,
    authorization_signer_id: str, authorization_key_id: str,
    contract_version: str,
) -> dict[str, Any]:
    return {
        "authorization_key_id": authorization_key_id,
        "authorization_policy_id": authorization_policy_id,
        "authorization_policy_version": authorization_policy_version,
        "authorization_signer_id": authorization_signer_id,
        "consumer_id": consumer_id,
        "contract_version": contract_version,
        "deployment_id": deployment_id,
        "domain": _PROPOSITION_DOMAIN,
        "expires_at": _time(expires_at),
        "issued_at": _time(issued_at),
        "not_before": _time(issued_at),
        "purpose": purpose,
        "readiness_attestation_digest": readiness_attestation_digest,
        "readiness_binding_fingerprint": readiness_binding_fingerprint,
        "readiness_contract_version": readiness_contract_version,
        "readiness_issuer_id": readiness_issuer_id,
        "readiness_key_id": readiness_key_id,
        "request_id": request_id,
        "requested_at": _time(requested_at),
    }


def continued_operation_proposition_digest(
    request: ContinuedOperationRequest,
    trusted_reference: TrustedReadinessReference,
    policy: ContinuedOperationAuthorizationPolicy,
    *, expires_at: datetime | None = None,
) -> str:
    """Digest the exact request, authenticated readiness, policy, signer, and validity."""
    if (type(request) is not ContinuedOperationRequest or
            type(trusted_reference) is not TrustedReadinessReference or
            type(policy) is not ContinuedOperationAuthorizationPolicy):
        raise ContinuedOperationAuthorizationError("continued-operation proposition is invalid.")
    effective_expiry = utc(expires_at or request.requested_until, "expires_at")
    document = _proposition_document(
        request_id=request.request_id, deployment_id=request.deployment_id,
        consumer_id=request.consumer_id, purpose=request.purpose,
        requested_at=request.requested_at, issued_at=request.evaluation_time,
        expires_at=effective_expiry,
        readiness_attestation_digest=trusted_reference.attestation_digest,
        readiness_binding_fingerprint=trusted_reference.binding_fingerprint,
        readiness_issuer_id=trusted_reference.issuer_id,
        readiness_key_id=trusted_reference.key_id,
        readiness_contract_version=trusted_reference.contract_version,
        authorization_policy_id=policy.policy_id,
        authorization_policy_version=policy.policy_version,
        authorization_signer_id=policy.signing_authority.signer_id,
        authorization_key_id=policy.signing_authority.key_id,
        contract_version=request.contract_version,
    )
    return hashlib.sha256(_canonical(document)).hexdigest()


def _artifact_proposition_digest(value: ContinuedOperationAuthorization) -> str:
    return hashlib.sha256(_canonical(_proposition_document(
        request_id=value.request_id, deployment_id=value.deployment_id,
        consumer_id=value.consumer_id, purpose=value.purpose,
        requested_at=value.requested_at, issued_at=value.issued_at,
        expires_at=value.expires_at,
        readiness_attestation_digest=value.readiness_attestation_digest,
        readiness_binding_fingerprint=value.readiness_binding_fingerprint,
        readiness_issuer_id=value.readiness_issuer_id,
        readiness_key_id=value.readiness_key_id,
        readiness_contract_version=value.readiness_contract_version,
        authorization_policy_id=value.authorization_policy_id,
        authorization_policy_version=value.authorization_policy_version,
        authorization_signer_id=value.authorization_signer_id,
        authorization_key_id=value.authorization_key_id,
        contract_version=value.contract_version,
    ))).hexdigest()


def _authorization_id(proposition_digest: str) -> str:
    return hashlib.sha256(_canonical({
        "domain": _AUTHORIZATION_ID_DOMAIN,
        "proposition_digest": proposition_digest,
    })).hexdigest()


def canonical_continued_operation_authorization_payload(
    value: ContinuedOperationAuthorization,
) -> bytes:
    if type(value) is not ContinuedOperationAuthorization:
        raise ContinuedOperationAuthorizationError("continued-operation authorization is invalid.")
    document = {
        "authorization_id": value.authorization_id,
        "proposition": _proposition_document(
            request_id=value.request_id, deployment_id=value.deployment_id,
            consumer_id=value.consumer_id, purpose=value.purpose,
            requested_at=value.requested_at, issued_at=value.issued_at,
            expires_at=value.expires_at,
            readiness_attestation_digest=value.readiness_attestation_digest,
            readiness_binding_fingerprint=value.readiness_binding_fingerprint,
            readiness_issuer_id=value.readiness_issuer_id,
            readiness_key_id=value.readiness_key_id,
            readiness_contract_version=value.readiness_contract_version,
            authorization_policy_id=value.authorization_policy_id,
            authorization_policy_version=value.authorization_policy_version,
            authorization_signer_id=value.authorization_signer_id,
            authorization_key_id=value.authorization_key_id,
            contract_version=value.contract_version,
        ),
        "proposition_digest": value.proposition_digest,
        "signature_algorithm": value.signature_algorithm,
        "signing_domain": _SIGNING_DOMAIN,
    }
    return _canonical(document)


def continued_operation_authorization_document(
    value: ContinuedOperationAuthorization,
) -> dict[str, Any]:
    if type(value) is not ContinuedOperationAuthorization:
        raise ContinuedOperationAuthorizationError("continued-operation authorization is invalid.")
    return {
        "authorization_id": value.authorization_id,
        "authorization_key_id": value.authorization_key_id,
        "authorization_policy_id": value.authorization_policy_id,
        "authorization_policy_version": value.authorization_policy_version,
        "authorization_signer_id": value.authorization_signer_id,
        "consumer_id": value.consumer_id,
        "contract_version": value.contract_version,
        "deployment_id": value.deployment_id,
        "expires_at": _time(value.expires_at),
        "issued_at": _time(value.issued_at),
        "not_before": _time(value.not_before),
        "proposition_digest": value.proposition_digest,
        "purpose": value.purpose,
        "readiness_attestation_digest": value.readiness_attestation_digest,
        "readiness_binding_fingerprint": value.readiness_binding_fingerprint,
        "readiness_contract_version": value.readiness_contract_version,
        "readiness_issuer_id": value.readiness_issuer_id,
        "readiness_key_id": value.readiness_key_id,
        "request_id": value.request_id,
        "requested_at": _time(value.requested_at),
        "signature_algorithm": value.signature_algorithm,
        "signature_base64": value.signature_base64,
    }


def translate_continued_operation_authorization(
    value: bytes | str | Mapping[str, Any],
) -> ContinuedOperationAuthorization:
    """Translate the canonical signed artifact without trusting any of its claims."""
    try:
        if type(value) is str:
            raw = value.encode("utf-8")
            document = json.loads(value)
        elif type(value) is bytes:
            raw = value
            document = json.loads(value)
        elif type(value) is dict:
            raw = None
            document = dict(value)
        else:
            raise ValueError
        fields = {
            "authorization_id", "authorization_key_id", "authorization_policy_id",
            "authorization_policy_version", "authorization_signer_id", "consumer_id",
            "contract_version", "deployment_id", "expires_at", "issued_at", "not_before",
            "proposition_digest", "purpose", "readiness_attestation_digest",
            "readiness_binding_fingerprint", "readiness_contract_version",
            "readiness_issuer_id", "readiness_key_id", "request_id", "requested_at",
            "signature_algorithm", "signature_base64",
        }
        if type(document) is not dict or set(document) != fields:
            raise ValueError
        if any(type(document[name]) is not str for name in fields):
            raise ValueError
        authorization = ContinuedOperationAuthorization(
            **{
                **document,
                "requested_at": _parse_time(document["requested_at"]),
                "issued_at": _parse_time(document["issued_at"]),
                "not_before": _parse_time(document["not_before"]),
                "expires_at": _parse_time(document["expires_at"]),
            }
        )
        if raw is not None and raw != _canonical(continued_operation_authorization_document(authorization)):
            raise ValueError
        return authorization
    except Exception as error:
        raise ContinuedOperationAuthorizationError(
            "continued-operation authorization document is invalid."
        ) from error


def _outcome(
    request: ContinuedOperationRequest, state: State,
    public: PublicReason | None = None, internal: Internal | None = None,
    authorization: ContinuedOperationAuthorization | None = None,
) -> ContinuedOperationAuthorizationOutcome:
    return ContinuedOperationAuthorizationOutcome(
        deployment_id=request.deployment_id,
        purpose=request.purpose,
        state=state,
        public_reason_codes=() if public is None else (public,),
        internal_reasons=() if internal is None else (internal,),
        decided_at=request.evaluation_time,
        authorization=authorization,
    )


def _denied(request: ContinuedOperationRequest, public: PublicReason,
            internal: Internal) -> ContinuedOperationAuthorizationOutcome:
    return _outcome(request, State.DENIED, public, internal)


def _review(request: ContinuedOperationRequest, public: PublicReason,
            internal: Internal) -> ContinuedOperationAuthorizationOutcome:
    return _outcome(request, State.REVIEW_REQUIRED, public, internal)


def _matches(scope: frozenset[str], value: str) -> bool:
    return value in scope or "*" in scope


def _grant_for(
    policy: ContinuedOperationAuthorizationPolicy, deployment_id: str,
) -> ContinuedOperationGrant | None:
    exact = next((item for item in policy.grants if item.deployment_id == deployment_id), None)
    return exact or next((item for item in policy.grants if item.deployment_id == "*"), None)


def _verification(
    value: ContinuedOperationAuthorization | None, checked_at: datetime, *,
    valid: bool, active: bool, applicable: bool,
    public: PublicReason | None = None, internal: Internal | None = None,
) -> ContinuedOperationAuthorizationVerification:
    return ContinuedOperationAuthorizationVerification(
        valid=valid, active=active, applicable=applicable,
        reason_code=public, internal_reason=internal, checked_at=checked_at,
        authorization_id=None if value is None else value.authorization_id,
        expires_at=None if value is None else value.expires_at,
    )


def verify_continued_operation_authorization(
    value: ContinuedOperationAuthorization,
    *, resolved_key: ResolvedAuthorizationVerificationKey | None,
    verification_time: datetime,
    expected_deployment_id: str | None = None,
    expected_consumer_id: str | None = None,
    expected_purpose: str | None = None,
) -> ContinuedOperationAuthorizationVerification:
    """Independently verify an ATL-A.25 artifact for the future A.26 boundary."""
    now = utc(verification_time, "verification_time")
    if type(value) is not ContinuedOperationAuthorization:
        return _verification(None, now, valid=False, active=False, applicable=False,
                             public=PublicReason.REQUEST_BINDING_INVALID,
                             internal=Internal.AUTHORIZATION_BINDING_INVALID)
    if value.readiness_contract_version != READINESS_AUTHENTICATION_CONTRACT_VERSION:
        return _verification(value, now, valid=False, active=False, applicable=False,
                             public=PublicReason.REQUEST_BINDING_INVALID,
                             internal=Internal.CONTRACT_VERSION_NOT_PERMITTED)
    expected_digest = _artifact_proposition_digest(value)
    if (value.proposition_digest != expected_digest or
            value.authorization_id != _authorization_id(expected_digest)):
        return _verification(value, now, valid=False, active=False, applicable=False,
                             public=PublicReason.REQUEST_BINDING_INVALID,
                             internal=Internal.AUTHORIZATION_BINDING_INVALID)
    if now < value.not_before:
        return _verification(value, now, valid=True, active=False, applicable=False,
                             public=PublicReason.REQUEST_BINDING_INVALID,
                             internal=Internal.AUTHORIZATION_NOT_YET_VALID)
    if now >= value.expires_at:
        return _verification(value, now, valid=True, active=False, applicable=False,
                             public=PublicReason.READINESS_REFERENCE_EXPIRED,
                             internal=Internal.AUTHORIZATION_EXPIRED)
    if resolved_key is None:
        return _verification(value, now, valid=False, active=True, applicable=False,
                             public=PublicReason.AUTHORIZATION_POLICY_UNAVAILABLE,
                             internal=Internal.SIGNING_KEY_UNAVAILABLE)
    if (type(resolved_key) is not ResolvedAuthorizationVerificationKey or
            resolved_key.signer_id != value.authorization_signer_id or
            resolved_key.key_id != value.authorization_key_id or
            resolved_key.algorithm != value.signature_algorithm):
        return _verification(value, now, valid=False, active=True, applicable=False,
                             public=PublicReason.AUTHORIZATION_AUTHORITY_NOT_TRUSTED,
                             internal=Internal.SIGNING_AUTHORITY_MISMATCH)
    if (resolved_key.lifecycle_state is not ContinuedOperationLifecycleState.ACTIVE or
            now < resolved_key.active_from or now >= resolved_key.expires_at):
        return _verification(value, now, valid=False, active=False, applicable=False,
                             public=PublicReason.AUTHORIZATION_AUTHORITY_NOT_TRUSTED,
                             internal=Internal.SIGNING_AUTHORITY_NOT_ACTIVE)
    try:
        Ed25519PublicKey.from_public_bytes(resolved_key.public_key).verify(
            base64.b64decode(value.signature_base64, validate=True),
            canonical_continued_operation_authorization_payload(value),
        )
    except (InvalidSignature, ValueError, TypeError):
        return _verification(value, now, valid=False, active=True, applicable=False,
                             public=PublicReason.AUTHORIZATION_AUTHORITY_NOT_TRUSTED,
                             internal=Internal.INVALID_AUTHORIZATION_SIGNATURE)
    applicable = (
        (expected_deployment_id is None or expected_deployment_id == value.deployment_id) and
        (expected_consumer_id is None or expected_consumer_id == value.consumer_id) and
        (expected_purpose is None or expected_purpose == value.purpose)
    )
    if not applicable:
        return _verification(value, now, valid=True, active=True, applicable=False,
                             public=PublicReason.REQUEST_BINDING_INVALID,
                             internal=Internal.AUTHORIZATION_NOT_APPLICABLE)
    return _verification(value, now, valid=True, active=True, applicable=True)


def authorize_continued_operation(
    request: ContinuedOperationRequest,
    *, readiness_result: ReadinessRevalidationResult,
    readiness_envelope: SignedReadinessEnvelope,
    readiness_policy: ReadinessAuthenticationPolicy | None,
    readiness_key: ResolvedReadinessVerificationKey | None,
    authorization_policy: ContinuedOperationAuthorizationPolicy | None,
    resolved_authorization_key: ResolvedAuthorizationVerificationKey | None,
    signer: Callable[[bytes], bytes] | None,
) -> ContinuedOperationAuthorizationOutcome:
    """Authorize intent only; no operational or lifecycle action is performed."""
    if type(request) is not ContinuedOperationRequest:
        raise ContinuedOperationAuthorizationError("an exact continued-operation request is required.")
    try:
        readiness = verify_readiness_authentication(
            readiness_result, envelope=readiness_envelope, policy=readiness_policy,
            resolved_key=readiness_key, verification_time=request.evaluation_time,
        )
    except Exception:
        return _denied(request, PublicReason.READINESS_NOT_ELIGIBLE,
                       Internal.READINESS_AUTHENTICATION_REJECTED)
    if readiness.authentication_state is not ReadinessAuthenticationState.VERIFIED:
        reason = (Internal.READINESS_AUTHENTICATION_INCOMPLETE
                  if readiness.authentication_state is ReadinessAuthenticationState.REVIEW_REQUIRED
                  else Internal.READINESS_AUTHENTICATION_REJECTED)
        return _denied(request, PublicReason.READINESS_NOT_ELIGIBLE, reason)
    if readiness.readiness_status is not DeploymentReadinessStatus.READY:
        return _denied(request, PublicReason.READINESS_NOT_ELIGIBLE,
                       Internal.READINESS_STATUS_INELIGIBLE)
    trusted = readiness.trusted_reference
    if type(trusted) is not TrustedReadinessReference:
        return _denied(request, PublicReason.READINESS_NOT_ELIGIBLE,
                       Internal.TRUSTED_REFERENCE_MISSING)
    if trusted.deployment_id != readiness.deployment_id:
        return _denied(request, PublicReason.REQUEST_BINDING_INVALID,
                       Internal.TRUSTED_REFERENCE_INCONSISTENT)
    if request.evaluation_time >= trusted.expires_at:
        return _denied(request, PublicReason.READINESS_REFERENCE_EXPIRED,
                       Internal.READINESS_REFERENCE_EXPIRED)
    if request.deployment_id != trusted.deployment_id:
        return _denied(request, PublicReason.REQUEST_BINDING_INVALID,
                       Internal.DEPLOYMENT_MISMATCH)
    if authorization_policy is None:
        return _review(request, PublicReason.AUTHORIZATION_POLICY_UNAVAILABLE,
                       Internal.POLICY_UNAVAILABLE)
    if type(authorization_policy) is not ContinuedOperationAuthorizationPolicy:
        return _denied(request, PublicReason.CONTINUED_OPERATION_NOT_PERMITTED,
                       Internal.POLICY_MISMATCH)
    policy = authorization_policy
    now = request.evaluation_time
    if request.policy_id != policy.policy_id or request.policy_version != policy.policy_version:
        return _denied(request, PublicReason.REQUEST_BINDING_INVALID, Internal.POLICY_MISMATCH)
    if (policy.lifecycle_state is not ContinuedOperationLifecycleState.ACTIVE or
            now < policy.active_from or now >= policy.expires_at):
        return _denied(request, PublicReason.CONTINUED_OPERATION_NOT_PERMITTED,
                       Internal.POLICY_NOT_ACTIVE)
    if (request.expected_readiness_contract_version != trusted.contract_version or
            trusted.contract_version not in policy.accepted_readiness_contract_versions or
            trusted.contract_version != READINESS_AUTHENTICATION_CONTRACT_VERSION):
        return _denied(request, PublicReason.REQUEST_BINDING_INVALID,
                       Internal.CONTRACT_VERSION_NOT_PERMITTED)
    if (trusted.issuer_id, trusted.key_id) not in policy.permitted_readiness_authorities:
        return _denied(request, PublicReason.AUTHORIZATION_AUTHORITY_NOT_TRUSTED,
                       Internal.READINESS_AUTHORITY_NOT_PERMITTED)
    grant = _grant_for(policy, request.deployment_id)
    if grant is None:
        return _denied(request, PublicReason.CONTINUED_OPERATION_NOT_PERMITTED,
                       Internal.DEPLOYMENT_NOT_PERMITTED)
    if not _matches(grant.permitted_consumers, request.consumer_id):
        return _denied(request, PublicReason.CONTINUED_OPERATION_NOT_PERMITTED,
                       Internal.CONSUMER_NOT_PERMITTED)
    if not _matches(grant.permitted_purposes, request.purpose):
        return _denied(request, PublicReason.CONTINUED_OPERATION_NOT_PERMITTED,
                       Internal.PURPOSE_NOT_PERMITTED)
    if request.requested_at > now or request.requested_until <= now:
        return _denied(request, PublicReason.REQUEST_BINDING_INVALID,
                       Internal.REQUEST_TIME_INVALID)
    if (request.requested_until - now).total_seconds() > policy.maximum_duration_seconds:
        return _denied(request, PublicReason.CONTINUED_OPERATION_NOT_PERMITTED,
                       Internal.REQUESTED_DURATION_EXCEEDED)
    authority: AuthorizationSigningAuthority = policy.signing_authority
    if (authority.lifecycle_state is not ContinuedOperationLifecycleState.ACTIVE or
            now < authority.active_from or now >= authority.expires_at):
        return _denied(request, PublicReason.AUTHORIZATION_AUTHORITY_NOT_TRUSTED,
                       Internal.SIGNING_AUTHORITY_NOT_ACTIVE)
    if not _matches(authority.permitted_deployments, request.deployment_id):
        return _denied(request, PublicReason.AUTHORIZATION_AUTHORITY_NOT_TRUSTED,
                       Internal.SIGNING_AUTHORITY_MISMATCH)
    validity_limit = min(trusted.expires_at, policy.expires_at, authority.expires_at)
    if request.requested_until > validity_limit:
        return _denied(request, PublicReason.READINESS_REFERENCE_EXPIRED,
                       Internal.REQUESTED_EXPIRY_EXCEEDED)
    if resolved_authorization_key is None and policy.require_resolved_signing_key:
        return _review(request, PublicReason.AUTHORIZATION_POLICY_UNAVAILABLE,
                       Internal.SIGNING_KEY_UNAVAILABLE)
    if resolved_authorization_key is None or signer is None:
        return _review(request, PublicReason.AUTHORIZATION_POLICY_UNAVAILABLE,
                       Internal.SIGNING_KEY_UNAVAILABLE)
    key = resolved_authorization_key
    if (type(key) is not ResolvedAuthorizationVerificationKey or
            key.signer_id != authority.signer_id or key.key_id != authority.key_id or
            key.algorithm != authority.algorithm):
        return _denied(request, PublicReason.AUTHORIZATION_AUTHORITY_NOT_TRUSTED,
                       Internal.SIGNING_AUTHORITY_MISMATCH)
    if (key.lifecycle_state is not ContinuedOperationLifecycleState.ACTIVE or
            now < key.active_from or now >= key.expires_at):
        return _denied(request, PublicReason.AUTHORIZATION_AUTHORITY_NOT_TRUSTED,
                       Internal.SIGNING_AUTHORITY_NOT_ACTIVE)
    if request.requested_until > key.expires_at:
        return _denied(request, PublicReason.AUTHORIZATION_AUTHORITY_NOT_TRUSTED,
                       Internal.REQUESTED_EXPIRY_EXCEEDED)
    proposition_digest = continued_operation_proposition_digest(request, trusted, policy)
    unsigned = ContinuedOperationAuthorization(
        authorization_id=_authorization_id(proposition_digest), request_id=request.request_id,
        deployment_id=request.deployment_id, consumer_id=request.consumer_id,
        purpose=request.purpose, readiness_attestation_digest=trusted.attestation_digest,
        readiness_binding_fingerprint=trusted.binding_fingerprint,
        readiness_issuer_id=trusted.issuer_id, readiness_key_id=trusted.key_id,
        readiness_contract_version=trusted.contract_version,
        authorization_policy_id=policy.policy_id,
        authorization_policy_version=policy.policy_version,
        authorization_signer_id=authority.signer_id, authorization_key_id=authority.key_id,
        requested_at=request.requested_at, issued_at=now, not_before=now,
        expires_at=request.requested_until, proposition_digest=proposition_digest,
        signature_algorithm=CONTINUED_OPERATION_AUTHORIZATION_ALGORITHM,
        signature_base64=base64.b64encode(bytes(64)).decode("ascii"),
        contract_version=CONTINUED_OPERATION_AUTHORIZATION_CONTRACT_VERSION,
    )
    try:
        signature = signer(canonical_continued_operation_authorization_payload(unsigned))
    except Exception:
        return _denied(request, PublicReason.AUTHORIZATION_AUTHORITY_NOT_TRUSTED,
                       Internal.SIGNING_FAILED)
    if type(signature) is not bytes or len(signature) != 64:
        return _denied(request, PublicReason.AUTHORIZATION_AUTHORITY_NOT_TRUSTED,
                       Internal.SIGNING_FAILED)
    authorization = replace(unsigned, signature_base64=base64.b64encode(signature).decode("ascii"))
    verification = verify_continued_operation_authorization(
        authorization, resolved_key=key, verification_time=now,
        expected_deployment_id=request.deployment_id,
        expected_consumer_id=request.consumer_id, expected_purpose=request.purpose,
    )
    if not (verification.valid and verification.active and verification.applicable):
        return _denied(request, PublicReason.AUTHORIZATION_AUTHORITY_NOT_TRUSTED,
                       verification.internal_reason or Internal.INVALID_AUTHORIZATION_SIGNATURE)
    return _outcome(request, State.AUTHORIZED, authorization=authorization)


def public_continued_operation_authorization(
    value: ContinuedOperationAuthorizationOutcome,
) -> PublicContinuedOperationAuthorizationV1:
    if type(value) is not ContinuedOperationAuthorizationOutcome:
        raise ContinuedOperationAuthorizationError("authorization outcome is invalid.")
    return PublicContinuedOperationAuthorizationV1(
        deployment_id=value.deployment_id, purpose=value.purpose,
        authorization_state=value.state, reason_codes=value.public_reason_codes,
        decided_at=value.decided_at,
        expires_at=None if value.authorization is None else value.authorization.expires_at,
    )


__all__ = [
    "authorize_continued_operation",
    "canonical_continued_operation_authorization_payload",
    "continued_operation_authorization_document",
    "continued_operation_proposition_digest",
    "continued_operation_request_document",
    "public_continued_operation_authorization",
    "translate_continued_operation_authorization",
    "translate_untrusted_continued_operation_request",
    "verify_continued_operation_authorization",
]
