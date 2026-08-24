import pytest

from src.candidate_regression_result_adapter import (
    adapt_candidate_regression_results,
)
from src.evaluation_run_regression_comparison import (
    EvaluationRunCaseResult,
)
from src.models import TestResult as CandidateTestResult


def make_test_result(
    *,
    test_id: str,
    passed: bool,
) -> CandidateTestResult:
    return CandidateTestResult.model_construct(
        test_id=test_id,
        passed=passed,
    )


def test_adapts_candidate_results() -> None:
    results = [
        make_test_result(
            test_id="case-001",
            passed=True,
        ),
        make_test_result(
            test_id="case-002",
            passed=False,
        ),
    ]

    adapted = adapt_candidate_regression_results(results)

    assert adapted == (
        EvaluationRunCaseResult(
            case_id="case-001",
            passed=True,
        ),
        EvaluationRunCaseResult(
            case_id="case-002",
            passed=False,
        ),
    )


def test_preserves_candidate_result_order() -> None:
    results = [
        make_test_result(
            test_id="case-z",
            passed=False,
        ),
        make_test_result(
            test_id="case-a",
            passed=True,
        ),
    ]

    adapted = adapt_candidate_regression_results(results)

    assert tuple(result.case_id for result in adapted) == (
        "case-z",
        "case-a",
    )


def test_empty_candidate_results_produce_empty_tuple() -> None:
    assert adapt_candidate_regression_results([]) == ()


def test_requires_results_to_be_a_list() -> None:
    with pytest.raises(TypeError, match="results must be a list"):
        adapt_candidate_regression_results(())  # type: ignore[arg-type]


def test_requires_test_result_objects() -> None:
    with pytest.raises(
        TypeError,
        match="results must contain TestResult objects",
    ):
        adapt_candidate_regression_results(
            ["not-a-result"]  # type: ignore[list-item]
        )


def test_rejects_invalid_candidate_case_id() -> None:
    results = [
        make_test_result(
            test_id=" ",
            passed=True,
        )
    ]

    with pytest.raises(
        ValueError,
        match="case_id must be a non-empty string",
    ):
        adapt_candidate_regression_results(results)
