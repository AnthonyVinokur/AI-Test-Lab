import pytest

from src.evaluation_run_identity import (
    EvaluationRunIdentity,
    create_evaluation_run_identity,
)

@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("run_id", ""),
        ("model", ""),
        ("evaluation_profile", ""),
        ("dataset", ""),
    ],
)
def test_evaluation_run_identity_rejects_empty_values(field_name, value):
        kwargs = {"run_id": "run-001", "model": "llama3.1:latest", "evaluation_profile": "fast-ci",
                  "dataset": "smoke-tests", field_name: value}

        with pytest.raises(ValueError):
            EvaluationRunIdentity(**kwargs)


def test_evaluation_run_identity_rejects_whitespace_only_values():
    with pytest.raises(ValueError):
        EvaluationRunIdentity(
            run_id="   ",
            model="llama3.1:latest",
            evaluation_profile="fast-ci",
            dataset="smoke-tests",
        )


def test_evaluation_run_identity_preserves_public_run_metadata():
    identity = EvaluationRunIdentity(
        run_id="run-001",
        model="llama3.1:latest",
        evaluation_profile="fast-ci",
        dataset="smoke-tests",
    )

    assert identity.run_id == "run-001"
    assert identity.model == "llama3.1:latest"
    assert identity.evaluation_profile == "fast-ci"
    assert identity.dataset == "smoke-tests"


def test_evaluation_run_identity_distinguishes_different_runs():
    first = EvaluationRunIdentity(
        run_id="run-001",
        model="llama3.1:latest",
        evaluation_profile="fast-ci",
        dataset="smoke-tests",
    )

    second = EvaluationRunIdentity(
        run_id="run-002",
        model="llama3.1:latest",
        evaluation_profile="fast-ci",
        dataset="smoke-tests",
    )

    assert first != second


def test_evaluation_run_identity_is_immutable():
    identity = EvaluationRunIdentity(
        run_id="run-001",
        model="llama3.1:latest",
        evaluation_profile="fast-ci",
        dataset="smoke-tests",
    )

    try:
        identity.run_id = "run-999"
    except (AttributeError, TypeError):
        pass
    else:
        raise AssertionError("EvaluationRunIdentity must be immutable")


def test_evaluation_run_identity_serializes_public_metadata():
    identity = EvaluationRunIdentity(
        run_id="run-001",
        model="llama3.1:latest",
        evaluation_profile="fast-ci",
        dataset="smoke-tests",
    )

    assert identity.to_public_dict() == {
        "run_id": "run-001",
        "model": "llama3.1:latest",
        "evaluation_profile": "fast-ci",
        "dataset": "smoke-tests",
    }

def test_create_evaluation_run_identity_generates_run_id():
    identity = create_evaluation_run_identity(
        model="llama3.1:latest",
        evaluation_profile="fast-ci",
        dataset="smoke-tests",
    )

    assert identity.run_id
    assert identity.run_id.startswith("run-")
    assert identity.model == "llama3.1:latest"
    assert identity.evaluation_profile == "fast-ci"
    assert identity.dataset == "smoke-tests"
