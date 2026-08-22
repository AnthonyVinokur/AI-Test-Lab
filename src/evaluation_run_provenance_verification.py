from __future__ import annotations

import hmac

from src.evaluation_run_provenance import EvaluationRunProvenance
from src.evaluation_run_provenance_fingerprint import (
    fingerprint_evaluation_run_provenance,
)


def verify_evaluation_run_provenance_fingerprint(
    provenance: EvaluationRunProvenance,
    expected_fingerprint: str,
) -> bool:
    actual_fingerprint = fingerprint_evaluation_run_provenance(provenance)

    return hmac.compare_digest(
        actual_fingerprint,
        expected_fingerprint,
    )