import pytest

from src.models import (
    AssertionType,
    EvaluationStatus,
    TestResult as ResultModel
)
from src.report_analytics import (
    build_model_summaries,
    get_fastest_model,
    get_highest_scoring_model,
)


def create_result(
    *,
    model: str,
    status: EvaluationStatus,
    response_time: float,
    generation_speed: float,
    output_tokens: int,
) -> ResultModel:
    return ResultModel(
        test_id="test-001",
        name="Example test",
        category="functional",
        prompt="Say hello",
        model=model,
        actual_response="Hello",
        passed=status == EvaluationStatus.PASS,
        status=status,
        assertion_type=AssertionType.CONTAINS,
        expected="Hello",
        reason="Test result",
        response_time_seconds=response_time,
        prompt_tokens=10,
        output_tokens=output_tokens,
        prompt_latency_seconds=0.5,
        generation_latency_seconds=1.0,
        model_load_seconds=0.2,
        prompt_tokens_per_second=20.0,
        generation_tokens_per_second=generation_speed,
    )


def test_build_model_summaries_groups_results_by_model() -> None:
    results = [
        create_result(
            model="model-a",
            status=EvaluationStatus.PASS,
            response_time=2.0,
            generation_speed=10.0,
            output_tokens=20,
        ),
        create_result(
            model="model-a",
            status=EvaluationStatus.FAIL,
            response_time=4.0,
            generation_speed=6.0,
            output_tokens=40,
        ),
        create_result(
            model="model-b",
            status=EvaluationStatus.PASS,
            response_time=1.0,
            generation_speed=12.0,
            output_tokens=10,
        ),
    ]

    summaries = build_model_summaries(results)

    assert len(summaries) == 2

    model_a = next(
        summary
        for summary in summaries
        if summary.model == "model-a"
    )

    assert model_a.passed == 1
    assert model_a.failed == 1
    assert model_a.errors == 0
    assert model_a.total == 2
    assert model_a.pass_rate_percent == 50.0
    assert model_a.average_response_time_seconds == 3.0
    assert model_a.average_generation_tokens_per_second == 8.0
    assert model_a.average_output_tokens == 30.0


def test_fastest_model_uses_average_response_time() -> None:
    results = [
        create_result(
            model="slow-model",
            status=EvaluationStatus.PASS,
            response_time=5.0,
            generation_speed=5.0,
            output_tokens=10,
        ),
        create_result(
            model="fast-model",
            status=EvaluationStatus.PASS,
            response_time=1.0,
            generation_speed=10.0,
            output_tokens=10,
        ),
    ]

    summaries = build_model_summaries(results)
    fastest = get_fastest_model(summaries)

    assert fastest is not None
    assert fastest.model == "fast-model"


def test_highest_scoring_model_uses_pass_rate() -> None:
    results = [
        create_result(
            model="model-a",
            status=EvaluationStatus.FAIL,
            response_time=1.0,
            generation_speed=10.0,
            output_tokens=10,
        ),
        create_result(
            model="model-b",
            status=EvaluationStatus.PASS,
            response_time=4.0,
            generation_speed=5.0,
            output_tokens=10,
        ),
    ]

    summaries = build_model_summaries(results)
    winner = get_highest_scoring_model(summaries)

    assert winner is not None
    assert winner.model == "model-b"


def test_empty_results_return_empty_summaries() -> None:
    assert build_model_summaries([]) == []
    assert get_fastest_model([]) is None
    assert get_highest_scoring_model([]) is None