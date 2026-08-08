from src.integrations.deepeval import (
    DeepEvalEngine,
    create_deepeval_engine,
)


def test_creates_default_engine() -> None:
    engine = create_deepeval_engine()

    assert isinstance(engine, DeepEvalEngine)
    assert engine.model is None
    assert engine.include_reason is True


def test_creates_configured_engine() -> None:
    engine = create_deepeval_engine(
        {
            "model": "gpt-4.1-mini",
            "include_reason": False,
        }
    )

    assert isinstance(engine, DeepEvalEngine)
    assert engine.model == "gpt-4.1-mini"
    assert engine.include_reason is False


def test_ignores_unknown_configuration() -> None:
    engine = create_deepeval_engine(
        {
            "unknown": 123,
            "model": "judge-model",
        }
    )

    assert engine.model == "judge-model"