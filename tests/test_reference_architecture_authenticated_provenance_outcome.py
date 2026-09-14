from __future__ import annotations

import pytest

from src.reference_architecture_authenticated_provenance_failure_normalization import (
    ReferenceArchitectureNormalizedAuthenticatedProvenanceV1,
    authenticate_reference_architecture_provenance_with_normalized_failure,
)
from src.reference_architecture_authenticated_provenance_outcome import (
    ReferenceArchitectureAuthenticatedProvenanceOutcomeV1,
    authenticate_public_reference_architecture_provenance,
    project_reference_architecture_authenticated_provenance_outcome,
)
from tests.authenticated_provenance_test_support import signed_document


def test_verified_provenance_projects_only_safe_public_fields() -> None:
    document, binding = signed_document()
    outcome = authenticate_public_reference_architecture_provenance(document, binding)

    assert outcome.succeeded is True
    assert outcome.failure is None
    assert outcome.authentication is not None
    assert outcome.authentication.attestation_id == "attestation-3"
    payload = outcome.model_dump(mode="json")
    text = repr(payload).lower()
    assert "signature" not in text
    assert "public_key" not in text
    assert "canonical" not in text


def test_normalized_failure_projects_as_detached_public_failure() -> None:
    _, binding = signed_document()
    normalized = authenticate_reference_architecture_provenance_with_normalized_failure(
        b"not-json", binding
    )
    outcome = project_reference_architecture_authenticated_provenance_outcome(normalized)
    assert outcome.succeeded is False
    assert outcome.authentication is None
    assert outcome.failure is not normalized.failure
    assert outcome.failure is not None
    assert outcome.failure.code.value == "invalid_provenance_document"


@pytest.mark.parametrize(
    "values",
    [
        {"succeeded": True},
        {"succeeded": False},
        {"succeeded": True, "authentication": None, "failure": None},
    ],
)
def test_public_outcome_requires_one_consistent_branch(values: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        ReferenceArchitectureAuthenticatedProvenanceOutcomeV1.model_validate(values)


def test_projection_rejects_non_normalized_internal_state() -> None:
    with pytest.raises(TypeError, match="A.03.06"):
        project_reference_architecture_authenticated_provenance_outcome(object())  # type: ignore[arg-type]


def test_internal_normalized_contract_still_rejects_empty_state() -> None:
    with pytest.raises(ValueError, match="Exactly one"):
        ReferenceArchitectureNormalizedAuthenticatedProvenanceV1()
