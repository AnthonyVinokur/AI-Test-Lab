from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum

from src.reference_architecture_authenticated_provenance_outcome import ReferenceArchitectureAuthenticatedProvenanceOutcomeV1
from src.reference_architecture_trust_policy_contract import ReferenceArchitectureTrustPolicyV1
from src.reference_architecture_trust_policy_evaluation import (
    authorize_reference_architecture_trust_scope,
    enforce_reference_architecture_cryptographic_policy,
    evaluate_reference_architecture_key_validity,
)
from src.reference_architecture_trusted_key_resolution import resolve_reference_architecture_trusted_key


class ReferenceArchitectureInternalTrustDecisionStatus(str, Enum):
    TRUSTED = "trusted"
    REJECTED = "rejected"


@dataclass(frozen=True, slots=True)
class ReferenceArchitectureTrustEvaluationRequestV1:
    authenticated_provenance: ReferenceArchitectureAuthenticatedProvenanceOutcomeV1
    policy: ReferenceArchitectureTrustPolicyV1
    purpose: str
    environment: str
    evaluated_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.authenticated_provenance, ReferenceArchitectureAuthenticatedProvenanceOutcomeV1):
            raise TypeError("authenticated_provenance must be an ATL-A.03 public outcome.")
        if not isinstance(self.policy, ReferenceArchitectureTrustPolicyV1):
            raise TypeError("policy must be a trust-policy contract.")
        for value, name in ((self.purpose, "purpose"), (self.environment, "environment")):
            if type(value) is not str or not value or any(c.isspace() or not c.isprintable() for c in value):
                raise ValueError(f"{name} must be a visible non-whitespace identifier.")
        if not isinstance(self.evaluated_at, datetime) or self.evaluated_at.tzinfo is None:
            raise ValueError("evaluated_at must be an explicit timezone-aware datetime.")
        object.__setattr__(self, "evaluated_at", self.evaluated_at.astimezone(timezone.utc))


@dataclass(frozen=True, slots=True)
class ReferenceArchitectureInternalTrustDecisionV1:
    status: ReferenceArchitectureInternalTrustDecisionStatus
    signer_id: str | None
    key_id: str | None
    policy_id: str
    policy_version: str
    evaluated_at: datetime
    failure: Exception | None = None

    @property
    def trusted(self) -> bool:
        return self.status is ReferenceArchitectureInternalTrustDecisionStatus.TRUSTED


def evaluate_reference_architecture_trust(request: ReferenceArchitectureTrustEvaluationRequestV1) -> ReferenceArchitectureInternalTrustDecisionV1:
    """Evaluate in a fixed order so equivalent inputs produce identical results."""
    if not isinstance(request, ReferenceArchitectureTrustEvaluationRequestV1):
        raise TypeError("request must be a trust-evaluation request.")
    authentication = request.authenticated_provenance.authentication
    signer_id = authentication.producer_id if authentication else None
    key_id = authentication.key_id if authentication else None
    try:
        if not request.authenticated_provenance.succeeded or authentication is None:
            raise ValueError("authenticated provenance is required")
        resolved = resolve_reference_architecture_trusted_key(request.authenticated_provenance, request.policy)
        evaluate_reference_architecture_key_validity(resolved, request.evaluated_at)
        authorize_reference_architecture_trust_scope(resolved, request.purpose, request.environment)
        enforce_reference_architecture_cryptographic_policy(resolved, authentication.algorithm, request.policy)
    except Exception as error:
        return ReferenceArchitectureInternalTrustDecisionV1(
            status=ReferenceArchitectureInternalTrustDecisionStatus.REJECTED, signer_id=signer_id, key_id=key_id,
            policy_id=request.policy.policy_id, policy_version=request.policy.policy_version, evaluated_at=request.evaluated_at, failure=error,
        )
    return ReferenceArchitectureInternalTrustDecisionV1(
        status=ReferenceArchitectureInternalTrustDecisionStatus.TRUSTED, signer_id=signer_id, key_id=key_id,
        policy_id=request.policy.policy_id, policy_version=request.policy.policy_version, evaluated_at=request.evaluated_at,
    )


__all__ = ["ReferenceArchitectureInternalTrustDecisionStatus", "ReferenceArchitectureInternalTrustDecisionV1", "ReferenceArchitectureTrustEvaluationRequestV1", "evaluate_reference_architecture_trust"]
