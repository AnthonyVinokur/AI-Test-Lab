from dataclasses import replace

import pytest

from src.evaluation_run_provenance import EvaluationRunProvenance
from src.evaluation_run_regression_eligibility import (
    determine_evaluation_run_regression_eligibility,
)


@pytest.fixture
def baseline() -> EvaluationRunProvenance:
    return EvaluationRunProvenance(
        run_id="run-001",
        model="llama3.1:latest",
        evaluation_profile="default",
        dataset="core",
        dataset_version="v1",
        report_contract="public-report-v1",
        report_contract_fingerprint="fingerprint-001",
    )


def test_reproducible_runs_are_eligible(
    baseline: EvaluationRunProvenance,
) -> None:
    candidate = replace(
        baseline,
        run_id="run-002",
    )

    result = determine_evaluation_run_regression_eligibility(
        baseline,
        candidate,
    )

    assert result.eligible is True
    assert result.mismatches == ()


def test_model_mismatch_makes_runs_ineligible(
    baseline: EvaluationRunProvenance,
) -> None:
    candidate = replace(
        baseline,
        run_id="run-002",
        model="different-model",
    )

    result = determine_evaluation_run_regression_eligibility(
        baseline,
        candidate,
    )

    assert result.eligible is False
    assert result.mismatches == ("model",)


def test_dataset_version_mismatch_makes_runs_ineligible(
    baseline: EvaluationRunProvenance,
) -> None:
    candidate = replace(
        baseline,
        run_id="run-002",
        dataset_version="v2",
    )

    result = determine_evaluation_run_regression_eligibility(
        baseline,
        candidate,
    )

    assert result.eligible is False
    assert result.mismatches == ("dataset_version",)


def test_multiple_mismatches_are_preserved_in_deterministic_order(
    baseline: EvaluationRunProvenance,
) -> None:
    candidate = replace(
        baseline,
        run_id="run-002",
        model="different-model",
        dataset_version="v2",
        report_contract="public-report-v2",
    )

    result = determine_evaluation_run_regression_eligibility(
        baseline,
        candidate,
    )

    assert result.eligible is False
    assert result.mismatches == (
        "model",
        "dataset_version",
        "report_contract",
    )


def test_invalid_baseline_is_rejected(
    baseline: EvaluationRunProvenance,
) -> None:
    with pytest.raises(
        TypeError,
        match="baseline must be an EvaluationRunProvenance",
    ):
        determine_evaluation_run_regression_eligibility(
            "invalid",  # type: ignore[arg-type]
            baseline,
        )


def test_invalid_candidate_is_rejected(
    baseline: EvaluationRunProvenance,
) -> None:
    with pytest.raises(
        TypeError,
        match="candidate must be an EvaluationRunProvenance",
    ):
        determine_evaluation_run_regression_eligibility(
            baseline,
            "invalid",  # type: ignore[arg-type]
        )