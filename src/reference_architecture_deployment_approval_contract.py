from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from src.reference_architecture_policy_decision_contract import decision_digest, decision_identifier, decision_utc


APPROVAL_CONTRACT_VERSION = "1.0"


class ApprovalState(str, Enum):
    APPROVED = "approved"
    APPROVED_WITH_CONDITIONS = "approved_with_conditions"
    DENIED = "denied"
    PENDING = "pending"
    EXPIRED = "expired"
    REVOKED = "revoked"
    SUPERSEDED = "superseded"
    INVALID = "invalid"


class ApprovalEventType(str, Enum):
    REQUESTED = "requested"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    CONDITIONALLY_APPROVED = "conditionally_approved"
    DENIED = "denied"
    EXPIRED = "expired"
    REVOKED = "revoked"
    SUPERSEDED = "superseded"


@dataclass(frozen=True, slots=True)
class DeploymentTarget:
    tenant_id: str
    environment: str
    region: str
    purpose: str

    def __post_init__(self) -> None:
        for value, name in ((self.tenant_id, "tenant_id"), (self.environment, "environment"),
                            (self.region, "region"), (self.purpose, "purpose")):
            decision_identifier(value, name)


@dataclass(frozen=True, slots=True)
class ArtifactBinding:
    artifact_digest: str
    configuration_digest: str
    provider: str
    model_version: str
    release_id: str
    prompt_version: str | None = None
    dataset_version: str | None = None

    def __post_init__(self) -> None:
        decision_digest(self.artifact_digest, "artifact_digest")
        decision_digest(self.configuration_digest, "configuration_digest")
        for value, name in ((self.provider, "provider"), (self.model_version, "model_version"),
                            (self.release_id, "release_id")):
            decision_identifier(value, name)
        for value, name in ((self.prompt_version, "prompt_version"),
                            (self.dataset_version, "dataset_version")):
            if value is not None:
                decision_identifier(value, name)


@dataclass(frozen=True, slots=True)
class ApproverGrant:
    actor_id: str
    tenant_id: str
    environments: frozenset[str]
    policy_categories: frozenset[str]
    roles: frozenset[str]
    max_risk_level: int
    max_duration_seconds: int
    valid_from: datetime
    valid_until: datetime

    def __post_init__(self) -> None:
        decision_identifier(self.actor_id, "actor_id")
        decision_identifier(self.tenant_id, "tenant_id")
        if not self.environments or not self.policy_categories or not self.roles:
            raise ValueError("approver scope sets must not be empty.")
        if type(self.max_risk_level) is not int or not 0 <= self.max_risk_level <= 10:
            raise ValueError("max_risk_level must be from 0 through 10.")
        if type(self.max_duration_seconds) is not int or self.max_duration_seconds < 1:
            raise ValueError("max_duration_seconds must be positive.")
        object.__setattr__(self, "valid_from", decision_utc(self.valid_from, "valid_from"))
        object.__setattr__(self, "valid_until", decision_utc(self.valid_until, "valid_until"))


@dataclass(frozen=True, slots=True)
class ApprovalRules:
    quorum: int = 1
    prohibit_evaluator: bool = True
    prohibit_sole_requester: bool = True
    required_roles: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        if type(self.quorum) is not int or self.quorum < 1:
            raise ValueError("quorum must be positive.")


@dataclass(frozen=True, slots=True)
class ApprovalRequest:
    request_id: str
    decision_attestation_id: str
    artifact: ArtifactBinding
    target: DeploymentTarget
    requester_id: str
    policy_category: str
    risk_level: int
    valid_from: datetime
    valid_until: datetime
    conditions: tuple[str, ...] = ()
    contract_version: str = APPROVAL_CONTRACT_VERSION

    def __post_init__(self) -> None:
        decision_identifier(self.request_id, "request_id")
        decision_digest(self.decision_attestation_id, "decision_attestation_id")
        decision_identifier(self.requester_id, "requester_id")
        decision_identifier(self.policy_category, "policy_category")
        if type(self.risk_level) is not int or not 0 <= self.risk_level <= 10:
            raise ValueError("risk_level must be from 0 through 10.")
        object.__setattr__(self, "valid_from", decision_utc(self.valid_from, "valid_from"))
        object.__setattr__(self, "valid_until", decision_utc(self.valid_until, "valid_until"))
        if self.valid_from >= self.valid_until:
            raise ValueError("approval validity window is invalid.")
        if len(self.conditions) != len(set(self.conditions)):
            raise ValueError("conditions must not contain duplicates.")
        for item in self.conditions:
            decision_identifier(item, "condition")
        if self.contract_version != APPROVAL_CONTRACT_VERSION:
            raise ValueError("contract_version is unsupported.")


@dataclass(frozen=True, slots=True)
class ApprovalDecision:
    state: ApprovalState
    reason_code: str
    approver_ids: tuple[str, ...]
    conditions: tuple[str, ...] = ()
