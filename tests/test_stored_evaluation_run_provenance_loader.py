from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.stored_evaluation_run_provenance_loader import (
    StoredEvaluationRunProvenanceLoadError,
    load_stored_evaluation_run_provenance,
)


def valid_payload() -> dict[str, str]:
    return {
        "run_id": "baseline-run-001",
        "model": "llama3.1:latest",
        "evaluation_profile": "fast-ci",
        "dataset": "regression-suite",
        "dataset_version": "1",
        "report_contract": "ai-test-lab.public-report",
        "report_contract_fingerprint": "sha256:abc123",
    }


def write_payload(
    tmp_path: Path,
    payload: object,
) -> Path:
    path = tmp_path / "baseline-provenance.json"
    path.write_text(
        json.dumps(payload),
        encoding="utf-8",
    )
    return path



def test_loads_valid_stored_provenance(tmp_path) -> None:
    path = write_payload(tmp_path, valid_payload())

    provenance = load_stored_evaluation_run_provenance(path)

    assert provenance.run_id == "baseline-run-001"
    assert provenance.model == "llama3.1:latest"
    assert provenance.evaluation_profile == "fast-ci"
    assert provenance.dataset == "regression-suite"
    assert provenance.dataset_version == "1"
    assert provenance.report_contract == "ai-test-lab.public-report"
    assert provenance.report_contract_fingerprint == "sha256:abc123"


def test_accepts_string_path(tmp_path) -> None:
    path = write_payload(tmp_path, valid_payload())

    provenance = load_stored_evaluation_run_provenance(str(path))

    assert provenance.run_id == "baseline-run-001"


def test_rejects_unreadable_file(tmp_path) -> None:
    missing_path = tmp_path / "missing.json"

    with pytest.raises(
            StoredEvaluationRunProvenanceLoadError,
            match="Unable to read evaluation-run provenance",
    ):
        load_stored_evaluation_run_provenance(missing_path)


def test_rejects_invalid_json(tmp_path) -> None:
    path = tmp_path / "invalid.json"
    path.write_text("{not-json", encoding="utf-8")

    with pytest.raises(
            StoredEvaluationRunProvenanceLoadError,
            match="Invalid evaluation-run provenance JSON",
    ):
        load_stored_evaluation_run_provenance(path)


def test_rejects_non_object_json(tmp_path) -> None:
    path = write_payload(tmp_path, [])

    with pytest.raises(
            StoredEvaluationRunProvenanceLoadError,
            match="JSON root must be an object",
    ):
        load_stored_evaluation_run_provenance(path)


def test_rejects_missing_field(tmp_path) -> None:
    payload = valid_payload()
    del payload["dataset_version"]
    path = write_payload(tmp_path, payload)

    with pytest.raises(
            StoredEvaluationRunProvenanceLoadError,
            match=(
                    r"missing required field\(s\): "
                    r"dataset_version\."
            ),
    ):
        load_stored_evaluation_run_provenance(path)


def test_rejects_unknown_field(tmp_path) -> None:
    payload = valid_payload()
    payload["internal_policy"] = "protected"
    path = write_payload(tmp_path, payload)

    with pytest.raises(
            StoredEvaluationRunProvenanceLoadError,
            match=(
                    r"contains unknown field\(s\): "
                    r"internal_policy\."
            ),
    ):
        load_stored_evaluation_run_provenance(path)


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("run_id", ""),
        ("model", "   "),
        ("evaluation_profile", None),
        ("dataset", 123),
        ("dataset_version", ""),
        ("report_contract", []),
        ("report_contract_fingerprint", False),
    ],
)
def test_rejects_invalid_field_values(
        tmp_path,
        field_name,
        invalid_value,
) -> None:
    payload = valid_payload()
    payload[field_name] = invalid_value
    path = write_payload(tmp_path, payload)

    with pytest.raises(
        StoredEvaluationRunProvenanceLoadError,
        match=rf"{field_name} must be a non-empty string",
    ):
        load_stored_evaluation_run_provenance(path)
