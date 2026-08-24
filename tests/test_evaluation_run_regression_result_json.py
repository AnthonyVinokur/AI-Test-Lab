import json

from src.evaluation_run_regression_enforcement import (
    EvaluationRunRegressionEnforcement,
    EvaluationRunRegressionEnforcementDecision,
)
from src.evaluation_run_regression_result import (
    build_evaluation_run_regression_result,
)
from src.evaluation_run_regression_result_json import (
    encode_evaluation_run_regression_result_json,
)


def test_encode_allow_result_as_json():
    enforcement = EvaluationRunRegressionEnforcement(
        decision=EvaluationRunRegressionEnforcementDecision.ALLOW
    )
    result = build_evaluation_run_regression_result(enforcement)

    encoded = encode_evaluation_run_regression_result_json(result)

    assert encoded == '{"enforcement":"allow","exit_code":0}'


def test_encode_block_result_as_json():
    enforcement = EvaluationRunRegressionEnforcement(
        decision=EvaluationRunRegressionEnforcementDecision.BLOCK
    )
    result = build_evaluation_run_regression_result(enforcement)

    encoded = encode_evaluation_run_regression_result_json(result)

    assert encoded == '{"enforcement":"block","exit_code":1}'


def test_json_encoding_is_deterministic():
    enforcement = EvaluationRunRegressionEnforcement(
        decision=EvaluationRunRegressionEnforcementDecision.ALLOW
    )
    result = build_evaluation_run_regression_result(enforcement)

    first = encode_evaluation_run_regression_result_json(result)
    second = encode_evaluation_run_regression_result_json(result)

    assert first == second


def test_encoded_json_is_valid_json():
    enforcement = EvaluationRunRegressionEnforcement(
        decision=EvaluationRunRegressionEnforcementDecision.BLOCK
    )
    result = build_evaluation_run_regression_result(enforcement)

    encoded = encode_evaluation_run_regression_result_json(result)

    assert json.loads(encoded) == {
        "enforcement": "block",
        "exit_code": 1,
    }
