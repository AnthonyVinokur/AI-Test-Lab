from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.evaluation_models import EvaluationRequest, MetricResult
from src.evaluation_plugins import (
    EvaluationEngineRegistry,
    discover_evaluation_plugins,
)


class FakeEngine:
    @property
    def name(self) -> str:
        return "fake"

    def evaluate(
        self,
        request: EvaluationRequest,
    ) -> list[MetricResult]:
        return []


def fake_factory(
    config: Mapping[str, Any] | None = None,
) -> FakeEngine:
    return FakeEngine()


class FakeEntryPoint:
    name = "fake"
    value = "fake_package:create_engine"

    def load(self):
        return fake_factory


class FakeEntryPoints:
    def select(self, *, group: str):
        assert group == "ai_test_lab.evaluation_engines"
        return [FakeEntryPoint()]


def test_discovers_installed_plugins(monkeypatch) -> None:
    monkeypatch.setattr(
        "src.evaluation_plugins.discovery.entry_points",
        lambda: FakeEntryPoints(),
    )

    registry = EvaluationEngineRegistry()

    discovered = discover_evaluation_plugins(registry)

    assert discovered == ("fake",)
    assert registry.contains("fake")