from __future__ import annotations

from typing import Literal

from pydantic import model_validator

from src.public_contract import PublicContractModel
from src.reference_architecture_trust_decision import ReferenceArchitectureInternalTrustDecisionV1
from src.reference_architecture_trust_failure_normalization import ReferenceArchitectureTrustFailureCode, normalize_reference_architecture_trust_failure


REFERENCE_ARCHITECTURE_TRUSTED_EVIDENCE_OUTCOME_CONTRACT_NAME = "ai-test-lab.reference-architecture-trusted-evidence-outcome"
REFERENCE_ARCHITECTURE_TRUSTED_EVIDENCE_OUTCOME_CONTRACT_VERSION = "1.0"


class ReferenceArchitectureTrustedEvidenceOutcomeV1(PublicContractModel):
    contract_name: Literal["ai-test-lab.reference-architecture-trusted-evidence-outcome"] = REFERENCE_ARCHITECTURE_TRUSTED_EVIDENCE_OUTCOME_CONTRACT_NAME
    outcome_contract_version: Literal["1.0"] = REFERENCE_ARCHITECTURE_TRUSTED_EVIDENCE_OUTCOME_CONTRACT_VERSION
    status: Literal["trusted", "rejected"]
    trusted: bool
    reason_code: ReferenceArchitectureTrustFailureCode | None = None
    signer_id: str | None = None
    key_id: str | None = None
    policy_id: str
    policy_version: str
    evaluated_at: str

    @model_validator(mode="after")
    def validate_status(self) -> "ReferenceArchitectureTrustedEvidenceOutcomeV1":
        if self.trusted != (self.status == "trusted"):
            raise ValueError("trusted must agree with status.")
        if self.trusted != (self.reason_code is None):
            raise ValueError("reason_code must be absent exactly for trusted outcomes.")
        return self


def project_reference_architecture_trusted_evidence_outcome(decision: ReferenceArchitectureInternalTrustDecisionV1) -> ReferenceArchitectureTrustedEvidenceOutcomeV1:
    if not isinstance(decision, ReferenceArchitectureInternalTrustDecisionV1):
        raise TypeError("decision must be an internal trust decision.")
    return ReferenceArchitectureTrustedEvidenceOutcomeV1(
        status="trusted" if decision.trusted else "rejected", trusted=decision.trusted,
        reason_code=None if decision.trusted else normalize_reference_architecture_trust_failure(decision.failure or RuntimeError()),
        signer_id=decision.signer_id, key_id=decision.key_id, policy_id=decision.policy_id, policy_version=decision.policy_version,
        evaluated_at=decision.evaluated_at.isoformat(timespec="seconds").replace("+00:00", "Z"),
    )


__all__ = ["REFERENCE_ARCHITECTURE_TRUSTED_EVIDENCE_OUTCOME_CONTRACT_NAME", "REFERENCE_ARCHITECTURE_TRUSTED_EVIDENCE_OUTCOME_CONTRACT_VERSION", "ReferenceArchitectureTrustedEvidenceOutcomeV1", "project_reference_architecture_trusted_evidence_outcome"]
