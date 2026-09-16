from dataclasses import FrozenInstanceError, replace
from datetime import timedelta

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from src.public_contract import serialize_public_contract
from src.reference_architecture_deployment_integrity_contract import TrustStatus
from src.reference_architecture_deployment_readiness_authentication import (
    canonical_readiness_authentication_payload, create_signed_readiness_envelope,
    public_readiness_authentication_outcome, readiness_binding_fingerprint,
    verify_readiness_authentication,
)
from src.reference_architecture_deployment_readiness_authentication_contract import (
    AuthorizedReadinessIssuerKey, ReadinessAuthenticationError,
    ReadinessAuthenticationInternalReason as Internal,
    ReadinessAuthenticationPolicy, ReadinessAuthenticationReasonCode as PublicReason,
    ReadinessAuthenticationState as Authentication, ReadinessAuthorityStatus,
    ResolvedReadinessVerificationKey, SignedReadinessEnvelope,
)
from src.reference_architecture_deployment_readiness_contract import (
    DeploymentReadinessAttestation, DeploymentReadinessStatus as Readiness,
)
from src.reference_architecture_deployment_readiness_revalidation import (
    ReadinessEvidence, ReadinessRevalidationResult, attest_bound_deployment_readiness,
    revalidate_deployment_readiness,
)
from tests.test_reference_architecture_deployment_readiness import trusted_integrity
from tests.test_reference_architecture_deployment_recovery import NOW


VALIDITY = timedelta(hours=1)
PRIVATE_KEY = Ed25519PrivateKey.from_private_bytes(bytes(range(1, 33)))
PUBLIC_KEY = PRIVATE_KEY.public_key().public_bytes(
    encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw,
)


def result(status=TrustStatus.TRUSTED, revision="revision-1"):
    evidence = ReadinessEvidence(
        "deployment", revision, replace(trusted_integrity(), status=status), None,
    )
    old = attest_bound_deployment_readiness(
        evidence=evidence, evaluation_time=NOW, validity=VALIDITY,
    )
    return revalidate_deployment_readiness(
        previous=old.attestation, binding=old, evidence=evidence,
        evaluation_time=NOW, validity=VALIDITY,
    )


def envelope(value=None, **overrides):
    arguments = dict(issuer_id="readiness-issuer", key_id="readiness-key-1",
                     policy_id="readiness-policy", policy_version="1", signer=PRIVATE_KEY.sign)
    arguments.update(overrides)
    return create_signed_readiness_envelope(value or result(), **arguments)


def policy(status=ReadinessAuthorityStatus.ACTIVE, *, deployments=frozenset({"deployment"}),
           active_from=NOW - VALIDITY, expires_at=NOW + VALIDITY):
    grant = AuthorizedReadinessIssuerKey(
        "readiness-issuer", "readiness-key-1", "ed25519", active_from,
        expires_at, status, deployments,
    )
    return ReadinessAuthenticationPolicy("readiness-policy", "1", (grant,))


def key(status=ReadinessAuthorityStatus.ACTIVE, *, public_key=PUBLIC_KEY,
        active_from=NOW - VALIDITY, expires_at=NOW + VALIDITY):
    return ResolvedReadinessVerificationKey(
        "readiness-issuer", "readiness-key-1", "ed25519", public_key,
        active_from, expires_at, status,
    )


def verify(value=None, signed=None, **overrides):
    value = value or result()
    arguments = dict(envelope=signed or envelope(value), policy=policy(),
                     resolved_key=key(), verification_time=NOW)
    arguments.update(overrides)
    return verify_readiness_authentication(value, **arguments)


def test_verified_ready_is_the_only_combination_that_mints_trusted_reference():
    outcome = verify()
    assert outcome.authentication_state is Authentication.VERIFIED
    assert outcome.readiness_status is Readiness.READY
    assert outcome.eligible_for_reliance
    assert outcome.trusted_reference is not None
    assert outcome.trusted_reference.binding_fingerprint == readiness_binding_fingerprint(result())


@pytest.mark.parametrize("status,expected", [
    (TrustStatus.UNTRUSTED, Readiness.BLOCKED),
    (TrustStatus.INDETERMINATE, Readiness.REVIEW_REQUIRED),
])
def test_valid_signature_authenticates_nonready_but_never_makes_it_eligible(status, expected):
    value = result(status)
    outcome = verify(value)
    assert outcome.authentication_state is Authentication.VERIFIED
    assert outcome.readiness_status is expected
    assert not outcome.eligible_for_reliance and outcome.trusted_reference is None


def test_only_exact_a23_result_enters_the_workflow():
    with pytest.raises(ReadinessAuthenticationError, match="exact ATL-A.23"):
        create_signed_readiness_envelope(result().attestation, issuer_id="issuer", key_id="key",
                                         policy_id="policy", policy_version="1", signer=PRIVATE_KEY.sign)
    with pytest.raises(ReadinessAuthenticationError, match="binding is invalid"):
        create_signed_readiness_envelope(
            replace(result(), binding=replace(result().binding, attestation=result(TrustStatus.UNTRUSTED).attestation)),
            issuer_id="issuer", key_id="key", policy_id="policy", policy_version="1",
            signer=PRIVATE_KEY.sign,
        )


def test_binding_fingerprint_and_payload_are_deterministic_and_domain_separated():
    first = result()
    second = result()
    assert readiness_binding_fingerprint(first) == readiness_binding_fingerprint(second)
    signed = envelope(first)
    assert canonical_readiness_authentication_payload(signed.claims) == canonical_readiness_authentication_payload(signed.claims)
    assert readiness_binding_fingerprint(first).encode() not in canonical_readiness_authentication_payload(signed.claims)[:40]


@pytest.mark.parametrize("mutation", [
    lambda value: replace(value, binding=replace(value.binding, evidence=replace(value.binding.evidence, revision="revision-2"))),
    lambda value: replace(value, binding=replace(value.binding, evidence=replace(
        value.binding.evidence, integrity=replace(value.binding.evidence.integrity, result_digest="d" * 64)))),
    lambda value: replace(value, binding=replace(value.binding, expires_at=value.binding.expires_at + VALIDITY)),
])
def test_any_evidence_revision_or_expiry_substitution_invalidates_signed_binding(mutation):
    original = result()
    outcome = verify(mutation(original), signed=envelope(original))
    assert outcome.authentication_state is Authentication.REJECTED
    assert outcome.public_reason_codes == (PublicReason.BINDING_INVALID,)
    assert outcome.internal_reasons == (Internal.CLAIMS_MISMATCH,)


@pytest.mark.parametrize("field,replacement", [
    ("deployment_id", "other"),
    ("readiness_status", Readiness.BLOCKED),
    ("readiness_reason_codes", ("integrity_not_verified",)),
    ("issuer_id", "other-issuer"),
    ("key_id", "other-key"),
    ("policy_id", "other-policy"),
    ("issued_at", NOW + timedelta(seconds=1)),
])
def test_security_relevant_claim_substitution_cannot_reuse_signature(field, replacement):
    value = result()
    original = envelope(value)
    changed = replace(original, claims=replace(original.claims, **{field: replacement}))
    outcome = verify(value, signed=changed)
    assert outcome.authentication_state is Authentication.REJECTED


def test_changed_signature_and_wrong_key_are_rejected_without_public_diagnostics():
    value = result()
    original = envelope(value)
    raw = bytearray(__import__("base64").b64decode(original.signature_base64))
    raw[0] ^= 1
    changed = replace(original, signature_base64=__import__("base64").b64encode(raw).decode())
    outcome = verify(value, signed=changed)
    assert outcome.public_reason_codes == (PublicReason.AUTHENTICITY_NOT_VERIFIED,)
    other = Ed25519PrivateKey.generate().public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw,
    )
    assert verify(value, resolved_key=key(public_key=other)).authentication_state is Authentication.REJECTED


@pytest.mark.parametrize("missing,internal", [("policy", Internal.POLICY_UNAVAILABLE),
                                                ("resolved_key", Internal.KEY_UNAVAILABLE)])
def test_missing_verification_material_requires_review(missing, internal):
    outcome = verify(**{missing: None})
    assert outcome.authentication_state is Authentication.REVIEW_REQUIRED
    assert outcome.public_reason_codes == (PublicReason.VERIFICATION_MATERIAL_UNAVAILABLE,)
    assert outcome.internal_reasons == (internal,)
    assert not outcome.eligible_for_reliance


def test_malformed_policy_and_key_contracts_are_normalized_as_untrusted():
    assert verify(policy={}).internal_reasons == (Internal.POLICY_MISMATCH,)
    assert verify(resolved_key=b"raw-key").internal_reasons == (Internal.KEY_INVALID,)


@pytest.mark.parametrize("status", [ReadinessAuthorityStatus.REVOKED,
                                     ReadinessAuthorityStatus.SUPERSEDED])
def test_revoked_or_superseded_authority_is_rejected(status):
    outcome = verify(policy=policy(status))
    assert outcome.authentication_state is Authentication.REJECTED
    assert outcome.public_reason_codes == (PublicReason.AUTHORITY_NOT_TRUSTED,)


def test_unauthorized_issuer_and_valid_signature_still_fail_closed():
    unauthorized = ReadinessAuthenticationPolicy(
        "readiness-policy", "1",
        (AuthorizedReadinessIssuerKey("other", "other", "ed25519", NOW - VALIDITY,
                                      NOW + VALIDITY, ReadinessAuthorityStatus.ACTIVE,
                                      frozenset({"deployment"})),),
    )
    outcome = verify(policy=unauthorized)
    assert outcome.authentication_state is Authentication.REJECTED
    assert outcome.internal_reasons == (Internal.ISSUER_NOT_AUTHORIZED,)


@pytest.mark.parametrize("now", [NOW + VALIDITY, NOW + VALIDITY + timedelta(seconds=1)])
def test_binding_expiry_is_half_open_and_fails_closed(now):
    outcome = verify(verification_time=now)
    assert outcome.authentication_state is Authentication.REJECTED
    assert outcome.public_reason_codes == (PublicReason.RECORD_EXPIRED,)


def test_key_lifecycle_is_independent_from_policy_authorization():
    outcome = verify(resolved_key=key(status=ReadinessAuthorityStatus.REVOKED))
    assert outcome.authentication_state is Authentication.REJECTED
    assert outcome.internal_reasons == (Internal.KEY_NOT_ACTIVE,)


def test_public_projection_is_strictly_allowlisted_and_serializable():
    internal = verify()
    public = serialize_public_contract(public_readiness_authentication_outcome(internal))
    assert set(public) == {"schema_version", "deployment_id", "readiness_status",
                           "authentication_state", "reason_codes", "verified_at"}
    wire = str(public)
    for protected in ("signature", "key_id", "issuer_id", "binding_fingerprint",
                      "revision-1", "public_key", "invalid_signature"):
        assert protected not in wire


def test_contracts_and_inputs_are_immutable_and_verification_is_idempotent():
    value = result()
    signed = envelope(value)
    first = verify(value, signed)
    second = verify(value, signed)
    assert first == second
    with pytest.raises(FrozenInstanceError):
        signed.signature_base64 = "changed"


def test_existing_a22_digest_and_a23_result_are_unchanged_by_authentication():
    value = result()
    before = value
    original_digest = value.attestation.attestation_digest
    verify(value)
    assert value == before
    assert value.attestation.attestation_digest == original_digest


def test_malformed_signature_and_private_key_never_enter_contracts():
    with pytest.raises(ReadinessAuthenticationError, match="signature is invalid"):
        SignedReadinessEnvelope(envelope().claims, "not-base64")
    assert "private" not in " ".join(SignedReadinessEnvelope.__dataclass_fields__)
    assert "private" not in " ".join(ResolvedReadinessVerificationKey.__dataclass_fields__)
