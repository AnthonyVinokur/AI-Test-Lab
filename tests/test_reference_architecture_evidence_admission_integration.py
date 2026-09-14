from copy import deepcopy
from datetime import datetime, timezone

import pytest

from src.reference_architecture_authenticated_provenance_failure_normalization import (
    ReferenceArchitectureAuthenticatedProvenanceFailureCode,
    ReferenceArchitectureAuthenticatedProvenanceFailureStage,
    ReferenceArchitectureAuthenticatedProvenanceFailureV1,
)
from src.reference_architecture_authenticated_provenance_outcome import (
    ReferenceArchitectureAuthenticatedProvenanceOutcomeV1,
    ReferenceArchitectureAuthenticatedProvenanceSuccessV1,
)
from src.reference_architecture_conformance_evidence_binding_failure_normalization import (
    ReferenceArchitectureConformanceEvidenceBindingFailureCode,
    ReferenceArchitectureConformanceEvidenceBindingFailureStage,
    ReferenceArchitectureConformanceEvidenceBindingFailureV1,
)
from src.reference_architecture_conformance_evidence_binding_outcome import (
    ReferenceArchitectureConformanceEvidenceBindingOutcomeV1,
    ReferenceArchitectureConformanceEvidenceBindingSuccessV1,
)
from src.reference_architecture_conformance_evidence_intake_contract import (
    supported_reference_architecture_conformance_evidence_intake_contract,
)
from src.reference_architecture_evidence_admission_orchestration import (
    admit_public_reference_architecture_evidence,
)
from src.reference_architecture_evidence_admission_outcome import (
    encode_reference_architecture_evidence_admission_outcome,
)
from src.reference_architecture_trust_failure_normalization import (
    ReferenceArchitectureTrustFailureCode,
)
from src.reference_architecture_trusted_evidence_outcome import (
    ReferenceArchitectureTrustedEvidenceOutcomeV1,
)


DIGEST = "a" * 64
NOW = datetime(2026, 9, 14, 12, 0, tzinfo=timezone.utc)


def request_document() -> dict:
    return {
        "contract_name": "ai-test-lab.reference-architecture-evidence-admission",
        "contract_version": "1.0", "evidence_contract_version": "1.0",
        "evidence_id": "attestation-1", "evidence_sha256": DIGEST,
        "evidence_type": "evaluation-report", "producer_id": "producer-1",
        "purpose": "release", "target_environment": "production",
        "workflow_id": "release-gate", "run_id": "run-1",
        "created_at": "2026-09-14T11:00:00Z", "not_before": "2026-09-14T10:00:00Z",
        "expires_at": "2026-09-14T13:00:00Z", "evaluated_at": "2026-09-14T12:00:00Z",
        "replay_status": "not_replayed",
    }


def policy_document() -> dict:
    return {
        "policy_id": "policy-1", "policy_version": "2026.09",
        "supported_evidence_types": ["evaluation-report"],
        "authorized_producers": ["producer-1"],
        "allowed_producer_evidence_types": [["producer-1", "evaluation-report"]],
        "acceptable_contract_versions": ["1.0"], "allowed_purposes": ["release"],
        "allowed_environments": ["production"], "permitted_workflows": ["release-gate"],
        "maximum_evidence_age_seconds": 7200,
    }


def integrity(*, succeeded: bool = True) -> ReferenceArchitectureConformanceEvidenceBindingOutcomeV1:
    if not succeeded:
        return ReferenceArchitectureConformanceEvidenceBindingOutcomeV1(
            succeeded=False,
            failure=ReferenceArchitectureConformanceEvidenceBindingFailureV1(
                stage=ReferenceArchitectureConformanceEvidenceBindingFailureStage.INTEGRITY,
                code=ReferenceArchitectureConformanceEvidenceBindingFailureCode.EVIDENCE_INTEGRITY_FAILED,
                message="safe",
            ),
        )
    evidence = supported_reference_architecture_conformance_evidence_intake_contract(
        evaluation={"passed": True}, evaluation_sha256="b" * 64, evidence_sha256=DIGEST
    )
    return ReferenceArchitectureConformanceEvidenceBindingOutcomeV1(
        succeeded=True,
        binding=ReferenceArchitectureConformanceEvidenceBindingSuccessV1(
            integration_id="adapter-1", correlation_id="run-1", evidence=evidence
        ),
    )


def authentication(*, succeeded: bool = True) -> ReferenceArchitectureAuthenticatedProvenanceOutcomeV1:
    if not succeeded:
        return ReferenceArchitectureAuthenticatedProvenanceOutcomeV1(
            succeeded=False,
            failure=ReferenceArchitectureAuthenticatedProvenanceFailureV1(
                stage=ReferenceArchitectureAuthenticatedProvenanceFailureStage.AUTHENTICATION,
                code=ReferenceArchitectureAuthenticatedProvenanceFailureCode.AUTHENTICATION_FAILED,
                message="safe",
            ),
        )
    return ReferenceArchitectureAuthenticatedProvenanceOutcomeV1(
        succeeded=True,
        authentication=ReferenceArchitectureAuthenticatedProvenanceSuccessV1(
            attestation_id="attestation-1", producer_id="producer-1", evidence_sha256=DIGEST,
            issued_at="2026-09-14T11:00:00Z", key_id="key-1", algorithm="ed25519",
        ),
    )


def trust(*, trusted: bool = True) -> ReferenceArchitectureTrustedEvidenceOutcomeV1:
    return ReferenceArchitectureTrustedEvidenceOutcomeV1(
        status="trusted" if trusted else "rejected", trusted=trusted,
        reason_code=None if trusted else ReferenceArchitectureTrustFailureCode.KEY_REVOKED,
        signer_id="producer-1", key_id="key-1", policy_id="trust-1",
        policy_version="1.0", evaluated_at="2026-09-14T12:00:00Z",
    )


def admit(request: dict | None = None, policy: dict | None = None, **prerequisites):
    return admit_public_reference_architecture_evidence(
        request or request_document(), policy or policy_document(),
        integrity_result=prerequisites.get("integrity_result", integrity()),
        authenticated_provenance_result=prerequisites.get("authenticated_provenance_result", authentication()),
        trust_result=prerequisites.get("trust_result", trust()),
    )


def test_complete_flow_admits_exactly_bound_authorized_fresh_evidence() -> None:
    result = admit()
    assert (result.decision.value, result.reason_code.value) == ("admitted", "evidence_admitted")


@pytest.mark.parametrize(("changes", "code"), [
    ({"evidence_sha256": "c" * 64}, "evidence_binding_mismatch"),
    ({"purpose": "compliance"}, "purpose_not_allowed"),
    ({"target_environment": "development"}, "environment_not_allowed"),
    ({"producer_id": "other"}, "evidence_binding_mismatch"),
    ({"evidence_type": "trace"}, "evidence_type_not_supported"),
    ({"expires_at": "2026-09-14T12:00:00Z"}, "evidence_expired"),
    ({"not_before": "2026-09-14T12:00:01Z"}, "evidence_not_yet_valid"),
    ({"replay_status": "replayed"}, "evidence_replay_detected"),
])
def test_request_rejections_are_stable(changes: dict, code: str) -> None:
    document = request_document(); document.update(changes)
    assert admit(document).reason_code.value == code


def test_unauthorized_producer_and_unsupported_contract_have_distinct_codes() -> None:
    producer_policy = policy_document(); producer_policy["authorized_producers"] = ["other"]
    assert admit(policy=producer_policy).reason_code.value == "producer_not_authorized"
    version_policy = policy_document(); version_policy["acceptable_contract_versions"] = ["2.0"]
    assert admit(policy=version_policy).reason_code.value == "contract_version_not_supported"


def test_failed_prerequisites_are_checked_in_fixed_order() -> None:
    assert admit(integrity_result=integrity(succeeded=False)).reason_code.value == "integrity_not_verified"
    assert admit(authenticated_provenance_result=authentication(succeeded=False)).reason_code.value == "provenance_not_authenticated"
    assert admit(trust_result=trust(trusted=False)).reason_code.value == "provenance_not_trusted"


def test_malformed_request_and_policy_fail_closed_by_stage() -> None:
    malformed = request_document(); malformed["private_trace"] = "do-not-leak"
    assert admit(malformed).reason_code.value == "invalid_admission_request"
    bad_policy = policy_document(); bad_policy["secret_rule"] = "do-not-leak"
    outcome = admit(policy=bad_policy)
    assert outcome.reason_code.value == "admission_policy_error"
    assert b"do-not-leak" not in encode_reference_architecture_evidence_admission_outcome(outcome)


def test_too_old_and_indeterminate_replay_fail_closed() -> None:
    document = request_document(); document["created_at"] = "2026-09-14T09:00:00Z"
    auth = authentication().model_copy(update={
        "authentication": authentication().authentication.model_copy(update={"issued_at": "2026-09-14T09:00:00Z"})
    })
    assert admit(document, authenticated_provenance_result=auth).reason_code.value == "evidence_too_old"
    document = request_document(); document["replay_status"] = "indeterminate"
    assert admit(document).reason_code.value == "evidence_replay_detected"


def test_equivalent_inputs_serialize_identically_without_internal_leakage() -> None:
    first = encode_reference_architecture_evidence_admission_outcome(admit())
    second = encode_reference_architecture_evidence_admission_outcome(
        admit(deepcopy(request_document()), deepcopy(policy_document()))
    )
    assert first == second
    for forbidden in (b"policy_id", b"signer", b"key_id", b"traceback", b"evaluation"):
        assert forbidden not in first
