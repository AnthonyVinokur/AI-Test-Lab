from __future__ import annotations

import subprocess
import sys

import pytest

from src.cli.exit_codes import CliExitCode


@pytest.mark.parametrize(
    ("exit_code", "expected"),
    [
        (CliExitCode.SUCCESS, 0),
        (CliExitCode.FAILURE, 1),
        (CliExitCode.INPUT_ERROR, 2),
        (CliExitCode.INFRASTRUCTURE_ERROR, 3),
    ],
)
def test_cli_exit_codes_cross_python_process_boundary(
    exit_code: CliExitCode,
    expected: int,
) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from src.cli.exit_codes import CliExitCode; "
                f"raise SystemExit(CliExitCode({int(exit_code)}))"
            ),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == expected
