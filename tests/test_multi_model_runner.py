from src.evaluation_engines import AssertionEvaluationEngine
from src.multi_model_runner import MultiModelRunner


def test_multi_model_runner_requires_at_least_one_model() -> None:
    try:
        MultiModelRunner(
            model_names=[],
            evaluation_engine=AssertionEvaluationEngine(),
        )
    except ValueError as error:
        assert str(error) == "At least one model name is required."
    else:
        raise AssertionError("Expected ValueError")