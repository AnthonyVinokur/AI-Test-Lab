from src.evaluation_run_regression_enforcement import (
    EvaluationRunRegressionEnforcement,
    EvaluationRunRegressionEnforcementDecision,
)
from src.evaluation_run_regression_result import (
    build_evaluation_run_regression_result,
)
from src.evaluation_run_regression_result_serializer import (
    serialize_evaluation_run_regression_result,
)


def test_serialize_allow_result():
    enforcement = EvaluationRunRegressionEnforcement(
        decision=EvaluationRunRegressionEnforcementDecision.ALLOW
    )
    result = build_evaluation_run_regression_result(enforcement)

    serialized = serialize_evaluation_run_regression_result(result)

    assert serialized == {
        "enforcement": "allow",
        "exit_code": 0,
    }


def test_serialize_block_result():
    enforcement = EvaluationRunRegressionEnforcement(
        decision=EvaluationRunRegressionEnforcementDecision.BLOCK
    )
    result = build_evaluation_run_regression_result(enforcement)

    serialized = serialize_evaluation_run_regression_result(result)

    assert serialized == {
        "enforcement": "block",
        "exit_code": 1,
    }


def test_serialization_is_deterministic():
    enforcement = EvaluationRunRegressionEnforcement(
        decision=EvaluationRunRegressionEnforcementDecision.ALLOW
    )
    result = build_evaluation_run_regression_result(enforcement)

    first = serialize_evaluation_run_regression_result(result)
    second = serialize_evaluation_run_regression_result(result)

    assert first == second


def test_serialization_preserves_original_result():
    enforcement = EvaluationRunRegressionEnforcement(
        decision=EvaluationRunRegressionEnforcementDecision.BLOCK
    )
    result = build_evaluation_run_regression_result(enforcement)

    serialize_evaluation_run_regression_result(result)

    assert result.enforcement is enforcement
    assert result.exit_code.code == 1
