import json

import pytest

from src.public_contract import PublicContractExposureError, serialize_public_contract
from src.reference_architecture_evidence_admission_contract import (
    ReferenceArchitectureAdmissionDecision,
    ReferenceArchitectureAdmissionReasonCode,
    ReferenceArchitectureInternalAdmissionResultV1,
)
from src.reference_architecture_evidence_admission_outcome import (
    decode_reference_architecture_evidence_admission_outcome,
    encode_reference_architecture_evidence_admission_outcome,
    project_reference_architecture_evidence_admission_outcome,
)


def test_public_outcome_is_minimal_frozen_json_safe_and_deterministic() -> None:
    internal = ReferenceArchitectureInternalAdmissionResultV1(
        ReferenceArchitectureAdmissionDecision.REJECTED,
        ReferenceArchitectureAdmissionReasonCode.EVIDENCE_BINDING_MISMATCH,
    )
    outcome = project_reference_architecture_evidence_admission_outcome(internal)
    encoded = encode_reference_architecture_evidence_admission_outcome(outcome)
    assert encoded == encode_reference_architecture_evidence_admission_outcome(outcome)
    assert json.loads(encoded) == {
        "contract_version": "1.0", "decision": "rejected",
        "reason_code": "evidence_binding_mismatch",
    }
    assert decode_reference_architecture_evidence_admission_outcome(encoded) == outcome
    with pytest.raises(Exception):
        outcome.decision = ReferenceArchitectureAdmissionDecision.ADMITTED  # type: ignore[misc]


def test_internal_models_cannot_cross_public_serializer() -> None:
    with pytest.raises(PublicContractExposureError):
        serialize_public_contract(
            ReferenceArchitectureInternalAdmissionResultV1(
                ReferenceArchitectureAdmissionDecision.ADMITTED,
                ReferenceArchitectureAdmissionReasonCode.EVIDENCE_ADMITTED,
            )
        )
