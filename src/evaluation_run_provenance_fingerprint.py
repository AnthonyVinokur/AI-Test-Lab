from __future__ import annotations

import hashlib
import json

from src.evaluation_run_provenance import EvaluationRunProvenance


def fingerprint_evaluation_run_provenance(
    provenance: EvaluationRunProvenance,
) -> str:
    canonical_payload = json.dumps(
        provenance.to_dict(),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )

    return hashlib.sha256(
        canonical_payload.encode("utf-8")
    ).hexdigest()

