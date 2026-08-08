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


def test_unknown_builtin_profile_raises_file_error():
    with pytest.raises(
        EvaluationConfigFileError,
        match="Evaluation profile does not exist",
    ):
        load_evaluation_profile("does-not-exist")