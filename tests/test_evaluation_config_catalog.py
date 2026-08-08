from pathlib import Path

from src.evaluation_config.catalog import (
    list_profiles,
    profile_exists,
    resolve_profile_path,
)


def test_list_profiles_returns_builtin_catalog():
    profiles = list_profiles()

    assert profiles == [
        "deep-quality",
        "default",
        "enterprise",
        "fast-ci",
        "rag",
    ]


def test_profile_exists_returns_true_for_builtin_profile():
    assert profile_exists("default") is True
    assert profile_exists("rag") is True


def test_profile_exists_returns_false_for_unknown_profile():
    assert profile_exists("does-not-exist") is False


def test_resolve_builtin_profile_name():
    path = resolve_profile_path("fast-ci")

    assert path.name == "fast-ci.yaml"
    assert path.is_file()


def test_resolve_existing_explicit_path(tmp_path):
    profile_path = tmp_path / "custom.yaml"
    profile_path.write_text("name: custom", encoding="utf-8")

    resolved = resolve_profile_path(profile_path)

    assert resolved == profile_path


def test_unknown_profile_is_preserved():
    resolved = resolve_profile_path("does-not-exist")

    assert resolved == Path("does-not-exist")