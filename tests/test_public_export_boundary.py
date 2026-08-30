from pathlib import Path

from scripts.check_public_export_boundary import (
    inspect_file,
    inspect_source,
    is_production_python_path,
    scan_repository,
    PublicExportBoundaryScanError,
)

import pytest

def test_direct_model_dump_is_rejected() -> None:
    violations = inspect_source(
        "payload = result.model_dump()\n",
        path=Path("src/example.py"),
    )

    assert len(violations) == 1
    assert violations[0].method == "model_dump"
    assert violations[0].line == 1


def test_direct_json_mode_model_dump_is_rejected() -> None:
    violations = inspect_source(
        'payload = result.model_dump(mode="json")\n',
        path=Path("src/example.py"),
    )

    assert len(violations) == 1
    assert violations[0].method == "model_dump"


def test_model_dump_json_is_rejected() -> None:
    violations = inspect_source(
        "payload = result.model_dump_json()\n",
        path=Path("src/example.py"),
    )

    assert len(violations) == 1
    assert violations[0].method == "model_dump_json"


def test_comments_and_strings_do_not_trigger() -> None:
    source = """
# result.model_dump()
message = "result.model_dump_json()"
"""

    violations = inspect_source(
        source,
        path=Path("src/example.py"),
    )

    assert violations == []


def test_normal_json_dump_is_allowed() -> None:
    source = """
import json

payload = {"status": "pass"}
encoded = json.dumps(payload)
"""

    violations = inspect_source(
        source,
        path=Path("src/example.py"),
    )

    assert violations == []


def test_public_serializer_call_is_allowed() -> None:
    source = """
payload = serialize_public_contract(public_result)
"""

    violations = inspect_source(
        source,
        path=Path("src/example.py"),
    )

    assert violations == []


def test_trusted_public_contract_file_may_export_model(
    tmp_path: Path,
) -> None:
    root = tmp_path
    path = root / "src" / "public_contract.py"
    path.parent.mkdir(parents=True)
    path.write_text(
        'payload = value.model_dump(mode="json")\n',
        encoding="utf-8",
    )

    violations = inspect_file(
        path,
        root=root,
    )

    assert violations == []


def test_untrusted_file_cannot_export_model(
    tmp_path: Path,
) -> None:
    root = tmp_path
    path = root / "src" / "some_serializer.py"
    path.parent.mkdir(parents=True)
    path.write_text(
        'payload = value.model_dump(mode="json")\n',
        encoding="utf-8",
    )

    violations = inspect_file(
        path,
        root=root,
    )

    assert len(violations) == 1
    assert violations[0].path == Path(
        "src/some_serializer.py"
    )


def test_violation_format_contains_source_location() -> None:
    violations = inspect_source(
        "payload = result.model_dump()\n",
        path=Path("src/example.py"),
    )

    message = violations[0].format()

    assert "src/example.py:1:" in message
    assert "model_dump()" in message

def test_src_python_file_is_production_surface() -> None:
    assert (
        is_production_python_path(
            Path("src/evaluation/report.py")
        )
        is True
    )


def test_root_python_entry_point_is_production_surface() -> None:
    assert (
        is_production_python_path(
            Path("dataset_cli.py")
        )
        is True
    )


def test_test_file_is_not_production_surface() -> None:
    assert (
        is_production_python_path(
            Path("tests/test_example.py")
        )
        is False
    )


def test_script_file_is_not_production_surface() -> None:
    assert (
        is_production_python_path(
            Path("scripts/check_something.py")
        )
        is False
    )


def test_current_repository_respects_public_export_boundary() -> None:
    root = Path(__file__).resolve().parents[1]

    violations = scan_repository(root)

    assert violations == []

def test_trusted_internal_serialization_gateway_may_export_model(
    tmp_path: Path,
) -> None:
    root = tmp_path
    path = root / "src" / "internal_serialization.py"
    path.parent.mkdir(parents=True)
    path.write_text(
        'payload = value.model_dump(mode="json")\n',
        encoding="utf-8",
    )

    violations = inspect_file(
        path,
        root=root,
    )

    assert violations == []

def test_scan_repository_includes_untracked_production_file(
    tmp_path: Path,
) -> None:
    path = tmp_path / "src" / "new_export.py"
    path.parent.mkdir(parents=True)

    path.write_text(
        "payload = result.model_dump()\n",
        encoding="utf-8",
    )

    violations = scan_repository(tmp_path)

    assert len(violations) == 1
    assert violations[0].path == Path(
        "src/new_export.py"
    )


def test_invalid_production_python_fails_closed() -> None:
    with pytest.raises(
        PublicExportBoundaryScanError,
        match="unable to parse production Python source",
    ):
        inspect_source(
            "def broken(:\n",
            path=Path("src/broken.py"),
        )
