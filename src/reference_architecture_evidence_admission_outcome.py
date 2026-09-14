from __future__ import annotations

import json
from typing import Literal

from pydantic import model_validator

from src.public_contract import PublicContractModel, serialize_public_contract
from src.reference_architecture_evidence_admission_contract import (
    REFERENCE_ARCHITECTURE_EVIDENCE_ADMISSION_CONTRACT_VERSION,
    ReferenceArchitectureAdmissionDecision,
    ReferenceArchitectureAdmissionReasonCode,
    ReferenceArchitectureInternalAdmissionResultV1,
)


class ReferenceArchitectureEvidenceAdmissionOutcomeV1(PublicContractModel):
    """The entire frozen public ATL-A.05 boundary: no internal trace is exposed."""

    contract_version: Literal["1.0"] = REFERENCE_ARCHITECTURE_EVIDENCE_ADMISSION_CONTRACT_VERSION
    decision: ReferenceArchitectureAdmissionDecision
    reason_code: ReferenceArchitectureAdmissionReasonCode

    @model_validator(mode="after")
    def validate_decision_reason(self) -> "ReferenceArchitectureEvidenceAdmissionOutcomeV1":
        if (self.decision is ReferenceArchitectureAdmissionDecision.ADMITTED) != (
            self.reason_code is ReferenceArchitectureAdmissionReasonCode.EVIDENCE_ADMITTED
        ):
            raise ValueError("Only evidence_admitted may accompany an admitted decision.")
        return self


def project_reference_architecture_evidence_admission_outcome(
    result: ReferenceArchitectureInternalAdmissionResultV1,
) -> ReferenceArchitectureEvidenceAdmissionOutcomeV1:
    if not isinstance(result, ReferenceArchitectureInternalAdmissionResultV1):
        raise TypeError("result must be an internal admission result.")
    return ReferenceArchitectureEvidenceAdmissionOutcomeV1(
        decision=result.decision, reason_code=result.reason_code
    )


def encode_reference_architecture_evidence_admission_outcome(
    outcome: ReferenceArchitectureEvidenceAdmissionOutcomeV1,
) -> bytes:
    payload = serialize_public_contract(outcome)
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def decode_reference_architecture_evidence_admission_outcome(
    document: bytes,
) -> ReferenceArchitectureEvidenceAdmissionOutcomeV1:
    if type(document) is not bytes:
        raise TypeError("document must be bytes.")
    return ReferenceArchitectureEvidenceAdmissionOutcomeV1.model_validate_json(document)


__all__ = [
    "ReferenceArchitectureEvidenceAdmissionOutcomeV1",
    "decode_reference_architecture_evidence_admission_outcome",
    "encode_reference_architecture_evidence_admission_outcome",
    "project_reference_architecture_evidence_admission_outcome",
]
