from copy import deepcopy

import pytest

from src.reference_architecture_evidence_admission_translation import (
    ReferenceArchitectureEvidenceAdmissionTranslationError,
    translate_untrusted_reference_architecture_admission_policy,
)


def policy_document() -> dict:
    return {
        "policy_id": "release-policy", "policy_version": "1.0",
        "supported_evidence_types": ["evaluation-report"],
        "authorized_producers": ["producer-1"],
        "allowed_producer_evidence_types": [["producer-1", "evaluation-report"]],
        "acceptable_contract_versions": ["1.0"], "allowed_purposes": ["release"],
        "allowed_environments": ["production"], "permitted_workflows": ["release-gate"],
        "maximum_evidence_age_seconds": 3600,
    }


def test_policy_translation_copies_untrusted_collections() -> None:
    document = policy_document()
    policy = translate_untrusted_reference_architecture_admission_policy(document)
    document["supported_evidence_types"].append("changed")
    assert policy.supported_evidence_types == frozenset({"evaluation-report"})


@pytest.mark.parametrize("mutation", ["missing", "unknown", "bad_age", "duplicate"])
def test_policy_translation_is_strict(mutation: str) -> None:
    document = deepcopy(policy_document())
    if mutation == "missing":
        document.pop("policy_id")
    elif mutation == "unknown":
        document["secret_rule"] = True
    elif mutation == "bad_age":
        document["maximum_evidence_age_seconds"] = True
    else:
        document["authorized_producers"].append("producer-1")
    with pytest.raises(ReferenceArchitectureEvidenceAdmissionTranslationError):
        translate_untrusted_reference_architecture_admission_policy(document)
