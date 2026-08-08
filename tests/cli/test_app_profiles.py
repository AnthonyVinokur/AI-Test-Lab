from src.cli.app import main


def test_list_evaluation_profiles_returns_success(
    capsys,
) -> None:
    exit_code = main(["--list-evaluation-profiles"])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Available evaluation profiles:" in captured.out
    assert "deep-quality" in captured.out
    assert "default" in captured.out
    assert "enterprise" in captured.out
    assert "fast-ci" in captured.out
    assert "rag" in captured.out


def test_list_evaluation_profiles_does_not_write_errors(
    capsys,
) -> None:
    exit_code = main(["--list-evaluation-profiles"])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.err == ""

def test_unknown_profile_returns_input_error(
    capsys,
) -> None:
    exit_code = main(
        ["--evaluation-profile", "does-not-exist"]
    )

    captured = capsys.readouterr()

    assert exit_code == 2
    assert "Unknown evaluation profile" in captured.err
    assert "does-not-exist" in captured.err
    assert "Available built-in profiles:" in captured.err

def test_unknown_profile_fails_before_loading_test_cases(
    monkeypatch,
    capsys,
) -> None:
    def fail_if_called(_args):
        raise AssertionError(
            "Test cases should not be loaded for an invalid profile."
        )

    monkeypatch.setattr(
        "src.cli.app.load_test_cases",
        fail_if_called,
    )

    exit_code = main(
        ["--evaluation-profile", "does-not-exist"]
    )

    captured = capsys.readouterr()

    assert exit_code == 2
    assert "Unknown evaluation profile" in captured.err

def test_invalid_profile_metric_fails_before_loading_test_cases(
    tmp_path,
    monkeypatch,
    capsys,
) -> None:
    profile_path = tmp_path / "invalid-metric.yaml"

    profile_path.write_text(
        """
name: invalid-metric
version: "1.0"

engines:
  - name: deepeval
    enabled: true
    metrics:
      - name: totally_fake_metric
        threshold: 0.7
""".strip(),
        encoding="utf-8",
    )

    def fail_if_called(_args):
        raise AssertionError(
            "Test cases should not be loaded for an invalid profile."
        )

    monkeypatch.setattr(
        "src.cli.app.load_test_cases",
        fail_if_called,
    )

    exit_code = main(
        [
            "--evaluation-profile",
            str(profile_path),
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 2
    assert "totally_fake_metric" in captured.err
    assert "Supported metrics:" in captured.err