from pathlib import Path

from scripts.check_repository_boundary import (
    content_violations,
    path_violations,
)


def test_empty_env_example_is_allowed(tmp_path: Path) -> None:
    path = tmp_path / ".env.example"
    path.write_text(
        "GEMINI_API_KEY=\n"
        "ANTHROPIC_API_KEY=\n"
        "OPENAI_API_KEY=\n",
        encoding="utf-8",
    )

    assert path_violations(path, tmp_path) == []
    assert content_violations(path) == []


def test_real_env_file_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / ".env"

    violations = path_violations(path, tmp_path)

    assert any(
        "forbidden sensitive filename" in violation
        for violation in violations
    )


def test_proprietary_directory_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "proprietary" / "scoring.py"

    violations = path_violations(path, tmp_path)

    assert any(
        "forbidden private directory" in violation
        for violation in violations
    )


def test_private_key_file_type_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "server.pem"

    violations = path_violations(path, tmp_path)

    assert any(
        "forbidden sensitive file type" in violation
        for violation in violations
    )


def test_openai_key_pattern_is_detected(tmp_path: Path) -> None:
    path = tmp_path / "config.txt"
    fake_key = "sk-" + ("A" * 24)

    path.write_text(
        f"token={fake_key}",
        encoding="utf-8",
    )

    violations = content_violations(path)

    assert any(
        "OpenAI API key" in violation
        for violation in violations
    )


def test_anthropic_key_pattern_is_detected(tmp_path: Path) -> None:
    path = tmp_path / "config.txt"
    fake_key = "sk-" + "ant-" + ("A" * 24)

    path.write_text(
        f"token={fake_key}",
        encoding="utf-8",
    )

    violations = content_violations(path)

    assert any(
        "Anthropic API key" in violation
        for violation in violations
    )


def test_populated_provider_assignment_is_detected(
    tmp_path: Path,
) -> None:
    path = tmp_path / "config.txt"
    fake_value = "x" * 24

    path.write_text(
        "OPENAI_API_KEY=" + fake_value,
        encoding="utf-8",
    )

    violations = content_violations(path)

    assert any(
        "populated provider API-key assignment" in violation
        for violation in violations
    )


def test_empty_provider_assignments_do_not_cross_lines(
    tmp_path: Path,
) -> None:
    path = tmp_path / ".env.example"

    path.write_text(
        "GEMINI_API_KEY=\n"
        "ANTHROPIC_API_KEY=\n"
        "OPENAI_API_KEY=\n",
        encoding="utf-8",
    )

    assert content_violations(path) == []


def test_private_key_content_is_detected(tmp_path: Path) -> None:
    path = tmp_path / "example.txt"
    marker = "-----BEGIN " + "PRIVATE KEY-----"

    path.write_text(
        marker,
        encoding="utf-8",
    )

    violations = content_violations(path)

    assert any(
        "private key" in violation
        for violation in violations
    )


def test_variable_name_documentation_is_safe(tmp_path: Path) -> None:
    path = tmp_path / "README.md"

    path.write_text(
        "Configure OPENAI_API_KEY through your environment.",
        encoding="utf-8",
    )

    assert content_violations(path) == []

def test_allowed_filename_inside_private_directory_is_rejected(
    tmp_path: Path,
) -> None:
    path = tmp_path / "proprietary" / ".env.example"

    violations = path_violations(path, tmp_path)

    assert any(
        "forbidden private directory" in violation
        for violation in violations
    )
