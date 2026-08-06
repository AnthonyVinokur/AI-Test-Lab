from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pytest

from src.evaluation_models import EvaluationRequest, MetricResult
from src.evaluation_plugins import (
    EvaluationEngineRegistry,
    InvalidPluginError,
    PluginAlreadyRegisteredError,
    PluginNotFoundError,
)


class FakeEvaluationEngine:
    def __init__(
        self,
        *,
        name: str = "fake",
        score: float = 0.9,
    ) -> None:
        self._name = name
        self.score = score

    @property
    def name(self) -> str:
        return self._name

    def evaluate(
        self,
        request: EvaluationRequest,
    ) -> list[MetricResult]:
        return [
            MetricResult(
                metric_name=request.metrics[0],
                score=self.score,
                passed=self.score >= request.threshold,
                threshold=request.threshold,
                engine=self.name,
                reason="Fake evaluation completed.",
            )
        ]


def fake_factory(
    config: Mapping[str, Any] | None = None,
) -> FakeEvaluationEngine:
    settings = dict(config or {})

    return FakeEvaluationEngine(
        score=float(settings.get("score", 0.9)),
    )


def test_registers_engine_factory() -> None:
    registry = EvaluationEngineRegistry()

    registry.register("fake", fake_factory)

    assert registry.contains("fake")
    assert registry.names() == ("fake",)
    assert len(registry) == 1


def test_normalizes_registered_engine_name() -> None:
    registry = EvaluationEngineRegistry()

    registry.register("  FAKE  ", fake_factory)

    assert registry.contains("fake")
    assert registry.contains("FAKE")


def test_creates_registered_engine() -> None:
    registry = EvaluationEngineRegistry()
    registry.register("fake", fake_factory)

    engine = registry.create(
        "fake",
        {
            "score": 0.82,
        },
    )

    assert engine.name == "fake"
    assert engine.score == pytest.approx(0.82)


def test_rejects_duplicate_registration() -> None:
    registry = EvaluationEngineRegistry()
    registry.register("fake", fake_factory)

    with pytest.raises(
        PluginAlreadyRegisteredError,
        match="already registered",
    ):
        registry.register("fake", fake_factory)


def test_can_replace_registered_factory() -> None:
    registry = EvaluationEngineRegistry()
    registry.register("fake", fake_factory)

    def replacement_factory(
        config: Mapping[str, Any] | None = None,
    ) -> FakeEvaluationEngine:
        return FakeEvaluationEngine(score=0.25)

    registry.register(
        "fake",
        replacement_factory,
        replace=True,
    )

    engine = registry.create("fake")

    assert engine.score == pytest.approx(0.25)


def test_raises_for_unknown_engine() -> None:
    registry = EvaluationEngineRegistry()

    with pytest.raises(
        PluginNotFoundError,
        match="not registered",
    ):
        registry.create("missing")


def test_unregisters_engine() -> None:
    registry = EvaluationEngineRegistry()
    registry.register("fake", fake_factory)

    registry.unregister("fake")

    assert not registry.contains("fake")
    assert registry.names() == ()


def test_rejects_engine_with_wrong_name() -> None:
    registry = EvaluationEngineRegistry()

    def wrong_name_factory(
        config: Mapping[str, Any] | None = None,
    ) -> FakeEvaluationEngine:
        return FakeEvaluationEngine(name="different")

    registry.register("fake", wrong_name_factory)

    with pytest.raises(
        InvalidPluginError,
        match="registered as 'fake'",
    ):
        registry.create("fake")


def test_rejects_non_callable_factory() -> None:
    registry = EvaluationEngineRegistry()

    with pytest.raises(
        InvalidPluginError,
        match="must be callable",
    ):
        registry.register("fake", object())  # type: ignore[arg-type]