from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum

from src.reference_architecture_authenticated_provenance_outcome import (
    ReferenceArchitectureAuthenticatedProvenanceOutcomeV1,
)
from src.reference_architecture_conformance_evidence_binding_outcome import (
    ReferenceArchitectureConformanceEvidenceBindingOutcomeV1,
)
from src.reference_architecture_trusted_evidence_outcome import (
    ReferenceArchitectureTrustedEvidenceOutcomeV1,
)


REFERENCE_ARCHITECTURE_EVIDENCE_ADMISSION_CONTRACT_NAME = (
    "ai-test-lab.reference-architecture-evidence-admission"
)
REFERENCE_ARCHITECTURE_EVIDENCE_ADMISSION_CONTRACT_VERSION = "1.0"

_IDENTITY_PATTERN = re.compile(r"[^\s\x00-\x1f\x7f]{1,256}")
_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")


class ReferenceArchitectureReplayStatus(str, Enum):
    NOT_REPLAYED = "not_replayed"
    REPLAYED = "replayed"
    INDETERMINATE = "indeterminate"


class ReferenceArchitectureAdmissionDecision(str, Enum):
    ADMITTED = "admitted"
    REJECTED = "rejected"


class ReferenceArchitectureAdmissionReasonCode(str, Enum):
    EVIDENCE_ADMITTED = "evidence_admitted"
    INVALID_ADMISSION_REQUEST = "invalid_admission_request"
    INTEGRITY_NOT_VERIFIED = "integrity_not_verified"
    PROVENANCE_NOT_AUTHENTICATED = "provenance_not_authenticated"
    PROVENANCE_NOT_TRUSTED = "provenance_not_trusted"
    EVIDENCE_BINDING_MISMATCH = "evidence_binding_mismatch"
    PURPOSE_NOT_ALLOWED = "purpose_not_allowed"
    ENVIRONMENT_NOT_ALLOWED = "environment_not_allowed"
    PRODUCER_NOT_AUTHORIZED = "producer_not_authorized"
    EVIDENCE_TYPE_NOT_SUPPORTED = "evidence_type_not_supported"
    CONTRACT_VERSION_NOT_SUPPORTED = "contract_version_not_supported"
    WORKFLOW_NOT_ALLOWED = "workflow_not_allowed"
    EVIDENCE_NOT_YET_VALID = "evidence_not_yet_valid"
    EVIDENCE_EXPIRED = "evidence_expired"
    EVIDENCE_TOO_OLD = "evidence_too_old"
    EVIDENCE_REPLAY_DETECTED = "evidence_replay_detected"
    ADMISSION_POLICY_ERROR = "admission_policy_error"


def _identity(value: object, name: str) -> str:
    if type(value) is not str or _IDENTITY_PATTERN.fullmatch(value) is None:
        raise ValueError(f"{name} must contain 1-256 visible non-whitespace characters.")
    return value


def _utc(value: object, name: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ValueError(f"{name} must be a timezone-aware datetime.")
    return value.astimezone(timezone.utc)


def _scope(value: object, name: str) -> frozenset[str]:
    if not isinstance(value, frozenset) or not value:
        raise ValueError(f"{name} must be a non-empty frozenset.")
    for item in value:
        _identity(item, name)
    return value


@dataclass(frozen=True, slots=True)
class ReferenceArchitectureEvidenceAdmissionPolicyV1:
    policy_id: str
    policy_version: str
    supported_evidence_types: frozenset[str]
    authorized_producers: frozenset[str]
    allowed_producer_evidence_types: frozenset[tuple[str, str]]
    acceptable_contract_versions: frozenset[str]
    allowed_purposes: frozenset[str]
    allowed_environments: frozenset[str]
    permitted_workflows: frozenset[str]
    maximum_evidence_age: timedelta

    def __post_init__(self) -> None:
        _identity(self.policy_id, "policy_id")
        _identity(self.policy_version, "policy_version")
        for value, name in (
            (self.supported_evidence_types, "supported_evidence_types"),
            (self.authorized_producers, "authorized_producers"),
            (self.acceptable_contract_versions, "acceptable_contract_versions"),
            (self.allowed_purposes, "allowed_purposes"),
            (self.allowed_environments, "allowed_environments"),
            (self.permitted_workflows, "permitted_workflows"),
        ):
            _scope(value, name)
        if not isinstance(self.allowed_producer_evidence_types, frozenset) or not self.allowed_producer_evidence_types:
            raise ValueError("allowed_producer_evidence_types must be a non-empty frozenset.")
        for combination in self.allowed_producer_evidence_types:
            if type(combination) is not tuple or len(combination) != 2:
                raise ValueError("Each producer/evidence combination must be a pair.")
            _identity(combination[0], "producer combination")
            _identity(combination[1], "evidence-type combination")
        if not isinstance(self.maximum_evidence_age, timedelta) or self.maximum_evidence_age <= timedelta(0):
            raise ValueError("maximum_evidence_age must be a positive duration.")


@dataclass(frozen=True, slots=True)
class ReferenceArchitectureEvidenceAdmissionRequestV1:
    evidence_id: str
    evidence_sha256: str
    evidence_type: str
    producer_id: str
    contract_version: str
    purpose: str
    target_environment: str
    workflow_id: str
    run_id: str
    created_at: datetime
    not_before: datetime
    expires_at: datetime
    evaluated_at: datetime
    replay_status: ReferenceArchitectureReplayStatus
    integrity_result: ReferenceArchitectureConformanceEvidenceBindingOutcomeV1
    authenticated_provenance_result: ReferenceArchitectureAuthenticatedProvenanceOutcomeV1
    trust_result: ReferenceArchitectureTrustedEvidenceOutcomeV1
    policy: ReferenceArchitectureEvidenceAdmissionPolicyV1

    def __post_init__(self) -> None:
        for value, name in (
            (self.evidence_id, "evidence_id"),
            (self.evidence_type, "evidence_type"),
            (self.producer_id, "producer_id"),
            (self.contract_version, "contract_version"),
            (self.purpose, "purpose"),
            (self.target_environment, "target_environment"),
            (self.workflow_id, "workflow_id"),
            (self.run_id, "run_id"),
        ):
            _identity(value, name)
        if type(self.evidence_sha256) is not str or _SHA256_PATTERN.fullmatch(self.evidence_sha256) is None:
            raise ValueError("evidence_sha256 must be 64 lowercase hexadecimal characters.")
        for name in ("created_at", "not_before", "expires_at", "evaluated_at"):
            object.__setattr__(self, name, _utc(getattr(self, name), name))
        if self.expires_at <= self.not_before:
            raise ValueError("expires_at must be later than not_before.")
        if not isinstance(self.replay_status, ReferenceArchitectureReplayStatus):
            raise ValueError("replay_status must be an explicit supported status.")
        if not isinstance(self.integrity_result, ReferenceArchitectureConformanceEvidenceBindingOutcomeV1):
            raise TypeError("integrity_result must be an ATL-A.02 public outcome.")
        if not isinstance(self.authenticated_provenance_result, ReferenceArchitectureAuthenticatedProvenanceOutcomeV1):
            raise TypeError("authenticated_provenance_result must be an ATL-A.03 public outcome.")
        if not isinstance(self.trust_result, ReferenceArchitectureTrustedEvidenceOutcomeV1):
            raise TypeError("trust_result must be an ATL-A.04 public outcome.")
        if not isinstance(self.policy, ReferenceArchitectureEvidenceAdmissionPolicyV1):
            raise TypeError("policy must be an ATL-A.05 admission policy.")


@dataclass(frozen=True, slots=True)
class ReferenceArchitectureInternalAdmissionResultV1:
    decision: ReferenceArchitectureAdmissionDecision
    reason_code: ReferenceArchitectureAdmissionReasonCode

    def __post_init__(self) -> None:
        if not isinstance(self.decision, ReferenceArchitectureAdmissionDecision):
            raise TypeError("decision must be an admission decision.")
        if not isinstance(self.reason_code, ReferenceArchitectureAdmissionReasonCode):
            raise TypeError("reason_code must be an admission reason code.")
        if (self.decision is ReferenceArchitectureAdmissionDecision.ADMITTED) != (
            self.reason_code is ReferenceArchitectureAdmissionReasonCode.EVIDENCE_ADMITTED
        ):
            raise ValueError("Only evidence_admitted may accompany an admitted decision.")


__all__ = [
    "REFERENCE_ARCHITECTURE_EVIDENCE_ADMISSION_CONTRACT_NAME",
    "REFERENCE_ARCHITECTURE_EVIDENCE_ADMISSION_CONTRACT_VERSION",
    "ReferenceArchitectureAdmissionDecision",
    "ReferenceArchitectureAdmissionReasonCode",
    "ReferenceArchitectureEvidenceAdmissionPolicyV1",
    "ReferenceArchitectureEvidenceAdmissionRequestV1",
    "ReferenceArchitectureInternalAdmissionResultV1",
    "ReferenceArchitectureReplayStatus",
]
