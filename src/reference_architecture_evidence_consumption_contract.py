from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from types import MappingProxyType
from typing import Mapping


EVIDENCE_CONSUMPTION_CONTRACT_VERSION = "1.0"
_ID = re.compile(r"[^\s\x00-\x1f\x7f]{1,256}")
_DIGEST = re.compile(r"[0-9a-f]{64}")


class EvidenceLifecycleState(str, Enum):
    ACTIVE = "active"
    RESTRICTED = "restricted"
    ON_HOLD = "on_hold"
    EXPIRED = "expired"
    RETIRED = "retired"
    REVOKED = "revoked"


class EvidenceDisclosurePurpose(str, Enum):
    INTERNAL_DEBUGGING = "internal_debugging"
    REGRESSION_INVESTIGATION = "regression_investigation"
    CUSTOMER_EVIDENCE_DELIVERY = "customer_evidence_delivery"
    EXTERNAL_AUDIT = "external_audit"
    INCIDENT_INVESTIGATION = "incident_investigation"
    REGULATORY_REVIEW = "regulatory_review"
    MODEL_RELEASE_REVIEW = "model_release_review"


class ConsumptionStatus(str, Enum):
    AUTHORIZED = "authorized"
    DENIED = "denied"
    ERROR = "error"


class ConsumptionReasonCode(str, Enum):
    CONSUMPTION_AUTHORIZED = "consumption_authorized"
    MALFORMED_CONSUMPTION_REQUEST = "malformed_consumption_request"
    REQUESTER_NOT_FOUND = "requester_not_found"
    REQUESTER_DISABLED = "requester_disabled"
    AMBIGUOUS_REQUESTER = "ambiguous_requester"
    POLICY_NOT_FOUND = "policy_not_found"
    UNSUPPORTED_POLICY_VERSION = "unsupported_policy_version"
    POLICY_NOT_ACTIVE = "policy_not_active"
    LEDGER_NOT_FOUND = "ledger_not_found"
    EVIDENCE_NOT_FOUND = "evidence_not_found"
    LEDGER_VERIFICATION_FAILED = "ledger_verification_failed"
    PURPOSE_NOT_ALLOWED = "purpose_not_allowed"
    ENVIRONMENT_NOT_ALLOWED = "environment_not_allowed"
    TENANT_SCOPE_MISMATCH = "tenant_scope_mismatch"
    RUN_SCOPE_MISMATCH = "run_scope_mismatch"
    EVIDENCE_TYPE_RESTRICTED = "evidence_type_restricted"
    EVIDENCE_ON_HOLD = "evidence_on_hold"
    EVIDENCE_EXPIRED = "evidence_expired"
    EVIDENCE_RETIRED = "evidence_retired"
    EVIDENCE_REVOKED = "evidence_revoked"
    DISCLOSURE_NOT_ALLOWED = "disclosure_not_allowed"
    PACKAGE_SELECTION_INCOMPLETE = "package_selection_incomplete"
    INTERNAL_CONSUMPTION_ERROR = "internal_consumption_error"


def _identifier(value: object, name: str) -> str:
    if type(value) is not str or _ID.fullmatch(value) is None:
        raise ValueError(f"{name} must be a visible identifier of 1-256 characters.")
    return value


def _digest(value: object, name: str) -> str:
    if type(value) is not str or _DIGEST.fullmatch(value) is None:
        raise ValueError(f"{name} must be a lowercase SHA-256 digest.")
    return value


def _utc(value: object, name: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware.")
    return value.astimezone(timezone.utc)


@dataclass(frozen=True, slots=True)
class EvidenceConsumptionRequest:
    requester_id: str
    requester_type: str
    tenant_id: str
    ledger_id: str
    purpose: EvidenceDisclosurePurpose
    target_environment: str
    policy_id: str
    policy_version: str
    package_version: str = "1.0"
    evidence_ids: tuple[str, ...] = ()
    run_id: str | None = None
    sequence_start: int | None = None
    sequence_end: int | None = None
    authorization_context: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for value, name in ((self.requester_id, "requester_id"), (self.requester_type, "requester_type"),
                            (self.tenant_id, "tenant_id"), (self.target_environment, "target_environment"),
                            (self.policy_id, "policy_id"), (self.policy_version, "policy_version"),
                            (self.package_version, "package_version")):
            _identifier(value, name)
        _digest(self.ledger_id, "ledger_id")
        if not isinstance(self.purpose, EvidenceDisclosurePurpose):
            raise ValueError("purpose is unsupported.")
        if not isinstance(self.evidence_ids, tuple) or len(set(self.evidence_ids)) != len(self.evidence_ids):
            raise ValueError("evidence_ids must be a duplicate-free tuple.")
        for item in self.evidence_ids:
            _digest(item, "evidence_id")
        if self.run_id is not None:
            _identifier(self.run_id, "run_id")
        for value, name in ((self.sequence_start, "sequence_start"), (self.sequence_end, "sequence_end")):
            if value is not None and (type(value) is not int or value < 1):
                raise ValueError(f"{name} must be a positive integer.")
        if self.sequence_start is not None and self.sequence_end is not None and self.sequence_start > self.sequence_end:
            raise ValueError("sequence range is invalid.")
        if not isinstance(self.authorization_context, Mapping) or len(self.authorization_context) > 16:
            raise ValueError("authorization_context is invalid.")
        clean: dict[str, str] = {}
        for key, value in self.authorization_context.items():
            clean[_identifier(key, "authorization context key")] = _identifier(value, "authorization context value")
        object.__setattr__(self, "authorization_context", MappingProxyType(clean))


@dataclass(frozen=True, slots=True)
class EvidenceConsumptionPolicy:
    policy_id: str
    version: str
    effective_at: datetime
    expires_at: datetime | None
    allowed_purposes: frozenset[EvidenceDisclosurePurpose]
    allowed_environments: frozenset[str]
    allowed_evidence_types: frozenset[str]
    retention_by_evidence_type: Mapping[str, timedelta]

    def __post_init__(self) -> None:
        _identifier(self.policy_id, "policy_id"); _identifier(self.version, "version")
        object.__setattr__(self, "effective_at", _utc(self.effective_at, "effective_at"))
        if self.expires_at is not None:
            object.__setattr__(self, "expires_at", _utc(self.expires_at, "expires_at"))
            if self.expires_at <= self.effective_at:
                raise ValueError("expires_at must follow effective_at.")
        if not self.allowed_purposes or not all(isinstance(x, EvidenceDisclosurePurpose) for x in self.allowed_purposes):
            raise ValueError("allowed_purposes is invalid.")
        for values, name in ((self.allowed_environments, "allowed environment"),
                             (self.allowed_evidence_types, "allowed evidence type")):
            if not values:
                raise ValueError(f"{name}s must not be empty.")
            for value in values: _identifier(value, name)
        retention = dict(self.retention_by_evidence_type)
        if set(retention) != set(self.allowed_evidence_types):
            raise ValueError("retention must be defined for every allowed evidence type.")
        if any(not isinstance(value, timedelta) or value <= timedelta(0) for value in retention.values()):
            raise ValueError("retention durations must be positive.")
        object.__setattr__(self, "retention_by_evidence_type", MappingProxyType(retention))


@dataclass(frozen=True, slots=True)
class RequesterAccessScope:
    requester_id: str
    requester_type: str
    tenant_id: str
    enabled: bool
    may_export: bool
    allowed_purposes: frozenset[EvidenceDisclosurePurpose]
    allowed_environments: frozenset[str]
    allowed_ledger_ids: frozenset[str] = frozenset()
    allowed_run_ids: frozenset[str] = frozenset()
    allowed_evidence_types: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        for value, name in ((self.requester_id, "requester_id"), (self.requester_type, "requester_type"),
                            (self.tenant_id, "tenant_id")):
            _identifier(value, name)
        if type(self.enabled) is not bool or type(self.may_export) is not bool:
            raise ValueError("requester status flags must be booleans.")
        if not all(isinstance(x, EvidenceDisclosurePurpose) for x in self.allowed_purposes):
            raise ValueError("requester purposes are invalid.")
        for value in self.allowed_environments | self.allowed_run_ids | self.allowed_evidence_types:
            _identifier(value, "access scope value")
        for value in self.allowed_ledger_ids:
            _digest(value, "allowed ledger id")


@dataclass(frozen=True, slots=True)
class EvidenceLifecycleRecord:
    evidence_id: str
    state: EvidenceLifecycleState = EvidenceLifecycleState.ACTIVE

    def __post_init__(self) -> None:
        _digest(self.evidence_id, "evidence_id")
        if not isinstance(self.state, EvidenceLifecycleState):
            raise ValueError("state is invalid.")


@dataclass(frozen=True, slots=True)
class EvidenceHold:
    hold_id: str
    tenant_id: str
    hold_type: str
    effective_at: datetime
    expires_at: datetime | None
    issuing_authority_reference: str
    policy_version: str
    evidence_ids: frozenset[str] = frozenset()
    run_ids: frozenset[str] = frozenset()
    permitted_purposes: frozenset[EvidenceDisclosurePurpose] = frozenset({EvidenceDisclosurePurpose.INCIDENT_INVESTIGATION})

    def __post_init__(self) -> None:
        for value, name in ((self.hold_id, "hold_id"), (self.tenant_id, "tenant_id"),
                            (self.hold_type, "hold_type"), (self.issuing_authority_reference, "issuing_authority_reference"),
                            (self.policy_version, "policy_version")):
            _identifier(value, name)
        object.__setattr__(self, "effective_at", _utc(self.effective_at, "effective_at"))
        if self.expires_at is not None:
            object.__setattr__(self, "expires_at", _utc(self.expires_at, "expires_at"))
            if self.expires_at <= self.effective_at:
                raise ValueError("hold expiration must follow its effective time.")
        for value in self.evidence_ids: _digest(value, "held evidence id")
        for value in self.run_ids: _identifier(value, "held run id")
        if not self.permitted_purposes or not all(isinstance(x, EvidenceDisclosurePurpose) for x in self.permitted_purposes):
            raise ValueError("hold purposes are invalid.")

    def active_at(self, when: datetime) -> bool:
        return self.effective_at <= when and (self.expires_at is None or when < self.expires_at)


@dataclass(frozen=True, slots=True)
class EvidenceConsumptionDecision:
    status: ConsumptionStatus
    reason_code: ConsumptionReasonCode
    policy_reference: str | None = None
    evidence_references: tuple[str, ...] = ()
    hold_reference: str | None = None

    @property
    def authorized(self) -> bool:
        return self.status is ConsumptionStatus.AUTHORIZED


@dataclass(frozen=True, slots=True)
class EvidenceConsumptionOutcome:
    status: ConsumptionStatus
    reason_code: ConsumptionReasonCode
    policy_reference: str | None = None
    evidence_references: tuple[str, ...] = ()
    package: object | None = None
    diagnostic: str | None = None

    @property
    def authorized(self) -> bool:
        return self.status is ConsumptionStatus.AUTHORIZED and self.package is not None
