from pathlib import Path

import pytest

from scripts.check_private_dependency_boundary import (
    DependencyViolation,
    PrivateDependencyBoundaryScanError,
    inspect_source,
    is_private_module,
    scan_repository,
)


def test_direct_private_import_is_rejected() -> None:
    violations = inspect_source(
        "import aitestlab_private\n",
        path=Path("src/example.py"),
    )

    assert len(violations) == 1
    assert violations[0].module == "aitestlab_private"


def test_private_submodule_import_is_rejected() -> None:
    violations = inspect_source(
        "import aitestlab_private.scoring\n",
        path=Path("src/example.py"),
    )

    assert len(violations) == 1
    assert violations[0].module == "aitestlab_private.scoring"


def test_from_private_package_is_rejected() -> None:
    violations = inspect_source(
        "from aitestlab_private import scoring\n",
        path=Path("src/example.py"),
    )

    assert len(violations) == 1
    assert violations[0].module == "aitestlab_private"


def test_from_private_submodule_is_rejected() -> None:
    violations = inspect_source(
        "from aitestlab_private.governance import PolicyEngine\n",
        path=Path("src/example.py"),
    )

    assert len(violations) == 1
    assert violations[0].module == "aitestlab_private.governance"


def test_similar_public_module_is_allowed() -> None:
    violations = inspect_source(
        "import aitestlab_public\n",
        path=Path("src/example.py"),
    )

    assert violations == []


def test_comments_and_strings_do_not_trigger() -> None:
    violations = inspect_source(
        (
            '# import aitestlab_private\n'
            'message = "aitestlab_private"\n'
        ),
        path=Path("src/example.py"),
    )

    assert violations == []


def test_private_module_classification() -> None:
    assert is_private_module("aitestlab_private")
    assert is_private_module("aitestlab_private.scoring")
    assert not is_private_module("aitestlab_private_tools")


def test_violation_format_is_deterministic() -> None:
    violation = DependencyViolation(
        path=Path("src/example.py"),
        line=4,
        column=1,
        module="aitestlab_private",
    )

    assert violation.format() == (
        "src/example.py:4:1: "
        "public production code imports "
        "private package 'aitestlab_private'"
    )


def test_invalid_production_python_fails_closed() -> None:
    with pytest.raises(
        PrivateDependencyBoundaryScanError,
        match="unable to parse production Python source",
    ):
        inspect_source(
            "def broken(:\n",
            path=Path("src/broken.py"),
        )


def test_scan_includes_untracked_production_file(
    tmp_path: Path,
) -> None:
    path = tmp_path / "src" / "new_module.py"
    path.parent.mkdir(parents=True)

    path.write_text(
        "import aitestlab_private\n",
        encoding="utf-8",
    )

    violations = scan_repository(tmp_path)

    assert len(violations) == 1
    assert violations[0].path == Path("src/new_module.py")


def test_current_repository_has_no_private_dependency() -> None:
    assert scan_repository(Path.cwd()) == []
