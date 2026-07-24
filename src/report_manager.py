from typing import Protocol

from src.models import TestResult


class Reporter(Protocol):
    """Defines the interface required by every reporter."""

    def write(self, results: list[TestResult]) -> None:
        ...


class ReportManager:
    """Runs multiple reporters for the same collection of test results."""

    def __init__(self, reporters: list[Reporter]) -> None:
        self.reporters = reporters

    def write(self, results: list[TestResult]) -> None:
        for reporter in self.reporters:
            reporter.write(results)