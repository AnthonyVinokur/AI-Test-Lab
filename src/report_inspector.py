from __future__ import annotations

from src.report_reader import PublicReport
from src.report_schema import (
    ReportEngineExecutionResultV1,
    ReportMetricResultV1,
    ReportTestResultV1,
)


def get_failed_results(
    report: PublicReport,
) -> list[ReportTestResultV1]:
    """Return public test results that did not pass."""

    return [
        result
        for result in report.results
        if not result.passed
    ]


def get_passing_results(
    report: PublicReport,
) -> list[ReportTestResultV1]:
    """Return public test results that passed."""

    return [
        result
        for result in report.results
        if result.passed
    ]


def get_results_for_model(
    report: PublicReport,
    model: str,
) -> list[ReportTestResultV1]:
    """Return public test results for one model."""

    return [
        result
        for result in report.results
        if result.model == model
    ]


def get_engine_failures(
    report: PublicReport,
) -> list[
    tuple[
        ReportTestResultV1,
        ReportEngineExecutionResultV1,
    ]
]:
    """Return failed engine executions with their test result."""

    failures: list[
        tuple[
            ReportTestResultV1,
            ReportEngineExecutionResultV1,
        ]
    ] = []

    for result in report.results:
        for engine_result in result.engine_results:
            if not engine_result.succeeded:
                failures.append(
                    (
                        result,
                        engine_result,
                    )
                )

    return failures


def get_metric_results(
    report: PublicReport,
    metric_name: str,
) -> list[
    tuple[
        ReportTestResultV1,
        ReportMetricResultV1,
    ]
]:
    """Return metric results matching one public metric name."""

    matches: list[
        tuple[
            ReportTestResultV1,
            ReportMetricResultV1,
        ]
    ] = []

    for result in report.results:
        for metric_result in result.evaluation_results:
            if metric_result.metric_name == metric_name:
                matches.append(
                    (
                        result,
                        metric_result,
                    )
                )

    return matches