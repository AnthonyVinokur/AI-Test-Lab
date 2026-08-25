from __future__ import annotations

import pytest

from src.candidate_evaluation_run_provenance import (
    construct_candidate_evaluation_run_provenance,
)
from src.evaluation_run_identity import EvaluationRunIdentity
from src.evaluation_run_provenance import EvaluationRunProvenance
from src.report_contract_fingerprint import (
    public_report_contract_fingerprint,
)
from src.report_contract_identity import (
    public_report_contract_identity,
)


def _identity() -> EvaluationRunIdentity:
    return EvaluationRunIdentity(
        run_id="run-candidate-001",
        model="llama3.1:latest",
        evaluation_profile="fast-ci",
        dataset="regression-suite",
    )


def test_construct_candidate_provenance_returns_expected_contract() -> None:
    provenance = construct_candidate_evaluation_run_provenance(
        identity=_identity(),
        dataset_version="1",
        report_schema_version="1.0",
    )

    contract = public_report_contract_identity("1.0")

    assert provenance == EvaluationRunProvenance(
        run_id="run-candidate-001",
        model="llama3.1:latest",
        evaluation_profile="fast-ci",
        dataset="regression-suite",
        dataset_version="1",
        report_contract=contract.name,
        report_contract_fingerprint=(
            public_report_contract_fingerprint("1.0")
        ),
    )


def test_construct_candidate_provenance_preserves_identity_fields() -> None:
    identity = _identity()

    provenance = construct_candidate_evaluation_run_provenance(
        identity=identity,
        dataset_version="7",
        report_schema_version="1.0",
    )

    assert provenance.run_id == identity.run_id
    assert provenance.model == identity.model
    assert provenance.evaluation_profile == identity.evaluation_profile
    assert provenance.dataset == identity.dataset
    assert provenance.dataset_version == "7"


def test_construct_candidate_provenance_uses_report_contract_helpers() -> None:
    provenance = construct_candidate_evaluation_run_provenance(
        identity=_identity(),
        dataset_version="1",
        report_schema_version="1.0",
    )

    contract = public_report_contract_identity("1.0")

    assert provenance.report_contract == contract.name
    assert provenance.report_contract_fingerprint == (
        public_report_contract_fingerprint("1.0")
    )


def test_construct_candidate_provenance_is_deterministic() -> None:
    kwargs = {
        "identity": _identity(),
        "dataset_version": "1",
        "report_schema_version": "1.0",
    }

    first = construct_candidate_evaluation_run_provenance(**kwargs)
    second = construct_candidate_evaluation_run_provenance(**kwargs)

    assert first == second


def test_construct_candidate_provenance_rejects_wrong_identity_type() -> None:
    with pytest.raises(
        TypeError,
        match="identity must be an EvaluationRunIdentity",
    ):
        construct_candidate_evaluation_run_provenance(
            identity="not-an-identity",  # type: ignore[arg-type]
            dataset_version="1",
            report_schema_version="1.0",
        )


@pytest.mark.parametrize(
    "dataset_version",
    [
        "",
        "   ",
    ],
)
def test_construct_candidate_provenance_rejects_invalid_dataset_version(
    dataset_version: str,
) -> None:
    with pytest.raises(
        ValueError,
        match="dataset_version must be a non-empty string",
    ):
        construct_candidate_evaluation_run_provenance(
            identity=_identity(),
            dataset_version=dataset_version,
            report_schema_version="1.0",
        )


def test_construct_candidate_provenance_rejects_non_string_dataset_version() -> None:
    with pytest.raises(
        ValueError,
        match="dataset_version must be a non-empty string",
    ):
        construct_candidate_evaluation_run_provenance(
            identity=_identity(),
            dataset_version=None,  # type: ignore[arg-type]
            report_schema_version="1.0",
        )


def test_construct_candidate_provenance_rejects_unsupported_report_version() -> None:
    with pytest.raises(
        ValueError,
        match="Unsupported public report schema version",
    ):
        construct_candidate_evaluation_run_provenance(
            identity=_identity(),
            dataset_version="1",
            report_schema_version="999.0",
        )
