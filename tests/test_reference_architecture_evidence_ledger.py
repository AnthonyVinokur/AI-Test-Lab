from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone

import pytest

from src.reference_architecture_authenticated_provenance_outcome import (
    ReferenceArchitectureAuthenticatedProvenanceOutcomeV1, ReferenceArchitectureAuthenticatedProvenanceSuccessV1,
)
from src.reference_architecture_conformance_evidence_binding_outcome import (
    ReferenceArchitectureConformanceEvidenceBindingOutcomeV1, ReferenceArchitectureConformanceEvidenceBindingSuccessV1,
)
from src.reference_architecture_conformance_evidence_intake_contract import supported_reference_architecture_conformance_evidence_intake_contract
from src.reference_architecture_evidence_admission_contract import (
    ReferenceArchitectureAdmissionDecision, ReferenceArchitectureAdmissionReasonCode,
    ReferenceArchitectureEvidenceAdmissionPolicyV1, ReferenceArchitectureEvidenceAdmissionRequestV1,
    ReferenceArchitectureInternalAdmissionResultV1, ReferenceArchitectureReplayStatus,
)
from src.reference_architecture_evidence_ledger import InMemoryEvidenceLedger, verify_evidence_ledger_chain
from src.reference_architecture_evidence_ledger_admission import AdmittedEvidenceAuthorization, mint_admitted_evidence_authorization
from src.reference_architecture_evidence_ledger_contract import EvidenceLedgerAppendRequest, LedgerEntryStatus, LedgerFailureReason
from src.reference_architecture_evidence_ledger_identity import calculate_evidence_ledger_entry_id
from src.reference_architecture_evidence_ledger_orchestration import append_admitted_evidence_to_ledger
from src.reference_architecture_evidence_ledger_outcome import decode_evidence_ledger_outcome, encode_evidence_ledger_outcome
from src.reference_architecture_evidence_ledger_translation import EvidenceLedgerTranslationError, translate_untrusted_evidence_ledger_append_request
from src.reference_architecture_trusted_evidence_outcome import ReferenceArchitectureTrustedEvidenceOutcomeV1

NOW = datetime(2026, 9, 14, 12, tzinfo=timezone.utc)

def admission_request(digest: str = "a" * 64, run: str = "run-1") -> ReferenceArchitectureEvidenceAdmissionRequestV1:
    evidence = supported_reference_architecture_conformance_evidence_intake_contract(
        evaluation={"passed": True}, evaluation_sha256="b" * 64, evidence_sha256=digest)
    integrity = ReferenceArchitectureConformanceEvidenceBindingOutcomeV1(succeeded=True,
        binding=ReferenceArchitectureConformanceEvidenceBindingSuccessV1(integration_id="adapter-1", correlation_id=run, evidence=evidence))
    authentication = ReferenceArchitectureAuthenticatedProvenanceOutcomeV1(succeeded=True,
        authentication=ReferenceArchitectureAuthenticatedProvenanceSuccessV1(attestation_id="attestation-1",
            producer_id="producer-1", evidence_sha256=digest, issued_at="2026-09-14T11:00:00Z", key_id="key-1", algorithm="ed25519"))
    trust = ReferenceArchitectureTrustedEvidenceOutcomeV1(status="trusted", trusted=True, reason_code=None,
        signer_id="producer-1", key_id="key-1", policy_id="trust-1", policy_version="1.0", evaluated_at="2026-09-14T12:00:00Z")
    policy = ReferenceArchitectureEvidenceAdmissionPolicyV1("policy-1", "2026.09", frozenset({"evaluation-report"}),
        frozenset({"producer-1"}), frozenset({("producer-1", "evaluation-report")}), frozenset({"1.0"}),
        frozenset({"release"}), frozenset({"production"}), frozenset({"release-gate"}), timedelta(hours=2))
    return ReferenceArchitectureEvidenceAdmissionRequestV1("attestation-1", digest, "evaluation-report", "producer-1",
        "1.0", "1.0", "release", "production", "release-gate", run,
        NOW - timedelta(hours=1), NOW - timedelta(hours=2), NOW + timedelta(hours=1), NOW,
        ReferenceArchitectureReplayStatus.NOT_REPLAYED, integrity, authentication, trust, policy)

def authorization(digest: str = "a" * 64, run: str = "run-1") -> AdmittedEvidenceAuthorization:
    result = ReferenceArchitectureInternalAdmissionResultV1(ReferenceArchitectureAdmissionDecision.ADMITTED,
        ReferenceArchitectureAdmissionReasonCode.EVIDENCE_ADMITTED)
    return mint_admitted_evidence_authorization(admission_request(digest, run), result, provenance_reference=f"provenance-{run}")

def document(auth: AdmittedEvidenceAuthorization, supersedes: str | None = None) -> dict:
    return {"contract_name": "ai-test-lab.reference-architecture-evidence-ledger", "contract_version": "1.0",
        "evidence_sha256": auth.evidence_sha256, "evidence_type": auth.evidence_type,
        "producer_id": auth.producer_id, "evaluation_run_id": auth.evaluation_run_id,
        "admission_decision_id": auth.decision_id, "provenance_reference": auth.provenance_reference,
        "evidence_contract_version": auth.evidence_contract_version,
        "admission_contract_version": auth.admission_contract_version,
        "policy_version": auth.policy_version, "supersedes_entry_id": supersedes}

def append(ledger: InMemoryEvidenceLedger, auth: AdmittedEvidenceAuthorization, supersedes: str | None = None):
    return append_admitted_evidence_to_ledger(document(auth, supersedes), authorization=auth, ledger=ledger, clock=lambda: NOW)

def test_contract_is_immutable_and_internal_fields_are_not_caller_controlled() -> None:
    auth = authorization()
    request = translate_untrusted_evidence_ledger_append_request(document(auth), authorization=auth, recorded_at=NOW)
    with pytest.raises(FrozenInstanceError): request.policy_version = "changed"  # type: ignore[misc]
    altered = document(auth); altered["sequence"] = 99
    with pytest.raises(EvidenceLedgerTranslationError):
        translate_untrusted_evidence_ledger_append_request(altered, authorization=auth, recorded_at=NOW)

@pytest.mark.parametrize("field", ["evidence_sha256", "evaluation_run_id", "producer_id", "provenance_reference", "admission_decision_id"])
def test_exact_admission_binding_rejects_substitution(field: str) -> None:
    auth = authorization(); payload = document(auth); payload[field] = "c" * 64 if field == "evidence_sha256" else "substitute"
    outcome = append_admitted_evidence_to_ledger(payload, authorization=auth, ledger=InMemoryEvidenceLedger(), clock=lambda: NOW)
    assert (outcome.status, outcome.reason_code) == (LedgerEntryStatus.REJECTED, LedgerFailureReason.EVIDENCE_BINDING_MISMATCH)

def test_only_successful_internal_admission_can_mint_authorization() -> None:
    rejected = ReferenceArchitectureInternalAdmissionResultV1(ReferenceArchitectureAdmissionDecision.REJECTED,
        ReferenceArchitectureAdmissionReasonCode.EVIDENCE_EXPIRED)
    with pytest.raises(ValueError): mint_admitted_evidence_authorization(admission_request(), rejected, provenance_reference="p")
    with pytest.raises(TypeError): AdmittedEvidenceAuthorization(_mint=object())

def test_expired_admission_fails_closed() -> None:
    auth = authorization()
    outcome = append_admitted_evidence_to_ledger(document(auth), authorization=auth, ledger=InMemoryEvidenceLedger(),
        clock=lambda: NOW + timedelta(hours=2))
    assert outcome.reason_code is LedgerFailureReason.ADMISSION_EXPIRED

def test_recording_identity_is_deterministic_and_ignores_recorded_time() -> None:
    auth = authorization(); payload = document(auth)
    first = translate_untrusted_evidence_ledger_append_request(payload, authorization=auth, recorded_at=NOW)
    second = replace(first, recorded_at=NOW + timedelta(minutes=1))
    assert calculate_evidence_ledger_entry_id(first) == calculate_evidence_ledger_entry_id(second)

def test_retry_is_idempotent_and_admission_reuse_conflicts() -> None:
    ledger = InMemoryEvidenceLedger(); auth = authorization()
    first = append(ledger, auth); retry = append(ledger, auth)
    assert first.status is LedgerEntryStatus.RECORDED
    assert (retry.status, retry.reason_code, retry.ledger_entry_id) == (LedgerEntryStatus.ALREADY_RECORDED, LedgerFailureReason.IDEMPOTENT_REPLAY, first.ledger_entry_id)
    request = translate_untrusted_evidence_ledger_append_request(document(auth), authorization=auth, recorded_at=NOW)
    conflict = ledger.append(replace(request, evaluation_run_id="run-other"))
    assert conflict.reason is LedgerFailureReason.ADMISSION_ALREADY_RECORDED

def test_duplicate_evidence_with_a_new_admission_is_rejected() -> None:
    ledger = InMemoryEvidenceLedger(); first = authorization(); assert append(ledger, first).status is LedgerEntryStatus.RECORDED
    second = authorization(run="run-2")
    assert append(ledger, second).reason_code is LedgerFailureReason.DUPLICATE_ENTRY

def test_supersession_builds_append_only_verified_chain_and_rejects_branch() -> None:
    ledger = InMemoryEvidenceLedger(); first = append(ledger, authorization())
    second = append(ledger, authorization("c" * 64, "run-2"), first.ledger_entry_id)
    assert (first.sequence_number, second.sequence_number, second.verification_state) == (1, 2, "verified")
    chain = ledger.chain(second.evidence_chain_id)
    assert chain[1].previous_entry_digest == chain[0].entry_digest
    branch = append(ledger, authorization("d" * 64, "run-3"), first.ledger_entry_id)
    assert (branch.status, branch.reason_code) == (LedgerEntryStatus.CONFLICT, LedgerFailureReason.CHAIN_HEAD_MISMATCH)

def test_verifier_detects_content_tampering_missing_entries_and_wrong_order() -> None:
    ledger = InMemoryEvidenceLedger(); first = append(ledger, authorization())
    second = append(ledger, authorization("c" * 64, "run-2"), first.ledger_entry_id)
    chain = ledger.chain(second.evidence_chain_id)
    assert verify_evidence_ledger_chain(chain).verified
    assert verify_evidence_ledger_chain((replace(chain[0], producer_id="attacker"), chain[1])).reason is LedgerFailureReason.EVIDENCE_BINDING_MISMATCH
    assert verify_evidence_ledger_chain((chain[1],)).reason is LedgerFailureReason.SEQUENCE_CONFLICT
    assert verify_evidence_ledger_chain(tuple(reversed(chain))).reason is LedgerFailureReason.SEQUENCE_CONFLICT

def test_public_projection_is_deterministic_round_trippable_and_redacted() -> None:
    outcome = append(InMemoryEvidenceLedger(), authorization())
    encoded = encode_evidence_ledger_outcome(outcome)
    assert encode_evidence_ledger_outcome(outcome) == encoded
    assert decode_evidence_ledger_outcome(encoded) == outcome
    for protected in (b"key_id", b"signature", b"policy_id", b"storage", b"traceback", b"internal"):
        assert protected not in encoded

def test_malformed_and_unknown_fields_have_stable_public_failure() -> None:
    auth = authorization(); payload = document(auth); payload["private_status"] = "recorded"
    result = append_admitted_evidence_to_ledger(payload, authorization=auth, ledger=InMemoryEvidenceLedger(), clock=lambda: NOW)
    assert (result.status, result.reason_code) == (LedgerEntryStatus.REJECTED, LedgerFailureReason.INVALID_APPEND_REQUEST)
