from dataclasses import FrozenInstanceError

import pytest

from src.reference_architecture_evidence_admission_contract import (
    ReferenceArchitectureAdmissionDecision,
    ReferenceArchitectureAdmissionReasonCode,
    ReferenceArchitectureInternalAdmissionResultV1,
)


def test_internal_admission_result_is_frozen_and_consistent() -> None:
    result = ReferenceArchitectureInternalAdmissionResultV1(
        decision=ReferenceArchitectureAdmissionDecision.ADMITTED,
        reason_code=ReferenceArchitectureAdmissionReasonCode.EVIDENCE_ADMITTED,
    )

    with pytest.raises(FrozenInstanceError):
        result.decision = ReferenceArchitectureAdmissionDecision.REJECTED  # type: ignore[misc]


def test_admitted_result_cannot_carry_rejection_reason() -> None:
    with pytest.raises(ValueError):
        ReferenceArchitectureInternalAdmissionResultV1(
            decision=ReferenceArchitectureAdmissionDecision.ADMITTED,
            reason_code=ReferenceArchitectureAdmissionReasonCode.EVIDENCE_EXPIRED,
        )
