from __future__ import annotations

from pathlib import Path

from src.report_inspector import (
    get_engine_failures,
    get_failed_results,
    get_metric_results,
    get_passing_results,
    get_results_for_model,
)
from src.report_reader import load_report


_FIXTURE_PATH = (
    Path(__file__).parent
    / "fixtures"
    / "report-v1.0.json"
)


def test_get_passing_results() -> None:
    report = load_report(_FIXTURE_PATH)

    results = get_passing_results(report)

    assert len(results) == 1
    assert results[0].test_id == "greeting-001"


def test_get_failed_results_returns_empty_for_passing_fixture() -> None:
    report = load_report(_FIXTURE_PATH)

    results = get_failed_results(report)

    assert results == []


def test_get_results_for_model() -> None:
    report = load_report(_FIXTURE_PATH)

    results = get_results_for_model(
        report,
        "llama3.1",
    )

    assert len(results) == 1
    assert results[0].model == "llama3.1"


def test_get_results_for_unknown_model_returns_empty() -> None:
    report = load_report(_FIXTURE_PATH)

    results = get_results_for_model(
        report,
        "missing-model",
    )

    assert results == []


def test_get_engine_failures() -> None:
    report = load_report(_FIXTURE_PATH)

    failures = get_engine_failures(report)

    assert len(failures) == 1

    test_result, engine_result = failures[0]

    assert test_result.test_id == "greeting-001"
    assert engine_result.engine == "deepeval"
    assert engine_result.succeeded is False


def test_get_metric_results() -> None:
    report = load_report(_FIXTURE_PATH)

    metrics = get_metric_results(
        report,
        "contains",
    )

    assert len(metrics) == 1

    test_result, metric_result = metrics[0]

    assert test_result.test_id == "greeting-001"
    assert metric_result.metric_name == "contains"
    assert metric_result.score == 1.0


def test_get_unknown_metric_returns_empty() -> None:
    report = load_report(_FIXTURE_PATH)

    metrics = get_metric_results(
        report,
        "missing-metric",
    )

    assert metrics == []