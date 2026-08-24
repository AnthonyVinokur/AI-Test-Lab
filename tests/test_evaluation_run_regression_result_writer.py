import json

from src.evaluation_run_regression_enforcement import (
    EvaluationRunRegressionEnforcement,
    EvaluationRunRegressionEnforcementDecision,
)
from src.evaluation_run_regression_result import (
    build_evaluation_run_regression_result,
)
from src.evaluation_run_regression_result_writer import (
    write_evaluation_run_regression_result_json,
)


def test_write_allow_result_json(tmp_path):
    enforcement = EvaluationRunRegressionEnforcement(
        decision=EvaluationRunRegressionEnforcementDecision.ALLOW
    )
    result = build_evaluation_run_regression_result(enforcement)
    output_path = tmp_path / "result.json"

    write_evaluation_run_regression_result_json(
        result,
        output_path,
    )

    assert output_path.read_text(
        encoding="utf-8"
    ) == '{"enforcement":"allow","exit_code":0}'


def test_write_block_result_json(tmp_path):
    enforcement = EvaluationRunRegressionEnforcement(
        decision=EvaluationRunRegressionEnforcementDecision.BLOCK
    )
    result = build_evaluation_run_regression_result(enforcement)
    output_path = tmp_path / "result.json"

    write_evaluation_run_regression_result_json(
        result,
        output_path,
    )

    assert output_path.read_text(
        encoding="utf-8"
    ) == '{"enforcement":"block","exit_code":1}'


def test_write_creates_missing_parent_directories(tmp_path):
    enforcement = EvaluationRunRegressionEnforcement(
        decision=EvaluationRunRegressionEnforcementDecision.ALLOW
    )
    result = build_evaluation_run_regression_result(enforcement)

    output_path = (
        tmp_path
        / "nested"
        / "regression"
        / "result.json"
    )

    write_evaluation_run_regression_result_json(
        result,
        output_path,
    )

    assert output_path.exists()
    assert output_path.is_file()


def test_write_overwrites_existing_file(tmp_path):
    output_path = tmp_path / "result.json"

    allow_enforcement = EvaluationRunRegressionEnforcement(
        decision=EvaluationRunRegressionEnforcementDecision.ALLOW
    )
    block_enforcement = EvaluationRunRegressionEnforcement(
        decision=EvaluationRunRegressionEnforcementDecision.BLOCK
    )

    allow_result = build_evaluation_run_regression_result(
        allow_enforcement
    )
    block_result = build_evaluation_run_regression_result(
        block_enforcement
    )

    write_evaluation_run_regression_result_json(
        allow_result,
        output_path,
    )
    write_evaluation_run_regression_result_json(
        block_result,
        output_path,
    )

    assert output_path.read_text(
        encoding="utf-8"
    ) == '{"enforcement":"block","exit_code":1}'


def test_written_file_contains_valid_public_json(tmp_path):
    enforcement = EvaluationRunRegressionEnforcement(
        decision=EvaluationRunRegressionEnforcementDecision.BLOCK
    )
    result = build_evaluation_run_regression_result(enforcement)

    output_path = tmp_path / "result.json"

    write_evaluation_run_regression_result_json(
        result,
        output_path,
    )

    decoded = json.loads(
        output_path.read_text(encoding="utf-8")
    )

    assert decoded == {
        "enforcement": "block",
        "exit_code": 1,
    }
