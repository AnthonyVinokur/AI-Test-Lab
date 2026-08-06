from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from src.evaluation_models import EvaluationRequest
from src.evaluation_plugins import EvaluationEngineRegistry
from src.integrations.deepeval import (
    DeepEvalEngine,
    create_deepeval_engine,
)


@dataclass
class FakeMetric:
    score: float = 0.88
    reason: str = "The response is relevant."

    def measure(self, test_case: Any) -> None:
        self.test_case = test_case

    def is_successful(self) -> bool:
        return True


def test_registry_creates_deepeval_engine() -> None:
    registry = EvaluationEngineRegistry()

    registry.register(
        "deepeval",
        create_deepeval_engine,
    )

    engine = registry.create(
        "deepeval",
        {
            "model": "judge-model",
            "include_reason": False,
        },
    )

    assert isinstance(engine, DeepEvalEngine)
    assert engine.name == "deepeval"
    assert engine.model == "judge-model"
    assert engine.include_reason is False


def test_registered_deepeval_engine_normalizes_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry = EvaluationEngineRegistry()
    registry.register("deepeval", create_deepeval_engine)

    engine = registry.create("deepeval")

    monkeypatch.setattr(
        engine,
        "_metric_creator",
        lambda *args, **kwargs: FakeMetric(),
    )

    request = EvaluationRequest(
        input="What is Python?",
        actual_output="Python is a programming language.",
        metrics=("answer_relevancy",),
        threshold=0.7,
    )

    results = engine.evaluate(request)

    assert len(results) == 1
    assert results[0].engine == "deepeval"
    assert results[0].metric_name == "answer_relevancy"
    assert results[0].score == pytest.approx(0.88)
    assert results[0].passed is True