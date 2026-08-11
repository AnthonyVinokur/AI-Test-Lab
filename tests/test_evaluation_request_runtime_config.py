import pytest

from src.evaluation_models import EvaluationRequest


def make_request(**overrides) -> EvaluationRequest:
    values = {
        "input": "What is Python?",
        "actual_output": "Python is a programming language.",
        "metrics": ("answer_relevancy",),
        "threshold": 0.7,
    }
    values.update(overrides)
    return EvaluationRequest(**values)


def test_threshold_for_uses_metric_override() -> None:
    request = make_request(
        metric_thresholds={"answer_relevancy": 0.85},
    )

    assert request.threshold_for("answer_relevancy") == pytest.approx(0.85)


def test_threshold_for_falls_back_to_shared_threshold() -> None:
    request = make_request()

    assert request.threshold_for("answer_relevancy") == pytest.approx(0.7)


def test_runtime_config_lookup_normalizes_metric_name() -> None:
    request = make_request(
        metric_thresholds={"ANSWER_RELEVANCY": 0.82},
        metric_options={
            "ANSWER_RELEVANCY": {"include_reason": False},
        },
    )

    assert request.threshold_for(" answer_relevancy ") == pytest.approx(0.82)
    assert request.options_for(" answer_relevancy ") == {
        "include_reason": False,
    }


def test_options_for_returns_defensive_copy() -> None:
    request = make_request(
        metric_options={
            "answer_relevancy": {"include_reason": False},
        },
    )

    options = request.options_for("answer_relevancy")
    options["include_reason"] = True

    assert request.metric_options["answer_relevancy"] == {
        "include_reason": False,
    }


def test_threshold_override_must_target_selected_metric() -> None:
    with pytest.raises(
        ValueError,
        match="threshold override configured for unselected",
    ):
        make_request(
            metric_thresholds={"faithfulness": 0.8},
        )


def test_runtime_options_must_target_selected_metric() -> None:
    with pytest.raises(
        ValueError,
        match="runtime options configured for unselected",
    ):
        make_request(
            metric_options={
                "faithfulness": {"include_reason": True},
            },
        )


def test_request_can_carry_profile_provenance() -> None:
    request = make_request(
        profile_name="enterprise",
        profile_version="1.4",
    )

    assert request.profile_name == "enterprise"
    assert request.profile_version == "1.4"
