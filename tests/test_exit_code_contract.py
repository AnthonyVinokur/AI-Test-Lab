from pathlib import Path
import re


CLI_ROOT = Path("src/cli")

RAW_PROCESS_EXIT_PATTERN = re.compile(
    r"return\s+[0-3]\b|SystemExit\([0-3]\)"
)


def test_cli_does_not_use_raw_process_exit_codes() -> None:
    violations: list[str] = []

    for path in CLI_ROOT.rglob("*.py"):
        source = path.read_text(encoding="utf-8")

        for line_number, line in enumerate(source.splitlines(), start=1):
            if RAW_PROCESS_EXIT_PATTERN.search(line):
                violations.append(
                    f"{path}:{line_number}: {line.strip()}"
                )

    assert not violations, (
        "CLI process exit codes must use CliExitCode:\n"
        + "\n".join(violations)
    )
