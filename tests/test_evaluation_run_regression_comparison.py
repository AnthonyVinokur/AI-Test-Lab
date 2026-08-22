from dataclasses import replace

import pytest

from src.evaluation_run_provenance import EvaluationRunProvenance
from src.evaluation_run_regression_comparison import (
    EvaluationRunCaseResult,
    EvaluationRunRegressionChange,
    compare_evaluation_runs_for_regression,
)


@pytest.fixture
def baseline_provenance() -> EvaluationRunProvenance:
    return EvaluationRunProvenance(
        run_id="run-001",
        model="llama3.1:latest",
        evaluation_profile="default",
        dataset="core",
        dataset_version="v1",
        report_contract="public-report-v1",
        report_contract_fingerprint="fingerprint-001",
    )


@pytest.fixture
def candidate_provenance(
    baseline_provenance: EvaluationRunProvenance,
) -> EvaluationRunProvenance:
    return replace(
        baseline_provenance,
        run_id="run-002",
    )


def test_pass_to_fail_is_regression(
    baseline_provenance: EvaluationRunProvenance,
    candidate_provenance: EvaluationRunProvenance,
) -> None:
    result = compare_evaluation_runs_for_regression(
        baseline_provenance,
        candidate_provenance,
        baseline_results=(
            EvaluationRunCaseResult(
                case_id="case-001",
                passed=True,
            ),
        ),
        candidate_results=(
            EvaluationRunCaseResult(
                case_id="case-001",
                passed=False,
            ),
        ),
    )

    assert result.compared_count == 1
    assert result.unchanged_count == 0
    assert result.improved_count == 0
    assert result.regressed_count == 1
    assert result.has_regressions is True
    assert result.case_comparisons[0].change is (
        EvaluationRunRegressionChange.REGRESSED
    )


def test_fail_to_pass_is_improvement(
    baseline_provenance: EvaluationRunProvenance,
    candidate_provenance: EvaluationRunProvenance,
) -> None:
    result = compare_evaluation_runs_for_regression(
        baseline_provenance,
        candidate_provenance,
        baseline_results=(
            EvaluationRunCaseResult(
                case_id="case-001",
                passed=False,
            ),
        ),
        candidate_results=(
            EvaluationRunCaseResult(
                case_id="case-001",
                passed=True,
            ),
        ),
    )

    assert result.improved_count == 1
    assert result.regressed_count == 0
    assert result.has_regressions is False
    assert result.case_comparisons[0].change is (
        EvaluationRunRegressionChange.IMPROVED
    )


@pytest.mark.parametrize(
    ("baseline_passed", "candidate_passed"),
    [
        (True, True),
        (False, False),
    ],
)
def test_same_verdict_is_unchanged(
    baseline_provenance: EvaluationRunProvenance,
    candidate_provenance: EvaluationRunProvenance,
    baseline_passed: bool,
    candidate_passed: bool,
) -> None:
    result = compare_evaluation_runs_for_regression(
        baseline_provenance,
        candidate_provenance,
        baseline_results=(
            EvaluationRunCaseResult(
                case_id="case-001",
                passed=baseline_passed,
            ),
        ),
        candidate_results=(
            EvaluationRunCaseResult(
                case_id="case-001",
                passed=candidate_passed,
            ),
        ),
    )

    assert result.unchanged_count == 1
    assert result.improved_count == 0
    assert result.regressed_count == 0
    assert result.case_comparisons[0].change is (
        EvaluationRunRegressionChange.UNCHANGED
    )


def test_multiple_cases_are_aggregated(
    baseline_provenance: EvaluationRunProvenance,
    candidate_provenance: EvaluationRunProvenance,
) -> None:
    result = compare_evaluation_runs_for_regression(
        baseline_provenance,
        candidate_provenance,
        baseline_results=(
            EvaluationRunCaseResult("case-001", True),
            EvaluationRunCaseResult("case-002", False),
            EvaluationRunCaseResult("case-003", True),
            EvaluationRunCaseResult("case-004", False),
        ),
        candidate_results=(
            EvaluationRunCaseResult("case-001", False),
            EvaluationRunCaseResult("case-002", True),
            EvaluationRunCaseResult("case-003", True),
            EvaluationRunCaseResult("case-004", False),
        ),
    )

    assert result.baseline_run_id == "run-001"
    assert result.candidate_run_id == "run-002"
    assert result.compared_count == 4
    assert result.unchanged_count == 2
    assert result.improved_count == 1
    assert result.regressed_count == 1


def test_case_comparison_order_is_deterministic(
    baseline_provenance: EvaluationRunProvenance,
    candidate_provenance: EvaluationRunProvenance,
) -> None:
    result = compare_evaluation_runs_for_regression(
        baseline_provenance,
        candidate_provenance,
        baseline_results=(
            EvaluationRunCaseResult("case-003", True),
            EvaluationRunCaseResult("case-001", True),
            EvaluationRunCaseResult("case-002", False),
        ),
        candidate_results=(
            EvaluationRunCaseResult("case-002", True),
            EvaluationRunCaseResult("case-003", True),
            EvaluationRunCaseResult("case-001", False),
        ),
    )

    assert tuple(
        comparison.case_id
        for comparison in result.case_comparisons
    ) == (
        "case-001",
        "case-002",
        "case-003",
    )


def test_ineligible_runs_are_rejected(
    baseline_provenance: EvaluationRunProvenance,
) -> None:
    candidate = replace(
        baseline_provenance,
        run_id="run-002",
        dataset_version="v2",
    )

    with pytest.raises(
        ValueError,
        match=(
            "evaluation runs are not eligible "
            "for regression comparison: dataset_version"
        ),
    ):
        compare_evaluation_runs_for_regression(
            baseline_provenance,
            candidate,
            baseline_results=(),
            candidate_results=(),
        )


def test_missing_candidate_case_is_rejected(
    baseline_provenance: EvaluationRunProvenance,
    candidate_provenance: EvaluationRunProvenance,
) -> None:
    with pytest.raises(
        ValueError,
        match="missing from candidate: case-002",
    ):
        compare_evaluation_runs_for_regression(
            baseline_provenance,
            candidate_provenance,
            baseline_results=(
                EvaluationRunCaseResult("case-001", True),
                EvaluationRunCaseResult("case-002", True),
            ),
            candidate_results=(
                EvaluationRunCaseResult("case-001", True),
            ),
        )


def test_missing_baseline_case_is_rejected(
    baseline_provenance: EvaluationRunProvenance,
    candidate_provenance: EvaluationRunProvenance,
) -> None:
    with pytest.raises(
        ValueError,
        match="missing from baseline: case-002",
    ):
        compare_evaluation_runs_for_regression(
            baseline_provenance,
            candidate_provenance,
            baseline_results=(
                EvaluationRunCaseResult("case-001", True),
            ),
            candidate_results=(
                EvaluationRunCaseResult("case-001", True),
                EvaluationRunCaseResult("case-002", False),
            ),
        )


def test_duplicate_baseline_case_is_rejected(
    baseline_provenance: EvaluationRunProvenance,
    candidate_provenance: EvaluationRunProvenance,
) -> None:
    with pytest.raises(
        ValueError,
        match=(
            "baseline_results contains duplicate "
            "case_id: case-001"
        ),
    ):
        compare_evaluation_runs_for_regression(
            baseline_provenance,
            candidate_provenance,
            baseline_results=(
                EvaluationRunCaseResult("case-001", True),
                EvaluationRunCaseResult("case-001", False),
            ),
            candidate_results=(
                EvaluationRunCaseResult("case-001", True),
            ),
        )


def test_empty_runs_can_be_compared(
    baseline_provenance: EvaluationRunProvenance,
    candidate_provenance: EvaluationRunProvenance,
) -> None:
    result = compare_evaluation_runs_for_regression(
        baseline_provenance,
        candidate_provenance,
        baseline_results=(),
        candidate_results=(),
    )

    assert result.compared_count == 0
    assert result.unchanged_count == 0
    assert result.improved_count == 0
    assert result.regressed_count == 0
    assert result.case_comparisons == ()
    assert result.has_regressions is False


def test_invalid_case_id_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="case_id must be a non-empty string",
    ):
        EvaluationRunCaseResult(
            case_id="",
            passed=True,
        )


def test_non_boolean_passed_value_is_rejected() -> None:
    with pytest.raises(
        TypeError,
        match="passed must be a bool",
    ):
        EvaluationRunCaseResult(
            case_id="case-001",
            passed=1,  # type: ignore[arg-type]
        )


