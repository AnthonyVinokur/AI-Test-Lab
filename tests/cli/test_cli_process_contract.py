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

def test_real_cli_dataset_validation_failure_returns_failure_exit_code(
    tmp_path,
) -> None:
    dataset_id = "invalid-dataset"
    dataset_storage = tmp_path / "datasets"
    dataset_storage.mkdir()

    dataset_file = dataset_storage / f"{dataset_id}.json"
    dataset_file.write_text(
        """
{
  "manifest": {
    "id": "invalid-dataset",
    "name": "Invalid validation dataset",
    "status": "active",
    "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-01-01T00:00:00Z",
    "latest_version": 1,
    "tags": []
  },
  "versions": [
    {
      "version": 1,
      "created_at": "2026-01-01T00:00:00Z",
      "created_by": "test",
      "change_summary": "Intentional invalid dataset",
      "entries": [],
      "checksum": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945"
    }
  ]
}
""".strip(),
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "src.cli.app",
            "--validate-dataset",
            dataset_id,
            "--dataset-storage",
            str(dataset_storage),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == CliExitCode.FAILURE
    assert "active_dataset_empty" in completed.stdout
    assert "Dataset validation failed." in completed.stdout
    assert completed.stderr == ""


def test_real_cli_report_write_failure_returns_infrastructure_error(
    tmp_path,
) -> None:
    prompts_path = tmp_path / "empty-prompts.json"
    prompts_path.write_text("[]", encoding="utf-8")

    # Deliberately use an existing directory as the JSON report path.
    # Opening a directory as a writable file must fail.
    invalid_report_path = tmp_path / "report-target"
    invalid_report_path.mkdir()

    html_report_path = tmp_path / "report.html"

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "src.cli.app",
            "--prompts",
            str(prompts_path),
            "--report",
            str(invalid_report_path),
            "--html-report",
            str(html_report_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == CliExitCode.INFRASTRUCTURE_ERROR
    assert "Infrastructure error:" in completed.stderr
    assert "Traceback" not in completed.stderr
    assert "JSON report:" not in completed.stdout
    assert "HTML report:" not in completed.stdout
