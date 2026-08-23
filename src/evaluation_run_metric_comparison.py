from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EvaluationRunMetricResult:
    case_id: str
    metric_name: str
    score: float

    def __post_init__(self) -> None:
        if not isinstance(self.case_id, str) or not self.case_id.strip():
            raise ValueError("case_id must be a non-empty string")

        if not isinstance(self.metric_name, str) or not self.metric_name.strip():
            raise ValueError("metric_name must be a non-empty string")

        if isinstance(self.score, bool) or not isinstance(self.score, (int, float)):
            raise TypeError("score must be a number")

        if not 0.0 <= self.score <= 1.0:
            raise ValueError("score must be between 0.0 and 1.0")


@dataclass(frozen=True)
class EvaluationRunMetricComparison:
    case_id: str
    metric_name: str
    baseline_score: float
    candidate_score: float
    delta: float


@dataclass(frozen=True)
class EvaluationRunMetricComparisonResult:
    metric_comparisons: tuple[EvaluationRunMetricComparison, ...]


def compare_evaluation_run_metrics(
    *,
    baseline_results: tuple[EvaluationRunMetricResult, ...],
    candidate_results: tuple[EvaluationRunMetricResult, ...],
) -> EvaluationRunMetricComparisonResult:
    baseline_by_key = _index_metric_results(
        baseline_results,
        name="baseline_results",
    )
    candidate_by_key = _index_metric_results(
        candidate_results,
        name="candidate_results",
    )

    baseline_keys = set(baseline_by_key)
    candidate_keys = set(candidate_by_key)

    if baseline_keys != candidate_keys:
        missing_from_candidate = sorted(
            baseline_keys - candidate_keys
        )
        missing_from_baseline = sorted(
            candidate_keys - baseline_keys
        )

        details: list[str] = []

        if missing_from_candidate:
            details.append(
                "missing from candidate: "
                + ", ".join(
                    f"{case_id}/{metric_name}"
                    for case_id, metric_name in missing_from_candidate
                )
            )

        if missing_from_baseline:
            details.append(
                "missing from baseline: "
                + ", ".join(
                    f"{case_id}/{metric_name}"
                    for case_id, metric_name in missing_from_baseline
                )
            )

        raise ValueError(
            "metric result sets do not match: "
            + "; ".join(details)
        )

    comparisons = tuple(
        EvaluationRunMetricComparison(
            case_id=case_id,
            metric_name=metric_name,
            baseline_score=baseline_by_key[
                (case_id, metric_name)
            ].score,
            candidate_score=candidate_by_key[
                (case_id, metric_name)
            ].score,
            delta=(
                candidate_by_key[(case_id, metric_name)].score
                - baseline_by_key[(case_id, metric_name)].score
            ),
        )
        for case_id, metric_name in sorted(baseline_keys)
    )

    return EvaluationRunMetricComparisonResult(
        metric_comparisons=comparisons,
    )


def _index_metric_results(
    results: tuple[EvaluationRunMetricResult, ...],
    *,
    name: str,
) -> dict[tuple[str, str], EvaluationRunMetricResult]:
    if not isinstance(results, tuple):
        raise TypeError(f"{name} must be a tuple")

    indexed: dict[
        tuple[str, str],
        EvaluationRunMetricResult,
    ] = {}

    for result in results:
        if not isinstance(result, EvaluationRunMetricResult):
            raise TypeError(
                f"{name} must contain EvaluationRunMetricResult objects"
            )

        key = (result.case_id, result.metric_name)

        if key in indexed:
            raise ValueError(
                "duplicate metric result: "
                f"{result.case_id}/{result.metric_name}"
            )

        indexed[key] = result

    return indexed

