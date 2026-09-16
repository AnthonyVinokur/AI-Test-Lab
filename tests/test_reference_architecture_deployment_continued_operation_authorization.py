import base64
import json
from dataclasses import FrozenInstanceError, replace
from datetime import timedelta

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from src.public_contract import serialize_public_contract
from src.reference_architecture_deployment_continued_operation_authorization import (
    authorize_continued_operation,
    canonical_continued_operation_authorization_payload,
    continued_operation_authorization_document,
    continued_operation_proposition_digest,
    continued_operation_request_document,
    public_continued_operation_authorization,
    translate_continued_operation_authorization,
    translate_untrusted_continued_operation_request,
    verify_continued_operation_authorization,
)
from src.reference_architecture_deployment_continued_operation_authorization_contract import (
    CONTINUED_OPERATION_AUTHORIZATION_CONTRACT_VERSION,
    AuthorizationSigningAuthority,
    ContinuedOperationAuthorizationError,
    ContinuedOperationAuthorizationInternalReason as Internal,
    ContinuedOperationAuthorizationPolicy,
    ContinuedOperationAuthorizationReasonCode as PublicReason,
    ContinuedOperationAuthorizationState as AuthorizationState,
    ContinuedOperationGrant,
    ContinuedOperationLifecycleState as Lifecycle,
    ContinuedOperationRequest,
    ResolvedAuthorizationVerificationKey,
)
from src.reference_architecture_deployment_integrity_contract import TrustStatus
from src.reference_architecture_deployment_readiness_authentication import (
    verify_readiness_authentication,
)
from src.reference_architecture_deployment_readiness_authentication_contract import (
    READINESS_AUTHENTICATION_CONTRACT_VERSION,
    ReadinessAuthorityStatus,
)
from tests.test_reference_architecture_deployment_readiness_authentication import (
    envelope as readiness_envelope,
    key as readiness_key,
    policy as readiness_policy,
    result as readiness_result,
)
from tests.test_reference_architecture_deployment_recovery import NOW


AUTHORIZATION_KEY = Ed25519PrivateKey.from_private_bytes(bytes(range(33, 65)))
AUTHORIZATION_PUBLIC_KEY = AUTHORIZATION_KEY.public_key().public_bytes(
    serialization.Encoding.Raw, serialization.PublicFormat.Raw,
)


def request(**overrides):
    arguments = dict(
        request_id="continued-operation-request-1",
        deployment_id="deployment",
        consumer_id="production-gateway",
        purpose="serve-production-traffic",
        requested_at=NOW,
        evaluation_time=NOW,
        requested_until=NOW + timedelta(minutes=30),
        policy_id="continued-operation-policy",
        policy_version="1",
        expected_readiness_contract_version=READINESS_AUTHENTICATION_CONTRACT_VERSION,
    )
    arguments.update(overrides)
    return ContinuedOperationRequest(**arguments)


def authorization_policy_contract(
    lifecycle=Lifecycle.ACTIVE, *, consumers=frozenset({"production-gateway"}),
    purposes=frozenset({"serve-production-traffic"}), deployments=("deployment",),
    readiness_authorities=frozenset({("readiness-issuer", "readiness-key-1")}),
    maximum_duration_seconds=3600, policy_expires_at=NOW + timedelta(hours=2),
    signer_lifecycle=Lifecycle.ACTIVE, signer_expires_at=NOW + timedelta(hours=2),
):
    grants = tuple(
        ContinuedOperationGrant(item, consumers, purposes) for item in deployments
    )
    authority = AuthorizationSigningAuthority(
        "continued-operation-authorizer", "authorization-key-1", "ed25519",
        NOW - timedelta(hours=1), signer_expires_at, signer_lifecycle,
        frozenset(deployments),
    )
    return ContinuedOperationAuthorizationPolicy(
        "continued-operation-policy", "1", NOW - timedelta(hours=1),
        policy_expires_at, lifecycle, grants, maximum_duration_seconds,
        frozenset({READINESS_AUTHENTICATION_CONTRACT_VERSION}),
        readiness_authorities, authority,
    )


def authorization_key_contract(
    lifecycle=Lifecycle.ACTIVE, *, public_key=AUTHORIZATION_PUBLIC_KEY,
    expires_at=NOW + timedelta(hours=2),
):
    return ResolvedAuthorizationVerificationKey(
        "continued-operation-authorizer", "authorization-key-1", "ed25519",
        public_key, NOW - timedelta(hours=1), expires_at, lifecycle,
    )


def authorize(req=None, ready=None, signed=None, **overrides):
    req = req or request()
    ready = ready or readiness_result()
    arguments = dict(
        readiness_result=ready,
        readiness_envelope=signed or readiness_envelope(ready),
        readiness_policy=readiness_policy(),
        readiness_key=readiness_key(),
        authorization_policy=authorization_policy_contract(),
        resolved_authorization_key=authorization_key_contract(),
        signer=AUTHORIZATION_KEY.sign,
    )
    arguments.update(overrides)
    return authorize_continued_operation(req, **arguments)


def authorized_artifact():
    outcome = authorize()
    assert outcome.authorization is not None
    return outcome.authorization


def canonical_wire(document):
    return json.dumps(document, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


def test_verified_ready_result_produces_narrow_independently_verifiable_authorization():
    outcome = authorize()
    assert outcome.state is AuthorizationState.AUTHORIZED
    assert outcome.public_reason_codes == () and outcome.internal_reasons == ()
    value = outcome.authorization
    assert value is not None
    assert value.deployment_id == "deployment"
    assert value.consumer_id == "production-gateway"
    assert value.purpose == "serve-production-traffic"
    assert value.expires_at == request().requested_until
    verified = verify_continued_operation_authorization(
        value, resolved_key=authorization_key_contract(), verification_time=NOW,
        expected_deployment_id="deployment", expected_consumer_id="production-gateway",
        expected_purpose="serve-production-traffic",
    )
    assert verified.valid and verified.active and verified.applicable


@pytest.mark.parametrize("status", [TrustStatus.UNTRUSTED, TrustStatus.INDETERMINATE])
def test_authenticated_nonready_results_are_denied(status):
    ready = readiness_result(status)
    outcome = authorize(ready=ready, signed=readiness_envelope(ready))
    assert outcome.state is AuthorizationState.DENIED
    assert outcome.public_reason_codes == (PublicReason.READINESS_NOT_ELIGIBLE,)
    assert outcome.internal_reasons == (Internal.READINESS_STATUS_INELIGIBLE,)
    assert outcome.authorization is None


def test_rejected_or_incomplete_a24_authentication_cannot_authorize():
    ready = readiness_result()
    signed = readiness_envelope(ready)
    raw = bytearray(base64.b64decode(signed.signature_base64))
    raw[0] ^= 1
    tampered = replace(signed, signature_base64=base64.b64encode(raw).decode("ascii"))
    rejected = authorize(ready=ready, signed=tampered)
    incomplete = authorize(ready=ready, signed=signed, readiness_policy=None)
    assert rejected.state is AuthorizationState.DENIED
    assert rejected.internal_reasons == (Internal.READINESS_AUTHENTICATION_REJECTED,)
    assert incomplete.state is AuthorizationState.DENIED
    assert incomplete.internal_reasons == (Internal.READINESS_AUTHENTICATION_INCOMPLETE,)


def test_a25_accepts_a23_only_through_a24_and_not_a24_dtos_or_references():
    ready = readiness_result()
    authenticated = verify_readiness_authentication(
        ready, envelope=readiness_envelope(ready), policy=readiness_policy(),
        resolved_key=readiness_key(), verification_time=NOW,
    )
    trusted = authenticated.trusted_reference
    assert trusted is not None
    arguments = dict(
        readiness_envelope=readiness_envelope(ready), readiness_policy=readiness_policy(),
        readiness_key=readiness_key(), authorization_policy=authorization_policy_contract(),
        resolved_authorization_key=authorization_key_contract(), signer=AUTHORIZATION_KEY.sign,
    )
    for caller_constructed in (authenticated, trusted):
        outcome = authorize_continued_operation(
            request(), readiness_result=caller_constructed, **arguments,
        )
        assert outcome.state is AuthorizationState.DENIED
        assert outcome.internal_reasons == (Internal.READINESS_AUTHENTICATION_REJECTED,)
    with pytest.raises(ContinuedOperationAuthorizationError, match="exact continued-operation request"):
        authorize_continued_operation(
            authenticated, readiness_result=ready, **arguments,
        )
    assert not hasattr(request(), "trusted_reference")


def test_strict_request_translation_rejects_unknown_subclass_and_malformed_time_inputs():
    document = continued_operation_request_document(request())
    assert translate_untrusted_continued_operation_request(document) == request()
    with pytest.raises(ContinuedOperationAuthorizationError):
        translate_untrusted_continued_operation_request({**document, "unexpected": "field"})

    class RequestDictionary(dict):
        pass

    with pytest.raises(ContinuedOperationAuthorizationError):
        translate_untrusted_continued_operation_request(RequestDictionary(document))
    with pytest.raises(ContinuedOperationAuthorizationError):
        translate_untrusted_continued_operation_request(
            {**document, "evaluation_time": "2026-09-15T12:00:00.1Z"}
        )
    with pytest.raises(ContinuedOperationAuthorizationError):
        replace(request(), evaluation_time=NOW.replace(tzinfo=None))
    with pytest.raises(ContinuedOperationAuthorizationError):
        replace(request(), contract_version="2.0")


def test_request_wire_form_must_be_canonical_and_round_trips():
    document = continued_operation_request_document(request())
    wire = canonical_wire(document)
    assert translate_untrusted_continued_operation_request(wire) == request()
    with pytest.raises(ContinuedOperationAuthorizationError):
        translate_untrusted_continued_operation_request(json.dumps(document).encode())


def test_proposition_digest_is_deterministic_domain_separated_and_mutation_sensitive():
    ready = readiness_result()
    authenticated = verify_readiness_authentication(
        ready, envelope=readiness_envelope(ready), policy=readiness_policy(),
        resolved_key=readiness_key(), verification_time=NOW,
    )
    trusted = authenticated.trusted_reference
    assert trusted is not None
    policy = authorization_policy_contract()
    first = continued_operation_proposition_digest(request(), trusted, policy)
    second = continued_operation_proposition_digest(request(), trusted, policy)
    changed = continued_operation_proposition_digest(
        request(request_id="continued-operation-request-2"), trusted, policy,
    )
    assert first == second and first != changed
    assert bytes.fromhex(first) not in canonical_continued_operation_authorization_payload(
        authorized_artifact()
    )[:80]


@pytest.mark.parametrize("field,value,reason", [
    ("deployment_id", "other-deployment", Internal.DEPLOYMENT_MISMATCH),
    ("consumer_id", "other-consumer", Internal.CONSUMER_NOT_PERMITTED),
    ("purpose", "diagnostics", Internal.PURPOSE_NOT_PERMITTED),
    ("policy_version", "2", Internal.POLICY_MISMATCH),
    ("expected_readiness_contract_version", "2.0", Internal.CONTRACT_VERSION_NOT_PERMITTED),
])
def test_exact_request_policy_and_readiness_bindings_fail_closed(field, value, reason):
    outcome = authorize(request(**{field: value}))
    assert outcome.state is AuthorizationState.DENIED
    assert outcome.internal_reasons == (reason,)


def test_readiness_digest_and_fingerprint_mutation_cannot_authorize():
    ready = readiness_result()
    signed = readiness_envelope(ready)
    for field in ("attestation_digest", "binding_fingerprint"):
        changed = replace(
            signed,
            claims=replace(signed.claims, **{field: "f" * 64}),
        )
        assert authorize(ready=ready, signed=changed).state is AuthorizationState.DENIED


def test_request_identifier_changes_authorization_identity_and_signed_payload():
    first = authorized_artifact()
    second = authorize(request(request_id="continued-operation-request-2")).authorization
    assert second is not None
    assert first.authorization_id != second.authorization_id
    assert first.proposition_digest != second.proposition_digest
    assert first.signature_base64 != second.signature_base64


def test_exact_readiness_and_policy_expiry_boundaries_are_half_open():
    readiness_expiry = readiness_result().binding.expires_at
    value = authorize(request(requested_until=readiness_expiry)).authorization
    assert value is not None
    at_boundary = verify_continued_operation_authorization(
        value, resolved_key=authorization_key_contract(), verification_time=readiness_expiry,
    )
    assert at_boundary.valid and not at_boundary.active
    assert at_boundary.internal_reason is Internal.AUTHORIZATION_EXPIRED
    policy_expiry = NOW + timedelta(minutes=20)
    policy = authorization_policy_contract(policy_expires_at=policy_expiry)
    assert authorize(
        request(requested_until=policy_expiry), authorization_policy=policy,
    ).state is AuthorizationState.AUTHORIZED
    assert authorize(
        request(requested_until=policy_expiry + timedelta(seconds=1)),
        authorization_policy=policy,
    ).state is AuthorizationState.DENIED


def test_duration_above_policy_maximum_is_denied_not_clamped():
    policy = authorization_policy_contract(maximum_duration_seconds=60)
    outcome = authorize(
        request(requested_until=NOW + timedelta(seconds=61)), authorization_policy=policy,
    )
    assert outcome.state is AuthorizationState.DENIED
    assert outcome.internal_reasons == (Internal.REQUESTED_DURATION_EXCEEDED,)


@pytest.mark.parametrize("lifecycle", [Lifecycle.REVOKED, Lifecycle.SUPERSEDED])
def test_revoked_or_superseded_authorization_policy_is_denied(lifecycle):
    outcome = authorize(authorization_policy=authorization_policy_contract(lifecycle))
    assert outcome.state is AuthorizationState.DENIED
    assert outcome.internal_reasons == (Internal.POLICY_NOT_ACTIVE,)


@pytest.mark.parametrize("status", [ReadinessAuthorityStatus.REVOKED,
                                     ReadinessAuthorityStatus.SUPERSEDED])
def test_revoked_or_superseded_readiness_authority_remains_ineligible(status):
    outcome = authorize(readiness_policy=readiness_policy(status))
    assert outcome.state is AuthorizationState.DENIED
    assert outcome.public_reason_codes == (PublicReason.READINESS_NOT_ELIGIBLE,)


@pytest.mark.parametrize("where", ["policy", "resolved_key"])
def test_revoked_authorization_signer_or_key_is_denied(where):
    overrides = (
        {"authorization_policy": authorization_policy_contract(signer_lifecycle=Lifecycle.REVOKED)}
        if where == "policy" else
        {"resolved_authorization_key": authorization_key_contract(Lifecycle.REVOKED)}
    )
    outcome = authorize(**overrides)
    assert outcome.state is AuthorizationState.DENIED
    assert outcome.internal_reasons == (Internal.SIGNING_AUTHORITY_NOT_ACTIVE,)


@pytest.mark.parametrize("missing", ["authorization_policy", "resolved_authorization_key"])
def test_missing_policy_or_resolved_signing_key_requires_review(missing):
    outcome = authorize(**{missing: None})
    assert outcome.state is AuthorizationState.REVIEW_REQUIRED
    assert outcome.public_reason_codes == (PublicReason.AUTHORIZATION_POLICY_UNAVAILABLE,)
    assert outcome.authorization is None


def test_unpermitted_readiness_authority_and_wrong_signing_key_are_denied():
    policy = authorization_policy_contract(
        readiness_authorities=frozenset({("other-issuer", "other-key")})
    )
    assert authorize(authorization_policy=policy).internal_reasons == (
        Internal.READINESS_AUTHORITY_NOT_PERMITTED,
    )
    wrong_key = Ed25519PrivateKey.generate().public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw,
    )
    assert authorize(
        resolved_authorization_key=authorization_key_contract(public_key=wrong_key)
    ).internal_reasons == (Internal.INVALID_AUTHORIZATION_SIGNATURE,)


def test_signed_artifact_tampering_and_context_substitution_fail_safely():
    value = authorized_artifact()
    raw = bytearray(base64.b64decode(value.signature_base64))
    raw[-1] ^= 1
    tampered = replace(value, signature_base64=base64.b64encode(raw).decode("ascii"))
    result = verify_continued_operation_authorization(
        tampered, resolved_key=authorization_key_contract(), verification_time=NOW,
    )
    assert not result.valid
    assert result.internal_reason is Internal.INVALID_AUTHORIZATION_SIGNATURE
    substituted = verify_continued_operation_authorization(
        value, resolved_key=authorization_key_contract(), verification_time=NOW,
        expected_consumer_id="another-gateway",
    )
    assert substituted.valid and substituted.active and not substituted.applicable
    assert substituted.internal_reason is Internal.AUTHORIZATION_NOT_APPLICABLE


def test_artifact_field_mutation_invalidates_proposition_before_signature_check():
    value = authorized_artifact()
    changed = replace(value, consumer_id="another-gateway")
    result = verify_continued_operation_authorization(
        changed, resolved_key=authorization_key_contract(), verification_time=NOW,
    )
    assert not result.valid
    assert result.internal_reason is Internal.AUTHORIZATION_BINDING_INVALID


def test_authorization_is_immutable_and_canonical_serialization_round_trips():
    value = authorized_artifact()
    with pytest.raises(FrozenInstanceError):
        value.consumer_id = "changed"
    document = continued_operation_authorization_document(value)
    wire = canonical_wire(document)
    restored = translate_continued_operation_authorization(wire)
    assert restored == value
    verified = verify_continued_operation_authorization(
        restored, resolved_key=authorization_key_contract(), verification_time=NOW,
    )
    assert verified.valid and verified.active and verified.applicable
    with pytest.raises(ContinuedOperationAuthorizationError):
        translate_continued_operation_authorization({**document, "unknown": "field"})


def test_repeated_evaluation_with_identical_inputs_and_time_is_deterministic():
    first = authorize()
    second = authorize()
    assert first == second


def test_public_projection_is_allowlisted_and_excludes_protected_data():
    outcome = authorize()
    public = serialize_public_contract(public_continued_operation_authorization(outcome))
    assert set(public) == {
        "schema_version", "deployment_id", "purpose", "authorization_state",
        "reason_codes", "decided_at", "expires_at",
    }
    assert public["schema_version"] == CONTINUED_OPERATION_AUTHORIZATION_CONTRACT_VERSION
    wire = str(public)
    for protected in (
        "signature", "fingerprint", "issuer", "key_id", "policy_version",
        "proposition_digest", "production-gateway", "public_key", "trusted_reference",
    ):
        assert protected not in wire
    denied = public_continued_operation_authorization(
        authorize(authorization_policy=None)
    )
    assert denied.expires_at is None


def test_authorization_does_not_mutate_a22_a23_or_a24_inputs_or_execute_operations():
    ready = readiness_result()
    signed = readiness_envelope(ready)
    before_ready, before_signed = ready, signed
    outcome = authorize(ready=ready, signed=signed)
    assert outcome.state is AuthorizationState.AUTHORIZED
    assert ready == before_ready and signed == before_signed
    assert not any(
        name in authorize_continued_operation.__code__.co_names
        for name in ("deploy", "execute", "rollback", "change_traffic", "restart")
    )


def test_private_keys_and_operational_credentials_never_enter_retained_contracts():
    from src.reference_architecture_deployment_continued_operation_authorization_contract import (
        ContinuedOperationAuthorization,
        ContinuedOperationAuthorizationPolicy,
        ResolvedAuthorizationVerificationKey,
    )

    retained = " ".join(
        tuple(ContinuedOperationAuthorization.__dataclass_fields__) +
        tuple(ContinuedOperationAuthorizationPolicy.__dataclass_fields__) +
        tuple(ResolvedAuthorizationVerificationKey.__dataclass_fields__)
    )
    assert "private_key" not in retained
    assert "credential" not in retained
