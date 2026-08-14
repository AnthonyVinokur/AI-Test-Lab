import pytest
from pydantic import ValidationError

from src.evaluation_models import EngineExecutionResult, MetricResult
from src.report_mapper import map_engine_result, map_metric_result
from src.report_schema import (
    ReportEngineExecutionResultV1,
    ReportMetricResultV1,
)


def test_public_report_schema_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        ReportEngineExecutionResultV1.model_validate(
            {
                "engine": "deepeval",
                "succeeded": True,
                "error": None,
                "internal_risk_weight": 0.42,
            }
        )


def test_public_metric_schema_is_versioned_contract_data_only() -> None:
    metric = ReportMetricResultV1(
        engine="builtin",
        metric_name="contains",
        score=1.0,
        threshold=1.0,
        passed=True,
        profile_name="fast-ci",
        profile_version="1.0",
        evaluator_model="test-judge",
    )

    assert set(metric.model_dump()) == {
        "engine",
        "metric_name",
        "score",
        "threshold",
        "passed",
        "reason",
        "runtime_options",
        "profile_name",
        "profile_version",
        "evaluator_model",
    }


def test_mapper_filters_unapproved_runtime_options() -> None:
    internal_metric = MetricResult(
        engine="builtin",
        metric_name="contains",
        score=1.0,
        threshold=1.0,
        passed=True,
        runtime_options={
            "include_reason": True,
            "internal_weighting_algorithm": "enterprise-v3",
            "internal_policy_id": "secret-policy-007",
        },
    )

    public_metric = map_metric_result(internal_metric)

    assert public_metric.runtime_options == {
        "include_reason": True,
    }
    assert "internal_weighting_algorithm" not in public_metric.runtime_options
    assert "internal_policy_id" not in public_metric.runtime_options


def test_mapper_normalizes_internal_engine_error_details() -> None:
    internal_result = EngineExecutionResult(
        engine="deepeval",
        succeeded=False,
        error=(
            r"Failed loading C:\\internal\\enterprise\\governance_engine.py "
            "using api_key=super-secret"
        ),
    )

    public_result = map_engine_result(internal_result)

    assert public_result.error == "Evaluation engine failed."
    assert "governance_engine.py" not in public_result.error
    assert "super-secret" not in public_result.error
