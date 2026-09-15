from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping


POLICY_DECISION_CONTRACT_VERSION = "1.0"
POLICY_DECISION_SERIALIZATION_ALGORITHM = "canonical-json-rfc8259"
POLICY_DECISION_DIGEST_ALGORITHM = "sha256"
_ID = re.compile(r"[^\s\x00-\x1f\x7f]{1,256}")
_DIGEST = re.compile(r"[0-9a-f]{64}")
_SIGNATURE = re.compile(r"[0-9a-f]{128}")


def decision_identifier(value: object, name: str) -> str:
    if type(value) is not str or _ID.fullmatch(value) is None:
        raise ValueError(f"{name} must be a visible identifier of 1-256 characters.")
    return value


def decision_digest(value: object, name: str) -> str:
    if type(value) is not str or _DIGEST.fullmatch(value) is None:
        raise ValueError(f"{name} must be a lowercase SHA-256 digest.")
    return value


def decision_signature(value: object, name: str) -> str:
    if type(value) is not str or _SIGNATURE.fullmatch(value) is None:
        raise ValueError(f"{name} must be a lowercase Ed25519 signature.")
    return value


def decision_utc(value: object, name: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware.")
    value = value.astimezone(timezone.utc)
    if value.microsecond:
        raise ValueError(f"{name} must use whole UTC seconds.")
    return value


class DecisionState(str, Enum):
    SATISFIED = "satisfied"
    NOT_SATISFIED = "not_satisfied"
    INDETERMINATE = "indeterminate"
    INVALID = "invalid"


class RequirementOperator(str, Enum):
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    MINIMUM = "minimum"
    MAXIMUM = "maximum"
    IN = "in"
    NOT_IN = "not_in"
    PRESENT = "present"
    ABSENT = "absent"
    FRESH_WITHIN_SECONDS = "fresh_within_seconds"


class RequirementLevel(str, Enum):
    MANDATORY = "mandatory"
    OPTIONAL = "optional"
    WARNING = "warning"


class IndeterminateRule(str, Enum):
    INDETERMINATE = "indeterminate"
    FAIL = "fail"


@dataclass(frozen=True, slots=True)
class PolicyRequirement:
    requirement_id: str
    evidence_type: str
    field: str
    operator: RequirementOperator
    expected: Any = None
    level: RequirementLevel = RequirementLevel.MANDATORY

    def __post_init__(self) -> None:
        decision_identifier(self.requirement_id, "requirement_id")
        decision_identifier(self.evidence_type, "evidence_type")
        decision_identifier(self.field, "field")
        if not isinstance(self.operator, RequirementOperator):
            raise ValueError("operator is unsupported.")
        if not isinstance(self.level, RequirementLevel):
            raise ValueError("level is unsupported.")
        if self.operator in {RequirementOperator.MINIMUM, RequirementOperator.MAXIMUM,
                             RequirementOperator.FRESH_WITHIN_SECONDS} and (
            isinstance(self.expected, bool) or not isinstance(self.expected, (int, float))
        ):
            raise ValueError("expected must be numeric for the selected operator.")
        if self.operator in {RequirementOperator.IN, RequirementOperator.NOT_IN} and not isinstance(
            self.expected, tuple
        ):
            raise ValueError("expected must be a tuple for membership operators.")


@dataclass(frozen=True, slots=True)
class PolicyContract:
    policy_id: str
    version: str
    owner_id: str
    system_type: str
    environment: str
    active_from: datetime
    expires_at: datetime
    requirements: tuple[PolicyRequirement, ...]
    indeterminate_rule: IndeterminateRule = IndeterminateRule.INDETERMINATE
    contract_version: str = POLICY_DECISION_CONTRACT_VERSION

    def __post_init__(self) -> None:
        for value, name in ((self.policy_id, "policy_id"), (self.version, "version"),
                            (self.owner_id, "owner_id"), (self.system_type, "system_type"),
                            (self.environment, "environment")):
            decision_identifier(value, name)
        object.__setattr__(self, "active_from", decision_utc(self.active_from, "active_from"))
        object.__setattr__(self, "expires_at", decision_utc(self.expires_at, "expires_at"))
        if self.active_from >= self.expires_at:
            raise ValueError("policy validity window is invalid.")
        if not isinstance(self.requirements, tuple) or not self.requirements:
            raise ValueError("requirements must be a non-empty tuple.")
        ids = tuple(item.requirement_id for item in self.requirements)
        if len(ids) != len(set(ids)):
            raise ValueError("requirement identifiers must be unique.")
        if not isinstance(self.indeterminate_rule, IndeterminateRule):
            raise ValueError("indeterminate_rule is unsupported.")
        if self.contract_version != POLICY_DECISION_CONTRACT_VERSION:
            raise ValueError("contract_version is unsupported.")


@dataclass(frozen=True, slots=True)
class VerifiedEvidence:
    evidence_id: str
    package_id: str
    package_digest: str
    evidence_type: str
    tenant_id: str
    environment: str
    produced_at: datetime
    values: Mapping[str, Any] = field(default_factory=dict)
    provenance_verified: bool = False
    signer_authorized: bool = False
    ledger_admitted: bool = False
    lifecycle_active: bool = False
    transparency_included: bool = False

    def __post_init__(self) -> None:
        decision_digest(self.evidence_id, "evidence_id")
        decision_digest(self.package_id, "package_id")
        decision_digest(self.package_digest, "package_digest")
        for value, name in ((self.evidence_type, "evidence_type"), (self.tenant_id, "tenant_id"),
                            (self.environment, "environment")):
            decision_identifier(value, name)
        object.__setattr__(self, "produced_at", decision_utc(self.produced_at, "produced_at"))
        if not isinstance(self.values, Mapping):
            raise ValueError("values must be an object.")
        object.__setattr__(self, "values", dict(self.values))

    @property
    def trusted(self) -> bool:
        return all((self.provenance_verified, self.signer_authorized, self.ledger_admitted,
                    self.lifecycle_active, self.transparency_included))


@dataclass(frozen=True, slots=True)
class PolicyDecisionRequest:
    request_id: str
    policy: PolicyContract
    evidence: tuple[VerifiedEvidence, ...]
    tenant_id: str
    system_id: str
    artifact_digest: str
    environment: str
    evaluated_at: datetime
    expires_at: datetime

    def __post_init__(self) -> None:
        for value, name in ((self.request_id, "request_id"), (self.tenant_id, "tenant_id"),
                            (self.system_id, "system_id"), (self.environment, "environment")):
            decision_identifier(value, name)
        decision_digest(self.artifact_digest, "artifact_digest")
        if not isinstance(self.evidence, tuple):
            raise ValueError("evidence must be a tuple.")
        object.__setattr__(self, "evaluated_at", decision_utc(self.evaluated_at, "evaluated_at"))
        object.__setattr__(self, "expires_at", decision_utc(self.expires_at, "expires_at"))
        if self.evaluated_at >= self.expires_at:
            raise ValueError("decision validity window is invalid.")


@dataclass(frozen=True, slots=True)
class RequirementOutcome:
    requirement_id: str
    state: DecisionState
    reason_code: str
    evidence_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PolicyDecision:
    state: DecisionState
    reason_code: str
    requirement_outcomes: tuple[RequirementOutcome, ...]
