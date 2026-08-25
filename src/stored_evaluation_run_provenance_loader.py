from __future__ import annotations

import json
from pathlib import Path

from src.evaluation_run_provenance import EvaluationRunProvenance


class StoredEvaluationRunProvenanceLoadError(ValueError):
    """Raised when stored evaluation-run provenance cannot be loaded."""


_REQUIRED_FIELDS = frozenset(
    {
        "run_id",
        "model",
        "evaluation_profile",
        "dataset",
        "dataset_version",
        "report_contract",
        "report_contract_fingerprint",
    }
)


def load_stored_evaluation_run_provenance(
    path: str | Path,
) -> EvaluationRunProvenance:
    """Load approved evaluation-run provenance from a JSON sidecar."""

    provenance_path = Path(path)

    try:
        raw = provenance_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise StoredEvaluationRunProvenanceLoadError(
            f"Unable to read evaluation-run provenance "
            f"'{provenance_path}'."
        ) from exc

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise StoredEvaluationRunProvenanceLoadError(
            f"Invalid evaluation-run provenance JSON "
            f"in '{provenance_path}'."
        ) from exc

    if not isinstance(payload, dict):
        raise StoredEvaluationRunProvenanceLoadError(
            "Evaluation-run provenance JSON root must be an object."
        )

    supplied_fields = set(payload)
    missing_fields = sorted(_REQUIRED_FIELDS - supplied_fields)
    unknown_fields = sorted(supplied_fields - _REQUIRED_FIELDS)

    if missing_fields:
        raise StoredEvaluationRunProvenanceLoadError(
            "Evaluation-run provenance is missing required field(s): "
            + ", ".join(missing_fields)
            + "."
        )

    if unknown_fields:
        raise StoredEvaluationRunProvenanceLoadError(
            "Evaluation-run provenance contains unknown field(s): "
            + ", ".join(unknown_fields)
            + "."
        )

    try:
        return EvaluationRunProvenance(**payload)
    except (TypeError, ValueError) as exc:
        raise StoredEvaluationRunProvenanceLoadError(
            f"Invalid evaluation-run provenance in "
            f"'{provenance_path}': {exc}"
        ) from exc
