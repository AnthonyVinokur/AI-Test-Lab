from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any

from src.public_contract import serialize_public_contract
from src.reference_architecture_conformance_evidence_intake_contract import (
    ReferenceArchitectureConformanceEvidenceIntakeV1,
)


REFERENCE_ARCHITECTURE_CONFORMANCE_EVIDENCE_INTEGRITY_VERIFICATION_CONTRACT_NAME = (
    "ai-test-lab.reference-architecture-conformance-evidence-integrity-verification"
)
REFERENCE_ARCHITECTURE_CONFORMANCE_EVIDENCE_INTEGRITY_VERIFICATION_CONTRACT_VERSION = (
    "1.0"
)


def verify_reference_architecture_conformance_evidence_integrity(
    intake: ReferenceArchitectureConformanceEvidenceIntakeV1,
) -> bool:
    """Verify the two SHA-256 identities published by Aquagear A.43.3.

    The verifier reproduces the frozen producer's canonical JSON inputs. It
    does not interpret the evaluation, decide compatibility, mutate the intake,
    or include the transport envelope in either digest.
    """

    if not isinstance(intake, ReferenceArchitectureConformanceEvidenceIntakeV1):
        raise TypeError(
            "intake must be a ReferenceArchitectureConformanceEvidenceIntakeV1."
        )

    evidence = serialize_public_contract(intake)["evidence"]
    evaluation = evidence["evaluation"]

    computed_evaluation_sha256 = _sha256_canonical_json(evaluation)
    evaluation_matches = hmac.compare_digest(
        computed_evaluation_sha256,
        evidence["evaluation_sha256"],
    )

    unsigned_evidence = {
        "schema_version": evidence["schema_version"],
        "architecture_version": evidence["architecture_version"],
        "evaluation": evaluation,
        "evaluation_sha256": evidence["evaluation_sha256"],
    }
    computed_evidence_sha256 = _sha256_canonical_json(unsigned_evidence)
    evidence_matches = hmac.compare_digest(
        computed_evidence_sha256,
        evidence["evidence_sha256"],
    )

    return evaluation_matches and evidence_matches


def _sha256_canonical_json(value: Any) -> str:
    canonical_json = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


__all__ = [
    "REFERENCE_ARCHITECTURE_CONFORMANCE_EVIDENCE_INTEGRITY_VERIFICATION_CONTRACT_NAME",
    "REFERENCE_ARCHITECTURE_CONFORMANCE_EVIDENCE_INTEGRITY_VERIFICATION_CONTRACT_VERSION",
    "verify_reference_architecture_conformance_evidence_integrity",
]
