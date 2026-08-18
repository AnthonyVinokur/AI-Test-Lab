from __future__ import annotations

import json

from src.evaluation_models import EngineExecutionResult, MetricResult
from src.json_reporter import JsonReporter
from src.models import AssertionType, EvaluationStatus, TestResult as T_R
from src.report_consumer import consume_report
from src.report_contract_validator import validate_report_payload


def test_generated_public_report_can_be_consumed_end_to_end(
    tmp_path,
) -> None:
    result = T_R(
        test_id="contract-e2e-001",
        name="Public contract end-to-end test",
        category="contract",
        prompt="Say hello.",
        provider="ollama",
        model="llama3.1",
        estimated_cost_usd=0.0,
        actual_response="Hello!",
        passed=True,
        status=EvaluationStatus.PASS,
        assertion_type=AssertionType.CONTAINS,
        expected="Hello",
        reason="The response contains the expected text.",
        evaluation_results=[
            MetricResult(
                engine="builtin",
                metric_name="contains",
                score=1.0,
                threshold=1.0,
                passed=True,
                reason="Passed.",
                runtime_options={
                    "include_reason": True,
                    "internal_scoring_strategy": "proprietary-v5",
                    "private_evidence_id": "EV-1122",
                },
                profile_name="fast-ci",
                profile_version="1.0",
                evaluator_model="test-judge",
            )
        ],
        engine_results=[
            EngineExecutionResult(
                engine="deepeval",
                succeeded=False,
                error=(
                    "Internal evaluator failed at "
                    "C:\\private\\governance\\engine.py"
                ),
            )
        ],
        response_time_seconds=0.25,
    )

    report_path = tmp_path / "generated-report.json"

    JsonReporter(report_path).write([result])

    payload = json.loads(
        report_path.read_text(encoding="utf-8")
    )

    validate_report_payload(payload)

    consumption = consume_report(report_path)

    assert consumption.report.schema_version == "1.0"

    assert consumption.report.results[0].test_id == (
        "contract-e2e-001"
    )

    assert consumption.summary.total == 1
    assert consumption.summary.passed == 1
    assert consumption.summary.failed == 0
    assert consumption.summary.errors == 0

    assert consumption.decision.total == 1
    assert consumption.decision.passed == 1

    assert (
        consumption.decision.status
        == consumption.assessment.status
    )

    serialized_report = json.dumps(payload)

    assert "internal_scoring_strategy" not in serialized_report
    assert "private_evidence_id" not in serialized_report
    assert "engine.py" not in serialized_report
    assert "private\\governance" not in serialized_report

    runtime_options = (
        payload["results"][0]
        ["evaluation_results"][0]
        ["runtime_options"]
    )

    assert runtime_options == {
        "include_reason": True,
    }

    engine_result = (
        payload["results"][0]
        ["engine_results"][0]
    )

    assert engine_result["error"] == (
        "Evaluation engine failed."
    )