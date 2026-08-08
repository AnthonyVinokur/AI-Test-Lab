from src.evaluation.deepeval_engine import DeepEvalEngine

from src.evaluation_engines import (
    AssertionEvaluationEngine,
    EvaluationEngine,
)


def create_engine(name: str) -> EvaluationEngine:
    """Create an evaluation engine by name."""

    normalized_name = name.strip().lower()

    engines: dict[str, type[EvaluationEngine]] = {
        "builtin": AssertionEvaluationEngine,
        "deepeval": DeepEvalEngine,
    }

    try:
        engine_class = engines[normalized_name]
    except KeyError as error:
        supported = ", ".join(sorted(engines))
        raise ValueError(
            f"Unknown evaluation engine: {name!r}. "
            f"Supported engines: {supported}."
        ) from error

    return engine_class()