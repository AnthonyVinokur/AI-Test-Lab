# from src.models import TestResult use a postponed or generic annotation.
from __future__ import annotations

from typing import TYPE_CHECKING

from src.report_manager import ReportManager

if TYPE_CHECKING:
    from src.models import TestResult


#class FakeReporter:
    # def __init__(self) -> None:
    #     self.received_results: list[object] | None = None
    #
    # def write(self, results: list) -> None:
    #     self.received_results = results
class FakeReporter:
    def __init__(self) -> None:
        self.received_results: list[TestResult] | None = None

    def write(self, results: list[TestResult]) -> None:
        self.received_results = results


def test_report_manager_calls_every_reporter() -> None:
    first_reporter = FakeReporter()
    second_reporter = FakeReporter()

    manager = ReportManager(
        reporters=[
            first_reporter,
            second_reporter,
        ]
    )

    results = []

    manager.write(results)

    assert first_reporter.received_results is results
    assert second_reporter.received_results is results
