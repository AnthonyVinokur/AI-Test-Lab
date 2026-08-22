from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from src.evaluation_run_provenance import EvaluationRunProvenance
from src.evaluation_run_regression_eligibility import (
    determine_evaluation_run_regression_eligibility,
)


class EvaluationRunRegressionChange(str, Enum):
    UNCHANGED = "unchanged"
    IMPROVED = "improved"
    REGRESSED = "regressed"


@dataclass(frozen=True)
class EvaluationRunCaseResult:
    case_id: str
    passed: bool

    def __post_init__(self) -> None:
        if not isinstance(self.case_id, str) or not self.case_id.strip():
            raise ValueError("case_id must be a non-empty string")

        if not isinstance(self.passed, bool):
            raise TypeError("passed must be a bool")


@dataclass(frozen=True)
class EvaluationRunCaseComparison:
    case_id: str
    baseline_passed: bool
    candidate_passed: bool
    change: EvaluationRunRegressionChange


@dataclass(frozen=True)
class EvaluationRunRegressionComparison:
    baseline_run_id: str
    candidate_run_id: str
    compared_count: int
    unchanged_count: int
    improved_count: int
    regressed_count: int
    case_comparisons: tuple[EvaluationRunCaseComparison, ...]

    @property
    def has_regressions(self) -> bool:
        return self.regressed_count > 0


def compare_evaluation_runs_for_regression(
    baseline: EvaluationRunProvenance,
    candidate: EvaluationRunProvenance,
    baseline_results: tuple[EvaluationRunCaseResult, ...],
    candidate_results: tuple[EvaluationRunCaseResult, ...],
) -> EvaluationRunRegressionComparison:
    eligibility = determine_evaluation_run_regression_eligibility(
        baseline,
        candidate,
    )

    if not eligibility.eligible:
        mismatch_text = ", ".join(eligibility.mismatches)
        raise ValueError(
            "evaluation runs are not eligible for regression comparison: "
            f"{mismatch_text}"
        )

    baseline_by_case = _index_results(
        baseline_results,
        name="baseline_results",
    )
    candidate_by_case = _index_results(
        candidate_results,
        name="candidate_results",
    )

    baseline_case_ids = set(baseline_by_case)
    candidate_case_ids = set(candidate_by_case)

    if baseline_case_ids != candidate_case_ids:
        missing_from_candidate = sorted(
            baseline_case_ids - candidate_case_ids
        )
        missing_from_baseline = sorted(
            candidate_case_ids - baseline_case_ids
        )

        details: list[str] = []

        if missing_from_candidate:
            details.append(
                "missing from candidate: "
                + ", ".join(missing_from_candidate)
            )

        if missing_from_baseline:
            details.append(
                "missing from baseline: "
                + ", ".join(missing_from_baseline)
            )

        raise ValueError(
            "evaluation run case sets do not match: "
            + "; ".join(details)
        )

    comparisons: list[EvaluationRunCaseComparison] = []

    for case_id in sorted(baseline_case_ids):
        baseline_result = baseline_by_case[case_id]
        candidate_result = candidate_by_case[case_id]

        change = _classify_change(
            baseline_passed=baseline_result.passed,
            candidate_passed=candidate_result.passed,
        )

        comparisons.append(
            EvaluationRunCaseComparison(
                case_id=case_id,
                baseline_passed=baseline_result.passed,
                candidate_passed=candidate_result.passed,
                change=change,
            )
        )

    case_comparisons = tuple(comparisons)

    return EvaluationRunRegressionComparison(
        baseline_run_id=baseline.run_id,
        candidate_run_id=candidate.run_id,
        compared_count=len(case_comparisons),
        unchanged_count=sum(
            comparison.change
            is EvaluationRunRegressionChange.UNCHANGED
            for comparison in case_comparisons
        ),
        improved_count=sum(
            comparison.change
            is EvaluationRunRegressionChange.IMPROVED
            for comparison in case_comparisons
        ),
        regressed_count=sum(
            comparison.change
            is EvaluationRunRegressionChange.REGRESSED
            for comparison in case_comparisons
        ),
        case_comparisons=case_comparisons,
    )


def _index_results(
    results: tuple[EvaluationRunCaseResult, ...],
    *,
    name: str,
) -> dict[str, EvaluationRunCaseResult]:
    if not isinstance(results, tuple):
        raise TypeError(f"{name} must be a tuple")

    indexed: dict[str, EvaluationRunCaseResult] = {}

    for result in results:
        if not isinstance(result, EvaluationRunCaseResult):
            raise TypeError(
                f"{name} must contain EvaluationRunCaseResult objects"
            )

        if result.case_id in indexed:
            raise ValueError(
                f"{name} contains duplicate case_id: {result.case_id}"
            )

        indexed[result.case_id] = result

    return indexed


def _classify_change(
    *,
    baseline_passed: bool,
    candidate_passed: bool,
) -> EvaluationRunRegressionChange:
    if baseline_passed and not candidate_passed:
        return EvaluationRunRegressionChange.REGRESSED

    if not baseline_passed and candidate_passed:
        return EvaluationRunRegressionChange.IMPROVED

    return EvaluationRunRegressionChange.UNCHANGED