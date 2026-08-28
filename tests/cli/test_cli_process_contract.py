from __future__ import annotations

import subprocess
import sys

from src.cli.exit_codes import CliExitCode


def test_real_cli_success_returns_success_exit_code() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "src.cli.app",
            "--list-evaluation-profiles",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == CliExitCode.SUCCESS
    assert "Available evaluation profiles:" in completed.stdout
    assert "default" in completed.stdout
    assert completed.stderr == ""

def test_real_cli_invalid_regression_invocation_returns_input_error() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "src.cli.app",
            "--regression-result-output",
            "results/regression.json",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == CliExitCode.INPUT_ERROR
    assert completed.stdout == ""
    assert (
        "--regression-baseline-report, --regression-baseline-provenance, "
        "and --regression-result-output must be supplied together"
        in completed.stderr
    )
