from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256

from src.reference_architecture_evidence_admission_contract import (
    REFERENCE_ARCHITECTURE_EVIDENCE_ADMISSION_CONTRACT_VERSION,
    ReferenceArchitectureAdmissionDecision, ReferenceArchitectureEvidenceAdmissionRequestV1,
    ReferenceArchitectureInternalAdmissionResultV1,
)

_MINT = object()


@dataclass(frozen=True, slots=True, init=False)
class AdmittedEvidenceAuthorization:
    decision_id: str; evidence_sha256: str; evidence_type: str; producer_id: str
    evaluation_run_id: str; provenance_reference: str; evidence_contract_version: str
    admission_contract_version: str; policy_version: str; expires_at: datetime
    _seal: object

    def __init__(self, *, _mint: object, **values: object) -> None:
        if _mint is not _MINT: raise TypeError("Admission authorizations may only be minted by the trusted ATL-A.05 boundary.")
        for name, value in values.items(): object.__setattr__(self, name, value)
        object.__setattr__(self, "_seal", _MINT)

    @property
    def authentic(self) -> bool: return self._seal is _MINT


def mint_admitted_evidence_authorization(request: ReferenceArchitectureEvidenceAdmissionRequestV1,
    result: ReferenceArchitectureInternalAdmissionResultV1, *, provenance_reference: str) -> AdmittedEvidenceAuthorization:
    if not isinstance(request, ReferenceArchitectureEvidenceAdmissionRequestV1): raise TypeError("request must be an ATL-A.05 request.")
    if not isinstance(result, ReferenceArchitectureInternalAdmissionResultV1) or result.decision is not ReferenceArchitectureAdmissionDecision.ADMITTED:
        raise ValueError("Only a successful internal ATL-A.05 result may authorize ledger admission.")
    seed = "\x1f".join((request.evidence_sha256, request.run_id, request.producer_id,
        provenance_reference, request.policy.policy_version, request.evaluated_at.isoformat()))
    return AdmittedEvidenceAuthorization(_mint=_MINT, decision_id=sha256(seed.encode()).hexdigest(),
        evidence_sha256=request.evidence_sha256, evidence_type=request.evidence_type,
        producer_id=request.producer_id, evaluation_run_id=request.run_id,
        provenance_reference=provenance_reference, evidence_contract_version=request.evidence_contract_version,
        admission_contract_version=REFERENCE_ARCHITECTURE_EVIDENCE_ADMISSION_CONTRACT_VERSION,
        policy_version=request.policy.policy_version, expires_at=request.expires_at)
