"""Public report summarization for AI Test Lab.

This module consumes the versioned public report contract.  It deliberately
does not import evaluation-pipeline, engine, governance, or other internal
runtime models.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class MetricFailureSummary:
    """Public description of one failed metric result."""

    test_id: str
    engine: str
    metric_name: str
    score: float
    threshold: float


@dataclass(frozen=True, slots=True)
class EngineFailureSummary:
    """Public description of one failed evaluation-engine execution."""

    test_id: str
    engine: str
    error: str | None = None


@dataclass(frozen=True, slots=True)
class ReportSummary:
    """Small, stable consumer view derived only from a public report."""

    schema_version: str
    generated_at: str
    overall_status: str

    total: int
    passed: int
    failed: int
    expected_failures: int
    unexpected_passes: int
    errors: int
    pass_rate_percent: float

    profiles: tuple[str, ...]
    failed_test_ids: tuple[str, ...]
    failed_metrics: tuple[MetricFailureSummary, ...]
    engine_failures: tuple[EngineFailureSummary, ...]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable public representation."""
        return asdict(self)


def summarize_report(report: Mapping[str, Any]) -> ReportSummary:
    """Build a stable consumer summary from a validated public report.

    The caller is expected to validate/inspect the report first.  This
    function intentionally reads only fields already exposed by the public
    report contract.
    """
    summary = _require_mapping(report, "summary")
    results = _require_list(report, "results")

    total = _require_int(summary, "total")
    passed = _require_int(summary, "passed")
    failed = _require_int(summary, "failed")
    expected_failures = _require_int(summary, "expected_failures")
    unexpected_passes = _require_int(summary, "unexpected_passes")
    errors = _require_int(summary, "errors")
    pass_rate_percent = _require_number(summary, "pass_rate_percent")

    failed_test_ids: list[str] = []
    failed_metrics: list[MetricFailureSummary] = []
    engine_failures: list[EngineFailureSummary] = []
    profiles: set[str] = set()

    for index, raw_result in enumerate(results):
        if not isinstance(raw_result, Mapping):
            raise TypeError(f"results[{index}] must be an object")

        test_id = _require_str(raw_result, "test_id")

        if raw_result.get("passed") is False:
            failed_test_ids.append(test_id)

        raw_metric_results = raw_result.get("evaluation_results", [])
        if not isinstance(raw_metric_results, list):
            raise TypeError(
                f"results[{index}].evaluation_results must be an array"
            )

        for metric_index, raw_metric in enumerate(raw_metric_results):
            if not isinstance(raw_metric, Mapping):
                raise TypeError(
                    "results"
                    f"[{index}].evaluation_results[{metric_index}] must be an object"
                )

            profile_name = raw_metric.get("profile_name")
            if isinstance(profile_name, str) and profile_name:
                profiles.add(profile_name)

            if raw_metric.get("passed") is False:
                failed_metrics.append(
                    MetricFailureSummary(
                        test_id=test_id,
                        engine=_require_str(raw_metric, "engine"),
                        metric_name=_require_str(raw_metric, "metric_name"),
                        score=_require_number(raw_metric, "score"),
                        threshold=_require_number(raw_metric, "threshold"),
                    )
                )

        raw_engine_results = raw_result.get("engine_results", [])
        if not isinstance(raw_engine_results, list):
            raise TypeError(f"results[{index}].engine_results must be an array")

        for engine_index, raw_engine in enumerate(raw_engine_results):
            if not isinstance(raw_engine, Mapping):
                raise TypeError(
                    "results"
                    f"[{index}].engine_results[{engine_index}] must be an object"
                )

            if raw_engine.get("succeeded") is False:
                error = raw_engine.get("error")
                if error is not None and not isinstance(error, str):
                    raise TypeError(
                        "results"
                        f"[{index}].engine_results[{engine_index}].error "
                        "must be a string or null"
                    )

                engine_failures.append(
                    EngineFailureSummary(
                        test_id=test_id,
                        engine=_require_str(raw_engine, "engine"),
                        error=error,
                    )
                )

    return ReportSummary(
        schema_version=_require_str(report, "schema_version"),
        generated_at=_require_str(report, "generated_at"),
        overall_status=_overall_status(
            total=total,
            failed=failed,
            errors=errors,
        ),
        total=total,
        passed=passed,
        failed=failed,
        expected_failures=expected_failures,
        unexpected_passes=unexpected_passes,
        errors=errors,
        pass_rate_percent=pass_rate_percent,
        profiles=tuple(sorted(profiles)),
        failed_test_ids=tuple(failed_test_ids),
        failed_metrics=tuple(failed_metrics),
        engine_failures=tuple(engine_failures),
    )


def _overall_status(*, total: int, failed: int, errors: int) -> str:
    if errors:
        return "error"
    if failed:
        return "failed"
    if total == 0:
        return "empty"
    return "passed"


def _require_mapping(container: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = container.get(key)
    if not isinstance(value, Mapping):
        raise TypeError(f"{key} must be an object")
    return value


def _require_list(container: Mapping[str, Any], key: str) -> list[Any]:
    value = container.get(key)
    if not isinstance(value, list):
        raise TypeError(f"{key} must be an array")
    return value


def _require_str(container: Mapping[str, Any], key: str) -> str:
    value = container.get(key)
    if not isinstance(value, str):
        raise TypeError(f"{key} must be a string")
    return value


def _require_int(container: Mapping[str, Any], key: str) -> int:
    value = container.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{key} must be an integer")
    return value


def _require_number(container: Mapping[str, Any], key: str) -> float:
    value = container.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{key} must be a number")
    return float(value)
