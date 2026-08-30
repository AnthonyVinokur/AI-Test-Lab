from __future__ import annotations

import ast
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


PRIVATE_PACKAGE = "aitestlab_private"


class PrivateDependencyBoundaryScanError(RuntimeError):
    """Raised when production source cannot be inspected safely."""


@dataclass(frozen=True)
class DependencyViolation:
    path: Path
    line: int
    column: int
    module: str

    def format(self) -> str:
        return (
            f"{self.path.as_posix()}:{self.line}:{self.column}: "
            f"public production code imports private package "
            f"{self.module!r}"
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


def is_private_module(module: str) -> bool:
    return (
        module == PRIVATE_PACKAGE
        or module.startswith(f"{PRIVATE_PACKAGE}.")
    )


def inspect_source(
    source: str,
    *,
    path: Path,
) -> list[DependencyViolation]:
    try:
        tree = ast.parse(
            source,
            filename=path.as_posix(),
        )
    except SyntaxError as exc:
        line = exc.lineno or 0

        raise PrivateDependencyBoundaryScanError(
            f"{path.as_posix()}:{line}: "
            "unable to parse production Python source: "
            f"{exc.msg}"
        ) from exc

    violations: list[DependencyViolation] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if not is_private_module(alias.name):
                    continue

                violations.append(
                    DependencyViolation(
                        path=path,
                        line=node.lineno,
                        column=node.col_offset + 1,
                        module=alias.name,
                    )
                )

        elif isinstance(node, ast.ImportFrom):
            module = node.module

            if module is None or not is_private_module(module):
                continue

            violations.append(
                DependencyViolation(
                    path=path,
                    line=node.lineno,
                    column=node.col_offset + 1,
                    module=module,
                )
            )

    return violations


def inspect_file(
    path: Path,
    *,
    root: Path,
) -> list[DependencyViolation]:
    relative_path = path.relative_to(root)

    try:
        source = path.read_text(
            encoding="utf-8",
            errors="replace",
        )
    except OSError as exc:
        raise PrivateDependencyBoundaryScanError(
            f"{relative_path.as_posix()}: "
            "unable to read production Python source"
        ) from exc

    return inspect_source(
        source,
        path=relative_path,
    )


def scan_repository(root: Path) -> list[DependencyViolation]:
    violations: list[DependencyViolation] = []

    for path in production_python_files(root):
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
            violation.module,
        ),
    )


def main() -> int:
    try:
        root = repository_root()
        violations = scan_repository(root)
    except subprocess.CalledProcessError:
        print(
            "Private dependency boundary check: "
            "ERROR (not inside a Git repository)",
            file=sys.stderr,
        )
        return 2
    except PrivateDependencyBoundaryScanError as exc:
        print(
            "Private dependency boundary check: ERROR",
            file=sys.stderr,
        )
        print(
            f"  - {exc}",
            file=sys.stderr,
        )
        return 2

    if violations:
        print(
            "Private dependency boundary check: FAIL",
            file=sys.stderr,
        )

        for violation in violations:
            print(
                f"  - {violation.format()}",
                file=sys.stderr,
            )

        return 1

    print("Private dependency boundary check: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
