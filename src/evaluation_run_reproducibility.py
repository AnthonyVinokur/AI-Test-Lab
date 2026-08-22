from __future__ import annotations

from dataclasses import dataclass

from src.evaluation_run_provenance import EvaluationRunProvenance


_REPRODUCIBILITY_FIELDS = (
    "model",
    "evaluation_profile",
    "dataset",
    "dataset_version",
    "report_contract",
    "report_contract_fingerprint",
)


@dataclass(frozen=True)
class EvaluationRunReproducibilityVerification:
    reproducible: bool
    mismatches: tuple[str, ...]


def verify_evaluation_run_reproducibility(
    baseline: EvaluationRunProvenance,
    candidate: EvaluationRunProvenance,
) -> EvaluationRunReproducibilityVerification:
    if not isinstance(baseline, EvaluationRunProvenance):
        raise TypeError("baseline must be an EvaluationRunProvenance")

    if not isinstance(candidate, EvaluationRunProvenance):
        raise TypeError("candidate must be an EvaluationRunProvenance")

    mismatches = tuple(
        field_name
        for field_name in _REPRODUCIBILITY_FIELDS
        if getattr(baseline, field_name) != getattr(candidate, field_name)
    )

    return EvaluationRunReproducibilityVerification(
        reproducible=not mismatches,
        mismatches=mismatches,
    )