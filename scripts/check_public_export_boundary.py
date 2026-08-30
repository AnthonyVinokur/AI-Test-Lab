from __future__ import annotations

import ast
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

TRUSTED_SERIALIZATION_GATEWAYS = {
    Path("src/public_contract.py"),
    Path("src/internal_serialization.py"),
}

FORBIDDEN_EXPORT_METHODS = {
    "model_dump",
    "model_dump_json",
}

class PublicExportBoundaryScanError(RuntimeError):
    """Raised when production source cannot be inspected safely."""

@dataclass(frozen=True)
class ExportViolation:
    path: Path
    line: int
    column: int
    method: str

    def format(self) -> str:
        normalized_path = self.path.as_posix()

        return (
            f"{normalized_path}:{self.line}:{self.column}: "
            f"direct model serialization via {self.method}() "
            f"bypasses an approved serialization gateway"
        )


def repository_root() -> Path:
    completed = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        check=True,
        capture_output=True,
        text=True,
    )
    return Path(completed.stdout.strip()).resolve()


def production_python_files(root: Path) -> list[Path]:
    paths = list((root / "src").rglob("*.py"))

    paths.extend(
        path
        for path in root.glob("*.py")
        if path.is_file()
    )

    return sorted(
        paths,
        key=lambda path: path.relative_to(root).as_posix(),
    )

def is_production_python_path(path: Path) -> bool:
    if path.suffix != ".py":
        return False

    if not path.parts:
        return False

    top_level = path.parts[0]

    if top_level in {
        "tests",
        "scripts",
    }:
        return False

    if top_level == "src":
        return True

    # Root-level Python entry points such as main.py and dataset_cli.py
    # are executable production surfaces and remain protected.
    return len(path.parts) == 1


def inspect_source(
    source: str,
    *,
    path: Path,
) -> list[ExportViolation]:
    try:
        tree = ast.parse(
            source,
            filename=path.as_posix(),
        )
    except SyntaxError as exc:
        line = exc.lineno or 0

        raise PublicExportBoundaryScanError(
            f"{path.as_posix()}:{line}: "
            f"unable to parse production Python source: {exc.msg}"
        ) from exc

    violations: list[ExportViolation] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        if not isinstance(node.func, ast.Attribute):
            continue

        if node.func.attr not in FORBIDDEN_EXPORT_METHODS:
            continue

        violations.append(
            ExportViolation(
                path=path,
                line=node.lineno,
                column=node.col_offset + 1,
                method=node.func.attr,
            )
        )

    return violations


def inspect_file(
    path: Path,
    *,
    root: Path,
) -> list[ExportViolation]:
    relative_path = path.relative_to(root)

    if relative_path in TRUSTED_SERIALIZATION_GATEWAYS:
        return []

    try:
        source = path.read_text(
            encoding="utf-8",
            errors="replace",
        )
    except OSError as exc:
        raise PublicExportBoundaryScanError(
            f"{relative_path.as_posix()}: "
            "unable to read production Python source"
        ) from exc

    return inspect_source(
        source,
        path=relative_path,
    )


def scan_repository(root: Path) -> list[ExportViolation]:
    violations: list[ExportViolation] = []

    for path in production_python_files(root):
        relative_path = path.relative_to(root)

        violations.extend(
            inspect_file(
                path,
                root=root,
            )
        )

    return sorted(
        violations,
        key=lambda violation: (
            violation.path.as_posix(),
            violation.line,
            violation.column,
            violation.method,
        ),
    )


def main() -> int:
    try:
        root = repository_root()
        violations = scan_repository(root)
    except subprocess.CalledProcessError:
        print(
            "Public export boundary check: ERROR "
            "(not inside a Git repository)",
            file=sys.stderr,
        )
        return 2

    if violations:
        print(
            "Public export boundary check: FAIL",
            file=sys.stderr,
        )

        for violation in violations:
            print(
                f"  - {violation.format()}",
                file=sys.stderr,
            )

        return 1

    print("Public export boundary check: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
