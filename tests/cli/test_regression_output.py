from pathlib import Path

from src.cli import regression_output
from src.evaluation_run_regression_enforcement import (
    EvaluationRunRegressionEnforcement,
    EvaluationRunRegressionEnforcementDecision,
)
from src.evaluation_run_regression_result import (
    EvaluationRunRegressionResult,
    build_evaluation_run_regression_result,
)


def _build_result(
    decision: EvaluationRunRegressionEnforcementDecision,
) -> EvaluationRunRegressionResult:
    enforcement = EvaluationRunRegressionEnforcement(
        decision=decision,
    )
    return build_evaluation_run_regression_result(enforcement)


def test_cli_regression_output_delegates_approved_result_and_path(
    monkeypatch,
):
    result = _build_result(
        EvaluationRunRegressionEnforcementDecision.ALLOW
    )
    output_path = Path("results/regression-result.json")
    calls = []

    def capture_writer(received_result, received_path):
        calls.append((received_result, received_path))

    monkeypatch.setattr(
        regression_output,
        "write_evaluation_run_regression_result_json",
        capture_writer,
    )

    regression_output.write_cli_regression_result(
        result,
        output_path,
    )

    assert calls == [(result, output_path)]


def test_cli_regression_output_writes_exact_allow_json(tmp_path):
    result = _build_result(
        EvaluationRunRegressionEnforcementDecision.ALLOW
    )
    output_path = tmp_path / "allow.json"

    regression_output.write_cli_regression_result(
        result,
        output_path,
    )

    assert output_path.read_text(
        encoding="utf-8"
    ) == '{"enforcement":"allow","exit_code":0}'


def test_cli_regression_output_writes_exact_block_json(tmp_path):
    result = _build_result(
        EvaluationRunRegressionEnforcementDecision.BLOCK
    )
    output_path = tmp_path / "nested" / "block.json"

    regression_output.write_cli_regression_result(
        result,
        output_path,
    )

    assert output_path.read_text(
        encoding="utf-8"
    ) == '{"enforcement":"block","exit_code":1}'
