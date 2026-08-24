from __future__ import annotations

from src.evaluation_run_regression_comparison import (
    EvaluationRunCaseResult,
)
from src.models import TestResult


def adapt_candidate_regression_results(
    results: list[TestResult],
) -> tuple[EvaluationRunCaseResult, ...]:
    """Convert candidate CLI results into regression comparison inputs."""

    if not isinstance(results, list):
        raise TypeError("results must be a list")

    adapted_results: list[EvaluationRunCaseResult] = []

    for result in results:
        if not isinstance(result, TestResult):
            raise TypeError("results must contain TestResult objects")

        adapted_results.append(
            EvaluationRunCaseResult(
                case_id=result.test_id,
                passed=result.passed,
            )
        )

    return tuple(adapted_results)
