from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


FORBIDDEN_DIRECTORIES = {
    "secrets",
    "credentials",
    "private",
    "proprietary",
    "enterprise-private",
    "internal-private",
}

FORBIDDEN_FILENAMES = {
    ".env",
    "credentials.json",
    "service-account.json",
    "service_account.json",
}

ALLOWED_FILENAMES = {
    ".env.example",
}

FORBIDDEN_SUFFIXES = {
    ".pem",
    ".key",
    ".p12",
    ".pfx",
}

SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "private key",
        re.compile(
            r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"
        ),
    ),
    (
        "OpenAI API key",
        re.compile(
            r"\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{20,}\b"
        ),
    ),
    (
        "Anthropic API key",
        re.compile(
            r"\bsk-ant-[A-Za-z0-9_-]{20,}\b"
        ),
    ),
    (
        "Google API key",
        re.compile(
            r"\bAIza[0-9A-Za-z_-]{30,}\b"
        ),
    ),
    (
        "GitHub token",
        re.compile(
            r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"
        ),
    ),
)

PROVIDER_ASSIGNMENT_PATTERN = re.compile(
    r"""(?im)^[ \t]*
    (?:OPENAI_API_KEY|ANTHROPIC_API_KEY|GEMINI_API_KEY)
    [ \t]*=[ \t]*
    ["']?
    ([^\s"'#]{16,})
    """,
    re.VERBOSE,
)


def repository_root() -> Path:
    completed = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        check=True,
        capture_output=True,
        text=True,
    )
    return Path(completed.stdout.strip()).resolve()


def tracked_files(root: Path) -> list[Path]:
    completed = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=root,
        check=True,
        capture_output=True,
    )

    paths = completed.stdout.decode(
        "utf-8",
        errors="surrogateescape",
    ).split("\0")

    return [
        root / relative_path
        for relative_path in paths
        if relative_path
    ]


def path_violations(path: Path, root: Path) -> list[str]:
    relative = path.relative_to(root)
    violations: list[str] = []

    allowed_filename = relative.name.lower() in ALLOWED_FILENAMES

    lowered_parts = {part.lower() for part in relative.parts}

    forbidden_parts = lowered_parts & FORBIDDEN_DIRECTORIES
    if forbidden_parts:
        violations.append(
            "forbidden private directory: "
            + ", ".join(sorted(forbidden_parts))
        )

    if (
        not allowed_filename
        and relative.name.lower() in FORBIDDEN_FILENAMES
    ):
        violations.append(
            f"forbidden sensitive filename: {relative.name}"
        )

    if (
        not allowed_filename
        and relative.suffix.lower() in FORBIDDEN_SUFFIXES
    ):
        violations.append(
            f"forbidden sensitive file type: {relative.suffix}"
        )

    return violations


def content_violations(path: Path) -> list[str]:
    try:
        content = path.read_text(
            encoding="utf-8",
            errors="replace",
        )
    except OSError as exc:
        return [f"could not inspect file: {exc}"]

    violations: list[str] = []

    for description, pattern in SECRET_PATTERNS:
        if pattern.search(content):
            violations.append(
                f"possible {description} detected"
            )

    if PROVIDER_ASSIGNMENT_PATTERN.search(content):
        violations.append(
            "possible populated provider API-key assignment detected"
        )

    return violations


def scan_repository(root: Path) -> list[str]:
    violations: list[str] = []

    for path in tracked_files(root):
        relative = path.relative_to(root)

        for violation in path_violations(path, root):
            violations.append(f"{relative}: {violation}")

        if path.is_file():
            for violation in content_violations(path):
                violations.append(f"{relative}: {violation}")

    return violations


def main() -> int:
    try:
        root = repository_root()
        violations = scan_repository(root)
    except subprocess.CalledProcessError:
        print(
            "Repository boundary check: ERROR "
            "(not inside a Git repository)",
            file=sys.stderr,
        )
        return 2

    if violations:
        print("Repository boundary check: FAIL", file=sys.stderr)

        for violation in violations:
            print(f"  - {violation}", file=sys.stderr)

        return 1

    print("Repository boundary check: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())