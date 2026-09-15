from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Protocol

from src.reference_architecture_deployment_execution_contract import digest, identifier, utc

INTEGRITY_CONTRACT_VERSION = "1.0"


class DriftClassification(str, Enum):
    NONE = "no_drift"; NON_MATERIAL = "non_material_drift"; MATERIAL = "material_drift"; UNKNOWN = "unknown"; INVALID = "invalid_evidence"


class TrustStatus(str, Enum):
    TRUSTED = "trusted"; DEGRADED = "degraded"; UNTRUSTED = "untrusted"; INDETERMINATE = "indeterminate"; INVALID = "invalid"


class AuthorizationIntegrityState(str, Enum):
    ACTIVE = "active"; EXPIRED = "expired"; REVOKED = "revoked"; SUPERSEDED = "superseded"; UNAVAILABLE = "unavailable"


class RemediationSignal(str, Enum):
    INVESTIGATE = "investigate"; REAUTHORIZE = "re_authorize"; BLOCK_FUTURE_CHANGE = "block_future_change"


@dataclass(frozen=True, slots=True)
class TrustedDeploymentBaseline:
    baseline_id: str; reconciliation_id: str; execution_attestation_id: str; authorization_id: str
    artifact_digest: str; release_id: str; tenant_id: str; environment: str; configuration_digest: str
    baseline_digest: str; established_at: datetime; contract_version: str = INTEGRITY_CONTRACT_VERSION
    def __post_init__(self) -> None:
        for v, n in ((self.baseline_id,"baseline_id"),(self.reconciliation_id,"reconciliation_id"),(self.execution_attestation_id,"execution_attestation_id"),(self.authorization_id,"authorization_id"),(self.artifact_digest,"artifact_digest"),(self.configuration_digest,"configuration_digest"),(self.baseline_digest,"baseline_digest")): digest(v,n)
        for v,n in ((self.release_id,"release_id"),(self.tenant_id,"tenant_id"),(self.environment,"environment")): identifier(v,n)
        object.__setattr__(self,"established_at",utc(self.established_at,"established_at"))
        if self.contract_version != INTEGRITY_CONTRACT_VERSION: raise ValueError("contract_version is unsupported.")


@dataclass(frozen=True, slots=True)
class IntegrityObservation:
    deployment_reference: str; artifact_digest: str | None; release_id: str | None; tenant_id: str | None
    environment: str | None; configuration_digest: str | None; authorization_state: AuthorizationIntegrityState
    observed_at: datetime; observation_digest: str; contract_version: str = INTEGRITY_CONTRACT_VERSION
    def __post_init__(self) -> None:
        identifier(self.deployment_reference,"deployment_reference")
        for v,n in ((self.artifact_digest,"artifact_digest"),(self.configuration_digest,"configuration_digest")):
            if v is not None: digest(v,n)
        for v,n in ((self.release_id,"release_id"),(self.tenant_id,"tenant_id"),(self.environment,"environment")):
            if v is not None: identifier(v,n)
        object.__setattr__(self,"observed_at",utc(self.observed_at,"observed_at")); digest(self.observation_digest,"observation_digest")
        if self.contract_version != INTEGRITY_CONTRACT_VERSION: raise ValueError("contract_version is unsupported.")


@dataclass(frozen=True, slots=True)
class TrustRevocationRecord:
    record_id: str; baseline_id: str; prior_status: TrustStatus; status: TrustStatus; reason_category: str; occurred_at: datetime; record_digest: str
    def __post_init__(self) -> None:
        for v,n in ((self.record_id,"record_id"),(self.baseline_id,"baseline_id"),(self.record_digest,"record_digest")): digest(v,n)
        identifier(self.reason_category,"reason_category"); object.__setattr__(self,"occurred_at",utc(self.occurred_at,"occurred_at"))


@dataclass(frozen=True, slots=True)
class IntegrityResult:
    baseline_id: str; status: TrustStatus; drift: DriftClassification; reason_category: str
    remediation: tuple[RemediationSignal,...]; evaluated_at: datetime; observation_digest: str | None
    result_digest: str; prior_status: TrustStatus | None = None; revocation: TrustRevocationRecord | None = None
    def __post_init__(self) -> None:
        for v,n in ((self.baseline_id,"baseline_id"),(self.result_digest,"result_digest")): digest(v,n)
        if self.observation_digest is not None: digest(self.observation_digest,"observation_digest")
        identifier(self.reason_category,"reason_category"); object.__setattr__(self,"evaluated_at",utc(self.evaluated_at,"evaluated_at"))
        if not isinstance(self.remediation,tuple) or len(self.remediation)!=len(set(self.remediation)): raise ValueError("remediation is invalid.")


class IntegrityObserverPort(Protocol):
    def observe(self, baseline: TrustedDeploymentBaseline, *, evaluation_time: datetime) -> IntegrityObservation: ...

