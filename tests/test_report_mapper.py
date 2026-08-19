from src.evaluation_models import EngineExecutionResult, MetricResult
from src.report_mapper import (
    map_engine_result,
    map_metric_result,
)


def test_map_metric_result_allows_only_public_runtime_options() -> None:
    metric = MetricResult(
        engine="builtin",
        metric_name="contains",
        score=1.0,
        threshold=1.0,
        passed=True,
        runtime_options={
            "include_reason": True,
            "governance_weight": 0.91,
            "internal_scoring_strategy": "proprietary-v4",
            "private_evidence_id": "EV-99182",
        },
    )

    public_metric = map_metric_result(metric)

    assert public_metric.runtime_options.include_reason is True

    assert public_metric.runtime_options.model_dump(
        mode="json",
        exclude_none=True,
    ) == {
               "include_reason": True,
           }


def test_map_engine_result_redacts_internal_error_details() -> None:
    engine_result = EngineExecutionResult(
        engine="private-engine",
        succeeded=False,
        error=(
            "Internal evaluator failed at "
            "C:\\private\\governance\\scorer.py"
        ),
    )

    public_result = map_engine_result(engine_result)

    assert public_result.error == "Evaluation engine failed."