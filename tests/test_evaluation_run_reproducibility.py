import pytest

from src.evaluation_run_provenance import EvaluationRunProvenance
from src.evaluation_run_reproducibility import (
    EvaluationRunReproducibilityVerification,
    verify_evaluation_run_reproducibility,
)


def make_provenance(
    *,
    run_id: str = "run-001",
    model: str = "llama3.1:latest",
    evaluation_profile: str = "default",
    dataset: str = "sample-dataset",
    dataset_version: str = "v1",
    report_contract: str = "public-report-v1",
    report_contract_fingerprint: str = "contract-fingerprint-001",
) -> EvaluationRunProvenance:
    return EvaluationRunProvenance(
        run_id=run_id,
        model=model,
        evaluation_profile=evaluation_profile,
        dataset=dataset,
        dataset_version=dataset_version,
        report_contract=report_contract,
        report_contract_fingerprint=report_contract_fingerprint,
    )


def test_identical_reproducibility_conditions_are_reproducible():
    baseline = make_provenance(run_id="run-001")
    candidate = make_provenance(run_id="run-002")

    result = verify_evaluation_run_reproducibility(
        baseline,
        candidate,
    )

    assert result == EvaluationRunReproducibilityVerification(
        reproducible=True,
        mismatches=(),
    )


def test_run_id_difference_does_not_break_reproducibility():
    baseline = make_provenance(run_id="run-001")
    candidate = make_provenance(run_id="run-999")

    result = verify_evaluation_run_reproducibility(
        baseline,
        candidate,
    )

    assert result.reproducible is True
    assert result.mismatches == ()


def test_dataset_version_difference_breaks_reproducibility():
    baseline = make_provenance(dataset_version="v1")
    candidate = make_provenance(dataset_version="v2")

    result = verify_evaluation_run_reproducibility(
        baseline,
        candidate,
    )

    assert result.reproducible is False
    assert result.mismatches == ("dataset_version",)


def test_model_difference_breaks_reproducibility():
    baseline = make_provenance(model="llama3.1:latest")
    candidate = make_provenance(model="different-model")

    result = verify_evaluation_run_reproducibility(
        baseline,
        candidate,
    )

    assert result.reproducible is False
    assert result.mismatches == ("model",)


def test_multiple_mismatches_are_reported_deterministically():
    baseline = make_provenance()

    candidate = make_provenance(
        model="different-model",
        dataset_version="v2",
        report_contract_fingerprint="different-fingerprint",
    )

    result = verify_evaluation_run_reproducibility(
        baseline,
        candidate,
    )

    assert result.reproducible is False
    assert result.mismatches == (
        "model",
        "dataset_version",
        "report_contract_fingerprint",
    )


def test_invalid_baseline_type_is_rejected():
    candidate = make_provenance()

    with pytest.raises(
        TypeError,
        match="baseline must be an EvaluationRunProvenance",
    ):
        verify_evaluation_run_reproducibility(
            "not-provenance",
            candidate,
        )


def test_invalid_candidate_type_is_rejected():
    baseline = make_provenance()

    with pytest.raises(
        TypeError,
        match="candidate must be an EvaluationRunProvenance",
    ):
        verify_evaluation_run_reproducibility(
            baseline,
            "not-provenance",
        )