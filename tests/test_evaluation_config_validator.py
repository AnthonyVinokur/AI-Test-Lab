import pytest

from src.evaluation_config import (
    EngineConfig,
    EvaluationConfigValidationError,
    EvaluationProfile,
    MetricConfig,
    validate_registered_engines,
    validate_supported_metrics,
)


def test_registered_engine_validation_passes():
    profile = EvaluationProfile(
        name="valid",
        engines=[
            EngineConfig(
                name="deepeval",
                enabled=True,
            )
        ],
    )

    validate_registered_engines(
        profile,
        ["deepeval"],
    )


def test_registered_engine_validation_rejects_unknown_engine():
    profile = EvaluationProfile(
        name="invalid",
        engines=[
            EngineConfig(
                name="unknown",
                enabled=True,
            )
        ],
    )

    with pytest.raises(
        EvaluationConfigValidationError,
        match="unregistered engine",
    ):
        validate_registered_engines(
            profile,
            ["deepeval"],
        )


def test_supported_metric_validation_passes():
    profile = EvaluationProfile(
        name="valid-metrics",
        engines=[
            EngineConfig(
                name="deepeval",
                metrics=[
                    MetricConfig(
                        name="answer_relevancy",
                    ),
                    MetricConfig(
                        name="faithfulness",
                    ),
                ],
            )
        ],
    )

    validate_supported_metrics(
        profile,
        {
            "deepeval": [
                "answer_relevancy",
                "faithfulness",
                "hallucination",
            ]
        },
    )


def test_supported_metric_validation_rejects_unknown_metric():
    profile = EvaluationProfile(
        name="invalid-metric",
        engines=[
            EngineConfig(
                name="deepeval",
                metrics=[
                    MetricConfig(
                        name="totally_fake_metric",
                    )
                ],
            )
        ],
    )

    with pytest.raises(
        EvaluationConfigValidationError,
        match="totally_fake_metric",
    ) as error:
        validate_supported_metrics(
            profile,
            {
                "deepeval": [
                    "answer_relevancy",
                    "faithfulness",
                    "hallucination",
                ]
            },
        )

    message = str(error.value)

    assert "deepeval" in message
    assert "Supported metrics:" in message
    assert "answer_relevancy" in message