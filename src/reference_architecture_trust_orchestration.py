from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any

from src.reference_architecture_authenticated_provenance_outcome import ReferenceArchitectureAuthenticatedProvenanceOutcomeV1
from src.reference_architecture_trust_decision import ReferenceArchitectureTrustEvaluationRequestV1, evaluate_reference_architecture_trust
from src.reference_architecture_trust_failure_normalization import ReferenceArchitectureTrustFailureCode
from src.reference_architecture_trust_policy_translation import translate_untrusted_reference_architecture_trust_policy
from src.reference_architecture_trusted_evidence_outcome import ReferenceArchitectureTrustedEvidenceOutcomeV1, project_reference_architecture_trusted_evidence_outcome


def evaluate_public_reference_architecture_trust(
    authenticated_provenance: ReferenceArchitectureAuthenticatedProvenanceOutcomeV1,
    policy_document: Mapping[str, Any],
    *,
    purpose: str,
    environment: str,
    evaluated_at: datetime,
) -> ReferenceArchitectureTrustedEvidenceOutcomeV1:
    """ATL-A.04 public boundary: explicit inputs, fail closed, minimal output."""
    if not isinstance(evaluated_at, datetime) or evaluated_at.tzinfo is None:
        return ReferenceArchitectureTrustedEvidenceOutcomeV1(
            status="rejected", trusted=False, reason_code=ReferenceArchitectureTrustFailureCode.TRUST_EVALUATION_FAILED,
            policy_id="unavailable", policy_version="unavailable", evaluated_at="unavailable",
        )
    public_time = evaluated_at.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    try:
        policy = translate_untrusted_reference_architecture_trust_policy(policy_document)
    except Exception:
        return ReferenceArchitectureTrustedEvidenceOutcomeV1(
            status="rejected", trusted=False, reason_code=ReferenceArchitectureTrustFailureCode.INVALID_TRUST_POLICY,
            policy_id="unavailable", policy_version="unavailable", evaluated_at=public_time,
        )
    try:
        request = ReferenceArchitectureTrustEvaluationRequestV1(
            authenticated_provenance=authenticated_provenance, policy=policy, purpose=purpose,
            environment=environment, evaluated_at=evaluated_at,
        )
        return project_reference_architecture_trusted_evidence_outcome(evaluate_reference_architecture_trust(request))
    except Exception:
        authentication = authenticated_provenance.authentication if isinstance(authenticated_provenance, ReferenceArchitectureAuthenticatedProvenanceOutcomeV1) else None
        return ReferenceArchitectureTrustedEvidenceOutcomeV1(
            status="rejected", trusted=False, reason_code=ReferenceArchitectureTrustFailureCode.TRUST_EVALUATION_FAILED,
            signer_id=authentication.producer_id if authentication else None, key_id=authentication.key_id if authentication else None,
            policy_id=policy.policy_id, policy_version=policy.policy_version, evaluated_at=public_time,
        )


__all__ = ["evaluate_public_reference_architecture_trust"]
