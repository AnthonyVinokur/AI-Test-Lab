import pytest

from src.evaluation_config import (
    EvaluationConfigFileError,
    load_evaluation_profile,
)


@pytest.mark.parametrize(
    "profile_name",
    [
        "default",
        "fast-ci",
        "deep-quality",
        "rag",
        "enterprise",
    ],
)
def test_load_builtin_profile_by_name(profile_name):
    profile = load_evaluation_profile(profile_name)

    assert profile.name == profile_name


def test_unknown_builtin_profile_raises_helpful_error():
    with pytest.raises(
        EvaluationConfigFileError,
        match="Unknown evaluation profile 'does-not-exist'",
    ) as error:
        load_evaluation_profile("does-not-exist")

    message = str(error.value)

    assert "Available built-in profiles:" in message
    assert "default" in message
    assert "fast-ci" in message
    assert "enterprise" in message
    assert "YAML or JSON profile" in message

def test_missing_explicit_profile_path_raises_file_error():
    with pytest.raises(
        EvaluationConfigFileError,
        match="Evaluation profile does not exist",
    ):
        load_evaluation_profile("profiles/missing.yaml")