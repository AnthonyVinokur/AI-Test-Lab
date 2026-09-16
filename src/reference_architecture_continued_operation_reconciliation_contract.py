"""ATL-A.28 protected-operation outcome verification contracts."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Protocol

from pydantic import Field

from src.public_contract import PublicContractModel
from src.reference_architecture_continued_operation_enforcement_contract import (
    ContinuedOperationConsumptionRecord,
)
from src.reference_architecture_continued_operation_execution_contract import (
    ContinuedOperationExecutionAttestation,
    ContinuedOperationExecutionRequest,
    ProtectedOperationManifest,
)
from src.reference_architecture_deployment_execution_contract import digest, identifier, utc


CONTINUED_OPERATION_RECONCILIATION_CONTRACT_VERSION = "1.0"
CONTINUED_OPERATION_RECONCILIATION_ATTESTATION_VERSION = "1.0"


class ContinuedOperationReconciliationError(ValueError):
    """Normalized ATL-A.28 contract error."""


class ReconciliationOutcome(str, Enum):
    VERIFIED = "verified"
    MISMATCH = "mismatch"
    INDETERMINATE = "indeterminate"
    INVALID = "invalid"


class ReconciliationReasonCode(str, Enum):
    EXPECTED_STATE_OBSERVED = "expected_state_observed"
    EXPECTED_STATE_MISMATCH = "expected_state_mismatch"
    EXECUTION_EVIDENCE_INVALID = "execution_evidence_invalid"
    EXECUTION_EVIDENCE_NOT_FOUND = "execution_evidence_not_found"
    EXECUTION_EVIDENCE_UNAVAILABLE = "execution_evidence_unavailable"
    EXECUTION_BINDING_MISMATCH = "execution_binding_mismatch"
    MANIFEST_NOT_FOUND = "manifest_not_found"
    MANIFEST_INVALID = "manifest_invalid"
    POSTCONDITION_UNSUPPORTED = "postcondition_unsupported"
    POLICY_MISMATCH = "policy_mismatch"
    OBSERVER_NOT_FOUND = "observer_not_found"
    OBSERVER_AMBIGUOUS = "observer_ambiguous"
    OBSERVER_DISABLED = "observer_disabled"
    OBSERVER_REVOKED = "observer_revoked"
    OBSERVER_CAPABILITY_MISMATCH = "observer_capability_mismatch"
    OBSERVER_NOT_READ_ONLY = "observer_not_read_only"
    OBSERVATION_UNAVAILABLE = "observation_unavailable"
    OBSERVATION_PARTIAL = "observation_partial"
    OBSERVATION_STALE = "observation_stale"
    OBSERVATION_PRECEDES_EXECUTION = "observation_precedes_execution"
    OBSERVATION_TIME_INVALID = "observation_time_invalid"
    OBSERVATION_INVALID = "observation_invalid"
    OBSERVATIONS_CONFLICT = "observations_conflict"
    VERIFICATION_WINDOW_EXPIRED = "verification_window_expired"
    IDEMPOTENT_RESULT_RETURNED = "idempotent_result_returned"
    RECONCILIATION_REQUEST_CONFLICT = "reconciliation_request_conflict"
    RECONCILIATION_IN_PROGRESS = "reconciliation_in_progress"
    RECONCILIATION_STATE_UNAVAILABLE = "reconciliation_state_unavailable"
    COMMIT_STATUS_UNKNOWN = "commit_status_unknown"
    UNTRUSTED_TIME_SOURCE = "untrusted_time_source"


class PostconditionKind(str, Enum):
    RESOURCE_EXISTS = "resource_exists"
    RESOURCE_ABSENT = "resource_absent"
    LIFECYCLE_STATE_EQUALS = "lifecycle_state_equals"
    FIELDS_EQUAL = "fields_equal"
    REVISION_ADVANCED = "revision_advanced"
    ATTRIBUTES_MATCH = "attributes_match"


class ObservationValueState(str, Enum):
    PRESENT = "present"
    ABSENT = "absent"
    UNKNOWN = "unknown"


class ReconciliationClaimState(str, Enum):
    NEW = "new"
    REPLAY = "replay"
    CONFLICT = "conflict"
    IN_PROGRESS = "in_progress"
    UNAVAILABLE = "unavailable"


def _id(value: object, name: str) -> str:
    try:
        return identifier(value, name)
    except ValueError:
        raise ContinuedOperationReconciliationError(f"{name} is invalid.") from None


def _digest(value: object, name: str) -> str:
    try:
        return digest(value, name)
    except ValueError:
        raise ContinuedOperationReconciliationError(f"{name} is invalid.") from None


def _time(value: object, name: str) -> datetime:
    try:
        return utc(value, name)
    except (ValueError, OverflowError):
        raise ContinuedOperationReconciliationError(f"{name} is invalid.") from None


def _ids(values: object, name: str, *, empty: bool = False) -> tuple[str, ...]:
    if type(values) is not tuple or (not values and not empty):
        raise ContinuedOperationReconciliationError(f"{name} is invalid.")
    if len(values) != len(set(values)):
        raise ContinuedOperationReconciliationError(f"{name} is invalid.")
    for value in values:
        _id(value, name)
    return values


@dataclass(frozen=True, slots=True)
class ReconciliationField:
    name: str
    state: ObservationValueState
    value: str | int | bool | None

    def __post_init__(self) -> None:
        _id(self.name, "field_name")
        if not isinstance(self.state, ObservationValueState):
            raise ContinuedOperationReconciliationError("field state is invalid.")
        if type(self.value) not in {str, int, bool, type(None)}:
            raise ContinuedOperationReconciliationError("field value is invalid.")
        if self.state is not ObservationValueState.PRESENT and self.value is not None:
            raise ContinuedOperationReconciliationError("field value is ambiguous.")
        if self.state is ObservationValueState.PRESENT and self.value is None:
            raise ContinuedOperationReconciliationError("field value is ambiguous.")


def _fields(values: object, name: str, *, empty: bool = False) -> tuple[ReconciliationField, ...]:
    if type(values) is not tuple or (not values and not empty):
        raise ContinuedOperationReconciliationError(f"{name} is invalid.")
    if any(type(value) is not ReconciliationField for value in values):
        raise ContinuedOperationReconciliationError(f"{name} is invalid.")
    names = tuple(value.name for value in values)
    if names != tuple(sorted(names)) or len(names) != len(set(names)):
        raise ContinuedOperationReconciliationError(f"{name} is invalid.")
    return values


@dataclass(frozen=True, slots=True)
class ContinuedOperationReconciliationRequest:
    reconciliation_request_id: str
    execution_attestation_reference: str
    execution_attempt_id: str
    enforcement_request_id: str
    authorization_id: str
    deployment_id: str
    consumer_id: str
    enforcement_point_id: str
    purpose: str
    operation_reference: str
    target_resource_id: str
    canonical_parameter_digest: str
    operation_manifest_reference: str
    operation_manifest_digest: str
    execution_adapter_identity: str
    execution_adapter_version: str
    verification_manifest_reference: str
    verification_policy_reference: str
    requested_observer_identity: str
    requested_observer_version: str
    verification_round_id: str
    idempotency_key: str
    requested_at: datetime
    correlation_id: str
    schema_version: str = CONTINUED_OPERATION_RECONCILIATION_CONTRACT_VERSION

    def __post_init__(self) -> None:
        for value, name in (
            (self.reconciliation_request_id, "reconciliation_request_id"),
            (self.execution_attempt_id, "execution_attempt_id"),
            (self.enforcement_request_id, "enforcement_request_id"),
            (self.deployment_id, "deployment_id"), (self.consumer_id, "consumer_id"),
            (self.enforcement_point_id, "enforcement_point_id"), (self.purpose, "purpose"),
            (self.operation_reference, "operation_reference"),
            (self.target_resource_id, "target_resource_id"),
            (self.operation_manifest_reference, "operation_manifest_reference"),
            (self.execution_adapter_identity, "execution_adapter_identity"),
            (self.execution_adapter_version, "execution_adapter_version"),
            (self.verification_manifest_reference, "verification_manifest_reference"),
            (self.verification_policy_reference, "verification_policy_reference"),
            (self.requested_observer_identity, "requested_observer_identity"),
            (self.requested_observer_version, "requested_observer_version"),
            (self.verification_round_id, "verification_round_id"),
            (self.idempotency_key, "idempotency_key"), (self.correlation_id, "correlation_id"),
        ):
            _id(value, name)
        for value, name in (
            (self.execution_attestation_reference, "execution_attestation_reference"),
            (self.authorization_id, "authorization_id"),
            (self.canonical_parameter_digest, "canonical_parameter_digest"),
            (self.operation_manifest_digest, "operation_manifest_digest"),
        ):
            _digest(value, name)
        object.__setattr__(self, "requested_at", _time(self.requested_at, "requested_at"))
        if self.schema_version != CONTINUED_OPERATION_RECONCILIATION_CONTRACT_VERSION:
            raise ContinuedOperationReconciliationError("reconciliation schema version is unsupported.")


@dataclass(frozen=True, slots=True)
class ExpectedPostcondition:
    kind: PostconditionKind
    target_resource_id: str
    fields: tuple[ReconciliationField, ...]
    expected_postcondition_digest: str

    def __post_init__(self) -> None:
        if not isinstance(self.kind, PostconditionKind):
            raise ContinuedOperationReconciliationError("postcondition kind is invalid.")
        _id(self.target_resource_id, "target_resource_id")
        _fields(self.fields, "postcondition_fields", empty=self.kind in {
            PostconditionKind.RESOURCE_EXISTS, PostconditionKind.RESOURCE_ABSENT,
        })
        _digest(self.expected_postcondition_digest, "expected_postcondition_digest")


@dataclass(frozen=True, slots=True)
class OutcomeVerificationManifest:
    reference: str
    version: str
    operation_manifest_reference: str
    operation_manifest_version: str
    operation_manifest_digest: str
    operation_reference: str
    canonical_parameter_digest: str
    provider: str
    resource_type: str
    target_resource_id: str
    postcondition_kind: PostconditionKind
    expected_fields: tuple[ReconciliationField, ...]
    observer_version: str
    required_observation_capability: str

    def __post_init__(self) -> None:
        for value, name in (
            (self.reference, "verification_manifest_reference"), (self.version, "manifest_version"),
            (self.operation_manifest_reference, "operation_manifest_reference"),
            (self.operation_manifest_version, "operation_manifest_version"),
            (self.operation_reference, "operation_reference"), (self.provider, "provider"),
            (self.resource_type, "resource_type"), (self.target_resource_id, "target_resource_id"),
            (self.observer_version, "observer_version"),
            (self.required_observation_capability, "required_observation_capability"),
        ):
            _id(value, name)
        _digest(self.operation_manifest_digest, "operation_manifest_digest")
        _digest(self.canonical_parameter_digest, "canonical_parameter_digest")
        if not isinstance(self.postcondition_kind, PostconditionKind):
            raise ContinuedOperationReconciliationError("postcondition kind is invalid.")
        _fields(self.expected_fields, "expected_fields", empty=self.postcondition_kind in {
            PostconditionKind.RESOURCE_EXISTS, PostconditionKind.RESOURCE_ABSENT,
        })


@dataclass(frozen=True, slots=True)
class ContinuedOperationVerificationPolicy:
    reference: str
    maximum_observation_age_seconds: int
    verification_window_seconds: int
    observation_timeout_seconds: int

    def __post_init__(self) -> None:
        _id(self.reference, "verification_policy_reference")
        for value, name in (
            (self.maximum_observation_age_seconds, "maximum_observation_age_seconds"),
            (self.verification_window_seconds, "verification_window_seconds"),
            (self.observation_timeout_seconds, "observation_timeout_seconds"),
        ):
            if type(value) is not int or value < 0:
                raise ContinuedOperationReconciliationError(f"{name} is invalid.")
        if self.observation_timeout_seconds > self.verification_window_seconds:
            raise ContinuedOperationReconciliationError("observation timeout exceeds verification window.")


@dataclass(frozen=True, slots=True)
class ObservationRequest:
    execution_attempt_id: str
    provider: str
    resource_type: str
    operation_reference: str
    target_resource_id: str
    required_capability: str
    invocation_started_at: datetime
    observation_deadline: datetime
    expected_postcondition_digest: str

    def __post_init__(self) -> None:
        for value, name in (
            (self.execution_attempt_id, "execution_attempt_id"), (self.provider, "provider"),
            (self.resource_type, "resource_type"),
            (self.operation_reference, "operation_reference"),
            (self.target_resource_id, "target_resource_id"),
            (self.required_capability, "required_capability"),
        ):
            _id(value, name)
        _digest(self.expected_postcondition_digest, "expected_postcondition_digest")
        object.__setattr__(self, "invocation_started_at", _time(
            self.invocation_started_at, "invocation_started_at",
        ))
        object.__setattr__(self, "observation_deadline", _time(
            self.observation_deadline, "observation_deadline",
        ))
        if self.observation_deadline < self.invocation_started_at:
            raise ContinuedOperationReconciliationError("observation window is invalid.")


@dataclass(frozen=True, slots=True)
class ProviderObservation:
    provider: str
    resource_type: str
    target_resource_id: str
    observed_at: datetime
    fields: tuple[ReconciliationField, ...]
    complete: bool
    volatile_field_names: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _id(self.provider, "provider")
        _id(self.resource_type, "resource_type")
        _id(self.target_resource_id, "target_resource_id")
        object.__setattr__(self, "observed_at", _time(self.observed_at, "observed_at"))
        _fields(self.fields, "observation_fields", empty=True)
        _ids(self.volatile_field_names, "volatile_field_names", empty=True)
        if type(self.complete) is not bool:
            raise ContinuedOperationReconciliationError("observation completeness is invalid.")


@dataclass(frozen=True, slots=True)
class NormalizedObservation:
    provider: str
    resource_type: str
    target_resource_id: str
    observed_at: datetime
    fields: tuple[ReconciliationField, ...]
    complete: bool
    observation_digest: str

    def __post_init__(self) -> None:
        _id(self.provider, "provider")
        _id(self.resource_type, "resource_type")
        _id(self.target_resource_id, "target_resource_id")
        object.__setattr__(self, "observed_at", _time(self.observed_at, "observed_at"))
        _fields(self.fields, "observation_fields", empty=True)
        if type(self.complete) is not bool:
            raise ContinuedOperationReconciliationError("observation completeness is invalid.")
        _digest(self.observation_digest, "observation_digest")


@dataclass(frozen=True, slots=True)
class AuthoritativeExecutionEvidence:
    evidence_reference: str
    request: ContinuedOperationExecutionRequest
    consumption_record: ContinuedOperationConsumptionRecord
    operation_manifest: ProtectedOperationManifest
    attestation: ContinuedOperationExecutionAttestation
    committed: bool

    def __post_init__(self) -> None:
        _digest(self.evidence_reference, "execution_evidence_reference")
        if (type(self.request) is not ContinuedOperationExecutionRequest or
                type(self.consumption_record) is not ContinuedOperationConsumptionRecord or
                type(self.operation_manifest) is not ProtectedOperationManifest or
                type(self.attestation) is not ContinuedOperationExecutionAttestation or
                type(self.committed) is not bool):
            raise ContinuedOperationReconciliationError("execution evidence is invalid.")


@dataclass(frozen=True, slots=True)
class ContinuedOperationReconciliationAttestation:
    reconciliation_id: str
    reconciliation_digest: str
    reconciliation_request_id: str
    execution_attestation_reference: str
    execution_attempt_id: str
    consumption_id: str
    authorization_id: str
    deployment_id: str
    consumer_id: str
    enforcement_point_id: str
    purpose: str
    operation_reference: str
    target_resource_id: str
    canonical_parameter_digest: str
    execution_adapter_identity: str
    execution_adapter_version: str
    operation_manifest_reference: str
    operation_manifest_version: str
    verification_manifest_reference: str
    verification_manifest_version: str
    verification_policy_reference: str
    observer_identity: str | None
    observer_version: str | None
    expected_postcondition_digest: str | None
    observation_digests: tuple[str, ...]
    outcome: ReconciliationOutcome
    reason_code: ReconciliationReasonCode
    observed_at: datetime | None
    evidence_issued_at: datetime
    verification_round_id: str
    correlation_id: str
    contract_version: str = CONTINUED_OPERATION_RECONCILIATION_ATTESTATION_VERSION

    def __post_init__(self) -> None:
        for value, name in (
            (self.reconciliation_id, "reconciliation_id"),
            (self.reconciliation_digest, "reconciliation_digest"),
            (self.execution_attestation_reference, "execution_attestation_reference"),
            (self.consumption_id, "consumption_id"), (self.authorization_id, "authorization_id"),
            (self.canonical_parameter_digest, "canonical_parameter_digest"),
        ):
            _digest(value, name)
        for value, name in (
            (self.reconciliation_request_id, "reconciliation_request_id"),
            (self.execution_attempt_id, "execution_attempt_id"),
            (self.deployment_id, "deployment_id"), (self.consumer_id, "consumer_id"),
            (self.enforcement_point_id, "enforcement_point_id"), (self.purpose, "purpose"),
            (self.operation_reference, "operation_reference"),
            (self.target_resource_id, "target_resource_id"),
            (self.execution_adapter_identity, "execution_adapter_identity"),
            (self.execution_adapter_version, "execution_adapter_version"),
            (self.operation_manifest_reference, "operation_manifest_reference"),
            (self.operation_manifest_version, "operation_manifest_version"),
            (self.verification_manifest_reference, "verification_manifest_reference"),
            (self.verification_manifest_version, "verification_manifest_version"),
            (self.verification_policy_reference, "verification_policy_reference"),
            (self.verification_round_id, "verification_round_id"),
            (self.correlation_id, "correlation_id"),
        ):
            _id(value, name)
        for value, name in (
            (self.observer_identity, "observer_identity"),
            (self.observer_version, "observer_version"),
        ):
            if value is not None:
                _id(value, name)
        if self.expected_postcondition_digest is not None:
            _digest(self.expected_postcondition_digest, "expected_postcondition_digest")
        if (type(self.observation_digests) is not tuple or
                tuple(sorted(self.observation_digests)) != self.observation_digests or
                len(set(self.observation_digests)) != len(self.observation_digests)):
            raise ContinuedOperationReconciliationError("observation digests are invalid.")
        for value in self.observation_digests:
            _digest(value, "observation_digest")
        if (not isinstance(self.outcome, ReconciliationOutcome) or
                not isinstance(self.reason_code, ReconciliationReasonCode)):
            raise ContinuedOperationReconciliationError("reconciliation outcome is invalid.")
        if self.observed_at is not None:
            object.__setattr__(self, "observed_at", _time(self.observed_at, "observed_at"))
        object.__setattr__(self, "evidence_issued_at", _time(
            self.evidence_issued_at, "evidence_issued_at",
        ))
        if self.contract_version != CONTINUED_OPERATION_RECONCILIATION_ATTESTATION_VERSION:
            raise ContinuedOperationReconciliationError("attestation version is unsupported.")


@dataclass(frozen=True, slots=True)
class ContinuedOperationReconciliationResult:
    reconciliation_request_id: str
    execution_attempt_id: str
    operation_reference: str
    outcome: ReconciliationOutcome
    reason_code: ReconciliationReasonCode
    evaluated_at: datetime
    attestation: ContinuedOperationReconciliationAttestation | None = None
    idempotent: bool = False

    def __post_init__(self) -> None:
        _id(self.reconciliation_request_id, "reconciliation_request_id")
        _id(self.execution_attempt_id, "execution_attempt_id")
        _id(self.operation_reference, "operation_reference")
        if (not isinstance(self.outcome, ReconciliationOutcome) or
                not isinstance(self.reason_code, ReconciliationReasonCode) or
                type(self.idempotent) is not bool):
            raise ContinuedOperationReconciliationError("reconciliation result is invalid.")
        if (self.attestation is not None and
                type(self.attestation) is not ContinuedOperationReconciliationAttestation):
            raise ContinuedOperationReconciliationError("reconciliation result is invalid.")
        object.__setattr__(self, "evaluated_at", _time(self.evaluated_at, "evaluated_at"))


@dataclass(frozen=True, slots=True)
class AtomicReconciliationClaim:
    state: ReconciliationClaimState
    result: ContinuedOperationReconciliationResult | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.state, ReconciliationClaimState):
            raise ContinuedOperationReconciliationError("claim state is invalid.")
        if self.result is not None and type(self.result) is not ContinuedOperationReconciliationResult:
            raise ContinuedOperationReconciliationError("claim result is invalid.")


class PublicContinuedOperationReconciliationV1(PublicContractModel):
    schema_version: str = CONTINUED_OPERATION_RECONCILIATION_CONTRACT_VERSION
    reconciliation_id: str | None = None
    execution_attempt_id: str = Field(min_length=1)
    operation_reference: str = Field(min_length=1)
    outcome: ReconciliationOutcome
    reason_code: ReconciliationReasonCode
    observed_at: datetime | None = None
    evidence_issued_at: datetime | None = None


class AuthoritativeExecutionEvidenceRepository(Protocol):
    def get_committed(self, reference: str) -> AuthoritativeExecutionEvidence | None: ...


class OutcomeVerificationManifestRepository(Protocol):
    def get(self, reference: str) -> OutcomeVerificationManifest | None: ...


class ContinuedOperationObserver(Protocol):
    identity: str
    version: str
    provider: str
    resource_type: str
    operation_reference: str
    manifest_version: str
    capabilities: frozenset[str]
    read_only: bool
    enabled: bool
    revoked: bool

    def observe(self, request: ObservationRequest) -> tuple[ProviderObservation, ...]: ...


class ReconciliationEvidenceRepository(Protocol):
    def claim(
        self, *, idempotency_key: str, request_digest: str,
    ) -> AtomicReconciliationClaim: ...

    def commit(
        self, *, idempotency_key: str, request_digest: str,
        result: ContinuedOperationReconciliationResult,
    ) -> None: ...


__all__ = [name for name in globals() if name.startswith("ContinuedOperation") or
           name.startswith("Reconciliation") or name.startswith("Postcondition") or
           name.startswith("Observation") or name.startswith("OutcomeVerification") or
           name.startswith("Authoritative") or name.startswith("AtomicReconciliation") or
           name.startswith("ProviderObservation") or name.startswith("NormalizedObservation") or
           name.startswith("PublicContinued")]
__all__ += ["CONTINUED_OPERATION_RECONCILIATION_CONTRACT_VERSION",
            "CONTINUED_OPERATION_RECONCILIATION_ATTESTATION_VERSION"]
