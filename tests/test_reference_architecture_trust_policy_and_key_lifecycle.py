from __future__ import annotations

import base64
from copy import deepcopy
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from src.reference_architecture_authenticated_provenance_outcome import (
    ReferenceArchitectureAuthenticatedProvenanceOutcomeV1,
    ReferenceArchitectureAuthenticatedProvenanceSuccessV1,
)
from src.reference_architecture_trust_orchestration import evaluate_public_reference_architecture_trust
from src.reference_architecture_trust_policy_translation import (
    ReferenceArchitectureTrustPolicyTranslationError,
    translate_untrusted_reference_architecture_trust_policy,
)
from src.reference_architecture_trusted_evidence_outcome import ReferenceArchitectureTrustedEvidenceOutcomeV1
from src.reference_architecture_trusted_evidence_serialization import (
    decode_reference_architecture_trusted_evidence_outcome,
    encode_reference_architecture_trusted_evidence_outcome,
)


NOW = datetime(2026, 9, 14, 12, 0, tzinfo=timezone.utc)


def authenticated(*, signer: str = "producer-1", key_id: str = "key-1") -> ReferenceArchitectureAuthenticatedProvenanceOutcomeV1:
    return ReferenceArchitectureAuthenticatedProvenanceOutcomeV1(
        succeeded=True,
        authentication=ReferenceArchitectureAuthenticatedProvenanceSuccessV1(
            attestation_id="attestation-1", producer_id=signer, evidence_sha256="a" * 64,
            issued_at="2026-09-14T11:00:00Z", key_id=key_id, algorithm="ed25519",
        ),
    )


def policy(*, status: str = "active", activated: str = "2026-01-01T00:00:00Z", expires: str | None = "2027-01-01T00:00:00Z", purposes: list[str] | None = None, environments: list[str] | None = None, algorithms: list[str] | None = None, key_types: list[str] | None = None) -> dict:
    return {
        "contract_name": "ai-test-lab.reference-architecture-trust-policy", "contract_version": "1.0",
        "policy_id": "policy-1", "policy_version": "2026.09",
        "permitted_algorithms": algorithms or ["ed25519"], "permitted_key_types": key_types or ["ed25519-public"],
        "trusted_signers": [{"signer_id": "producer-1", "keys": [{
            "key_id": "key-1", "public_key_base64": base64.b64encode(bytes(range(32))).decode(),
            "algorithm": "ed25519", "key_type": "ed25519-public", "activated_at": activated,
            "expires_at": expires, "status": status, "permitted_purposes": purposes or ["evidence-publication"],
            "permitted_environments": environments or ["production"],
        }]}],
    }


def evaluate(document: dict, outcome: ReferenceArchitectureAuthenticatedProvenanceOutcomeV1 | None = None):
    return evaluate_public_reference_architecture_trust(outcome or authenticated(), document, purpose="evidence-publication", environment="production", evaluated_at=NOW)


def test_authorized_active_key_is_trusted_and_identifies_policy() -> None:
    result = evaluate(policy())
    assert result.trusted and result.status == "trusted" and result.reason_code is None
    assert (result.signer_id, result.key_id, result.policy_id, result.policy_version) == ("producer-1", "key-1", "policy-1", "2026.09")


@pytest.mark.parametrize(("outcome", "code"), [
    (authenticated(signer="unknown"), "unknown_signer"),
    (authenticated(key_id="unknown"), "unknown_key"),
])
def test_unknown_identity_or_key_fails_closed(outcome, code: str) -> None:
    assert evaluate(policy(), outcome).reason_code.value == code


def test_signer_key_mismatch_is_distinct() -> None:
    document = policy()
    document["trusted_signers"].append({"signer_id": "producer-2", "keys": [dict(document["trusted_signers"][0]["keys"][0], key_id="other-key")]})
    assert evaluate(document, authenticated(signer="producer-2", key_id="key-1")).reason_code.value == "signer_key_mismatch"


@pytest.mark.parametrize(("changes", "code"), [
    ({"status": "revoked"}, "key_revoked"),
    ({"status": "disabled"}, "key_disabled"),
    ({"activated": "2026-09-15T00:00:00Z"}, "key_not_yet_active"),
    ({"expires": "2026-09-14T12:00:00Z"}, "key_expired"),
    ({"purposes": ["reporting"]}, "purpose_not_authorized"),
    ({"environments": ["development"]}, "environment_not_authorized"),
    ({"algorithms": ["rsa-pss"]}, "algorithm_not_permitted"),
    ({"key_types": ["rsa-public"]}, "key_type_not_permitted"),
])
def test_policy_rejections_are_normalized(changes: dict, code: str) -> None:
    assert evaluate(policy(**changes)).reason_code.value == code


def test_activation_boundary_is_inclusive_and_expiration_boundary_is_exclusive() -> None:
    active = policy(activated="2026-09-14T12:00:00Z", expires="2026-09-14T12:00:01Z")
    assert evaluate(active).trusted
    assert evaluate(policy(expires="2026-09-14T12:00:00Z")).reason_code.value == "key_expired"


@pytest.mark.parametrize("mutation", [
    lambda value: value.update({"unknown": True}),
    lambda value: value["trusted_signers"].append(deepcopy(value["trusted_signers"][0])),
    lambda value: value["trusted_signers"][0]["keys"].append(deepcopy(value["trusted_signers"][0]["keys"][0])),
    lambda value: value.update({"policy_version": ""}),
])
def test_malformed_or_ambiguous_policy_fails_closed(mutation) -> None:
    document = policy(); mutation(document)
    assert evaluate(document).reason_code.value == "invalid_trust_policy"


def test_translation_copies_input_and_is_immutable() -> None:
    document = policy(); translated = translate_untrusted_reference_architecture_trust_policy(document)
    document["trusted_signers"][0]["keys"][0]["permitted_purposes"].append("changed")
    assert translated.trusted_signers[0].keys[0].permitted_purposes == frozenset({"evidence-publication"})
    with pytest.raises(Exception):
        translated.policy_id = "changed"


def test_missing_explicit_evaluation_time_fails_closed() -> None:
    result = evaluate_public_reference_architecture_trust(authenticated(), policy(), purpose="evidence-publication", environment="production", evaluated_at=None)  # type: ignore[arg-type]
    assert result.reason_code.value == "trust_evaluation_failed"


def test_equivalent_inputs_are_deterministic_and_round_trip_stably() -> None:
    first = evaluate(deepcopy(policy())); second = evaluate(deepcopy(policy()))
    assert first == second
    encoded = encode_reference_architecture_trusted_evidence_outcome(first)
    assert encoded == encode_reference_architecture_trusted_evidence_outcome(second)
    assert decode_reference_architecture_trusted_evidence_outcome(encoded) == first


def test_public_dto_is_frozen_strict_and_redacted() -> None:
    result = evaluate(policy(status="revoked"))
    with pytest.raises(ValidationError):
        ReferenceArchitectureTrustedEvidenceOutcomeV1.model_validate({**result.model_dump(), "traceback": "secret"})
    wire = encode_reference_architecture_trusted_evidence_outcome(result)
    for forbidden in (b"public_key", b"private", b"credential", b"traceback", b"signature"):
        assert forbidden not in wire
    with pytest.raises(ValidationError):
        result.status = "trusted"


def test_translation_error_does_not_leak_diagnostics() -> None:
    with pytest.raises(ReferenceArchitectureTrustPolicyTranslationError):
        translate_untrusted_reference_architecture_trust_policy({"secret": "do-not-leak"})
    result = evaluate({"secret": "do-not-leak"})
    assert "do-not-leak" not in encode_reference_architecture_trusted_evidence_outcome(result).decode()
