"""ATL-A.28 independent protected-operation outcome reconciliation."""
from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path
from threading import Lock
from typing import Any, Callable, Mapping

from src.reference_architecture_continued_operation_execution import (
    canonicalize_execution_command,
    operation_manifest_digest,
    verify_continued_operation_execution_attestation,
)
from src.reference_architecture_continued_operation_execution_contract import (
    TrustedContinuedOperationPermit,
)
from src.reference_architecture_continued_operation_reconciliation_contract import (
    CONTINUED_OPERATION_RECONCILIATION_ATTESTATION_VERSION,
    CONTINUED_OPERATION_RECONCILIATION_CONTRACT_VERSION,
    AtomicReconciliationClaim,
    AuthoritativeExecutionEvidence,
    AuthoritativeExecutionEvidenceRepository,
    ContinuedOperationObserver,
    ContinuedOperationReconciliationAttestation,
    ContinuedOperationReconciliationError,
    ContinuedOperationReconciliationRequest,
    ContinuedOperationReconciliationResult,
    ContinuedOperationVerificationPolicy,
    ExpectedPostcondition,
    NormalizedObservation,
    ObservationRequest,
    ObservationValueState,
    OutcomeVerificationManifest,
    OutcomeVerificationManifestRepository,
    PostconditionKind,
    ProviderObservation,
    PublicContinuedOperationReconciliationV1,
    ReconciliationClaimState,
    ReconciliationEvidenceRepository,
    ReconciliationField,
    ReconciliationOutcome as Outcome,
    ReconciliationReasonCode as Reason,
)


_REQUEST_DOMAIN = "ai-test-lab:atl-a.28:reconciliation-request:v1"
_POSTCONDITION_DOMAIN = "ai-test-lab:atl-a.28:expected-postcondition:v1"
_OBSERVATION_DOMAIN = "ai-test-lab:atl-a.28:normalized-observation:v1"
_ATTESTATION_DOMAIN = "ai-test-lab:atl-a.28:reconciliation-attestation:v1"
_MAX_DOCUMENT_BYTES = 64 * 1024


class ReconciliationPersistenceError(RuntimeError):
    """The reconciliation repository could not safely complete an operation."""


class ReconciliationCommitStatusUnknown(ReconciliationPersistenceError):
    """The repository cannot establish whether the reconciliation was committed."""


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError):
        raise ContinuedOperationReconciliationError(
            "reconciliation canonical payload is invalid."
        ) from None


def _timestamp(value: datetime) -> str:
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_time(value: object) -> datetime:
    if type(value) is not str or len(value) != 20 or not value.endswith("Z"):
        raise ValueError
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def _no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError
        result[key] = value
    return result


def reconciliation_request_document(
    value: ContinuedOperationReconciliationRequest,
) -> dict[str, Any]:
    if type(value) is not ContinuedOperationReconciliationRequest:
        raise ContinuedOperationReconciliationError("an exact reconciliation request is required.")
    document = asdict(value)
    document["requested_at"] = _timestamp(value.requested_at)
    return document


def reconciliation_request_digest(value: ContinuedOperationReconciliationRequest) -> str:
    return sha256(_canonical({
        "domain": _REQUEST_DOMAIN, **reconciliation_request_document(value),
    })).hexdigest()


def translate_untrusted_reconciliation_request(
    value: bytes | str | Mapping[str, Any],
) -> ContinuedOperationReconciliationRequest:
    try:
        raw: bytes | None
        if type(value) is bytes:
            raw = value
            if len(raw) > _MAX_DOCUMENT_BYTES:
                raise ValueError
            document = json.loads(
                raw, object_pairs_hook=_no_duplicates,
                parse_constant=lambda _: (_ for _ in ()).throw(ValueError()),
            )
        elif type(value) is str:
            raw = value.encode("utf-8")
            if len(raw) > _MAX_DOCUMENT_BYTES:
                raise ValueError
            document = json.loads(
                raw, object_pairs_hook=_no_duplicates,
                parse_constant=lambda _: (_ for _ in ()).throw(ValueError()),
            )
        elif type(value) is dict:
            raw = None
            document = dict(value)
            if len(_canonical(document)) > _MAX_DOCUMENT_BYTES:
                raise ValueError
        else:
            raise ValueError
        forbidden = {
            "expected_postcondition", "expected_fields", "provider_response", "observation",
            "credentials", "token", "trusted", "verified", "repair", "retry_execution",
            "authorization_artifact", "execution_attestation",
        }
        if (type(document) is not dict or
                set(document) != set(ContinuedOperationReconciliationRequest.__dataclass_fields__) or
                set(document) & forbidden):
            raise ValueError
        request = ContinuedOperationReconciliationRequest(**{
            **document, "requested_at": _parse_time(document["requested_at"]),
        })
        if raw is not None and raw != _canonical(reconciliation_request_document(request)):
            raise ValueError
        return request
    except Exception as error:
        raise ContinuedOperationReconciliationError("reconciliation request is invalid.") from error


def _field_document(value: ReconciliationField) -> dict[str, Any]:
    return {"name": value.name, "state": value.state.value, "value": value.value}


def _postcondition_document(
    manifest: OutcomeVerificationManifest,
) -> dict[str, Any]:
    return {
        "canonical_parameter_digest": manifest.canonical_parameter_digest,
        "expected_fields": [_field_document(value) for value in manifest.expected_fields],
        "kind": manifest.postcondition_kind.value,
        "operation_manifest_digest": manifest.operation_manifest_digest,
        "operation_manifest_reference": manifest.operation_manifest_reference,
        "operation_manifest_version": manifest.operation_manifest_version,
        "operation_reference": manifest.operation_reference,
        "target_resource_id": manifest.target_resource_id,
        "verification_manifest_reference": manifest.reference,
        "verification_manifest_version": manifest.version,
    }


def derive_expected_postcondition(
    evidence: AuthoritativeExecutionEvidence,
    manifest: OutcomeVerificationManifest,
) -> ExpectedPostcondition:
    if (type(evidence) is not AuthoritativeExecutionEvidence or
            type(manifest) is not OutcomeVerificationManifest):
        raise ContinuedOperationReconciliationError("postcondition source is invalid.")
    execution_manifest = evidence.operation_manifest
    if (
        manifest.operation_manifest_reference != execution_manifest.reference
        or manifest.operation_manifest_version != execution_manifest.version
        or manifest.operation_manifest_digest != operation_manifest_digest(execution_manifest)
        or manifest.operation_reference != execution_manifest.operation_reference
        or manifest.canonical_parameter_digest != execution_manifest.canonical_operation_input_digest
    ):
        raise ContinuedOperationReconciliationError("verification manifest binding is invalid.")
    digest_value = sha256(_canonical({
        "domain": _POSTCONDITION_DOMAIN, **_postcondition_document(manifest),
    })).hexdigest()
    return ExpectedPostcondition(
        manifest.postcondition_kind, manifest.target_resource_id,
        manifest.expected_fields, digest_value,
    )


def _normalized_document(
    *, provider: str, resource_type: str, target_resource_id: str,
    observed_at: datetime, fields: tuple[ReconciliationField, ...], complete: bool,
) -> dict[str, Any]:
    return {
        "complete": complete,
        "fields": [_field_document(value) for value in fields],
        "observed_at": _timestamp(observed_at),
        "provider": provider,
        "resource_type": resource_type,
        "target_resource_id": target_resource_id,
    }


def normalize_observation(value: ProviderObservation) -> NormalizedObservation:
    if type(value) is not ProviderObservation:
        raise ContinuedOperationReconciliationError("provider observation is invalid.")
    volatile = frozenset(value.volatile_field_names)
    fields = tuple(field for field in value.fields if field.name not in volatile)
    document = _normalized_document(
        provider=value.provider, resource_type=value.resource_type,
        target_resource_id=value.target_resource_id, observed_at=value.observed_at,
        fields=fields, complete=value.complete,
    )
    digest_value = sha256(_canonical({
        "domain": _OBSERVATION_DOMAIN, **document,
    })).hexdigest()
    return NormalizedObservation(
        value.provider, value.resource_type, value.target_resource_id,
        value.observed_at, fields, value.complete, digest_value,
    )


class InMemoryAuthoritativeExecutionEvidenceRepository:
    def __init__(self, values: tuple[AuthoritativeExecutionEvidence, ...] = ()) -> None:
        self._values = {value.evidence_reference: value for value in values}
        self._lock = Lock()

    def get_committed(self, reference: str) -> AuthoritativeExecutionEvidence | None:
        with self._lock:
            return self._values.get(reference)


class InMemoryOutcomeVerificationManifestRepository:
    def __init__(self, values: tuple[OutcomeVerificationManifest, ...] = ()) -> None:
        self._values = {value.reference: value for value in values}

    def get(self, reference: str) -> OutcomeVerificationManifest | None:
        return self._values.get(reference)


class ObserverRegistry:
    """Exact-match, versioned registry for read-only observer adapters."""

    def __init__(self, observers: tuple[ContinuedOperationObserver, ...] = ()) -> None:
        self._observers = observers

    def resolve(
        self, *, identity: str, version: str, provider: str, resource_type: str,
        operation_reference: str, manifest_version: str, required_capability: str,
    ) -> tuple[ContinuedOperationObserver | None, Reason | None]:
        candidates = tuple(observer for observer in self._observers if (
            getattr(observer, "identity", None) == identity
            and getattr(observer, "version", None) == version
            and getattr(observer, "provider", None) == provider
            and getattr(observer, "resource_type", None) == resource_type
            and getattr(observer, "operation_reference", None) == operation_reference
            and getattr(observer, "manifest_version", None) == manifest_version
        ))
        if not candidates:
            return None, Reason.OBSERVER_NOT_FOUND
        if len(candidates) != 1:
            return None, Reason.OBSERVER_AMBIGUOUS
        observer = candidates[0]
        if getattr(observer, "revoked", None) is not False:
            return None, Reason.OBSERVER_REVOKED
        if getattr(observer, "enabled", None) is not True:
            return None, Reason.OBSERVER_DISABLED
        if getattr(observer, "read_only", None) is not True:
            return None, Reason.OBSERVER_NOT_READ_ONLY
        capabilities = getattr(observer, "capabilities", None)
        if (not isinstance(capabilities, frozenset) or
                required_capability not in capabilities):
            return None, Reason.OBSERVER_CAPABILITY_MISMATCH
        return observer, None


class InMemoryReconciliationEvidenceRepository:
    """Thread-safe reference repository with immutable exact-retry behavior."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._records: dict[str, tuple[str, ContinuedOperationReconciliationResult | None]] = {}

    def claim(self, *, idempotency_key: str, request_digest: str) -> AtomicReconciliationClaim:
        with self._lock:
            current = self._records.get(idempotency_key)
            if current is None:
                self._records[idempotency_key] = (request_digest, None)
                return AtomicReconciliationClaim(ReconciliationClaimState.NEW)
            existing_digest, result = current
            if existing_digest != request_digest:
                return AtomicReconciliationClaim(ReconciliationClaimState.CONFLICT)
            if result is None:
                return AtomicReconciliationClaim(ReconciliationClaimState.IN_PROGRESS)
            return AtomicReconciliationClaim(ReconciliationClaimState.REPLAY, result)

    def commit(
        self, *, idempotency_key: str, request_digest: str,
        result: ContinuedOperationReconciliationResult,
    ) -> None:
        with self._lock:
            current = self._records.get(idempotency_key)
            if current is None or current[0] != request_digest:
                raise ReconciliationPersistenceError("reconciliation claim is unavailable")
            if current[1] is not None and current[1] != result:
                raise ReconciliationPersistenceError("reconciliation evidence is immutable")
            self._records[idempotency_key] = (request_digest, result)


def _attestation_document(value: ContinuedOperationReconciliationAttestation) -> dict[str, Any]:
    document = asdict(value)
    document.pop("reconciliation_id")
    document.pop("reconciliation_digest")
    document["outcome"] = value.outcome.value
    document["reason_code"] = value.reason_code.value
    document["observed_at"] = _timestamp(value.observed_at) if value.observed_at else None
    document["evidence_issued_at"] = _timestamp(value.evidence_issued_at)
    document["observation_digests"] = list(value.observation_digests)
    return document


def _result_document(value: ContinuedOperationReconciliationResult) -> dict[str, Any]:
    return {
        "attestation": None if value.attestation is None else {
            **_attestation_document(value.attestation),
            "reconciliation_id": value.attestation.reconciliation_id,
            "reconciliation_digest": value.attestation.reconciliation_digest,
        },
        "evaluated_at": _timestamp(value.evaluated_at),
        "execution_attempt_id": value.execution_attempt_id,
        "idempotent": value.idempotent,
        "operation_reference": value.operation_reference,
        "outcome": value.outcome.value,
        "reason_code": value.reason_code.value,
        "reconciliation_request_id": value.reconciliation_request_id,
    }


def _restore_result(document: dict[str, Any]) -> ContinuedOperationReconciliationResult:
    raw_attestation = document["attestation"]
    attestation = None
    if raw_attestation is not None:
        attestation = ContinuedOperationReconciliationAttestation(**{
            **raw_attestation,
            "outcome": Outcome(raw_attestation["outcome"]),
            "reason_code": Reason(raw_attestation["reason_code"]),
            "observed_at": (_parse_time(raw_attestation["observed_at"])
                            if raw_attestation["observed_at"] else None),
            "evidence_issued_at": _parse_time(raw_attestation["evidence_issued_at"]),
            "observation_digests": tuple(raw_attestation["observation_digests"]),
        })
    return ContinuedOperationReconciliationResult(
        reconciliation_request_id=document["reconciliation_request_id"],
        execution_attempt_id=document["execution_attempt_id"],
        operation_reference=document["operation_reference"],
        outcome=Outcome(document["outcome"]), reason_code=Reason(document["reason_code"]),
        evaluated_at=_parse_time(document["evaluated_at"]), attestation=attestation,
        idempotent=document["idempotent"],
    )


class SqliteReconciliationEvidenceRepository:
    """Durable append-only ATL-A.28 repository using SQLite transactions."""

    def __init__(self, path: str | Path) -> None:
        self._path = str(path)
        with self._connect() as connection:
            connection.execute("""CREATE TABLE IF NOT EXISTS continued_operation_reconciliation (
                idempotency_key TEXT PRIMARY KEY,
                request_digest TEXT NOT NULL,
                result_json TEXT
            )""")

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._path, timeout=30)
        connection.execute("PRAGMA journal_mode=WAL")
        return connection

    def claim(self, *, idempotency_key: str, request_digest: str) -> AtomicReconciliationClaim:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT request_digest, result_json FROM continued_operation_reconciliation "
                "WHERE idempotency_key = ?", (idempotency_key,),
            ).fetchone()
            if row is None:
                connection.execute(
                    "INSERT INTO continued_operation_reconciliation VALUES (?, ?, NULL)",
                    (idempotency_key, request_digest),
                )
                connection.commit()
                return AtomicReconciliationClaim(ReconciliationClaimState.NEW)
            connection.rollback()
            if row[0] != request_digest:
                return AtomicReconciliationClaim(ReconciliationClaimState.CONFLICT)
            if row[1] is None:
                return AtomicReconciliationClaim(ReconciliationClaimState.IN_PROGRESS)
            return AtomicReconciliationClaim(
                ReconciliationClaimState.REPLAY, _restore_result(json.loads(row[1])),
            )
        except sqlite3.Error as error:
            try:
                connection.rollback()
            except sqlite3.Error:
                pass
            raise ReconciliationPersistenceError("reconciliation claim failed") from error
        finally:
            connection.close()

    def commit(
        self, *, idempotency_key: str, request_digest: str,
        result: ContinuedOperationReconciliationResult,
    ) -> None:
        payload = _canonical(_result_document(result)).decode("utf-8")
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT request_digest, result_json FROM continued_operation_reconciliation "
                "WHERE idempotency_key = ?", (idempotency_key,),
            ).fetchone()
            if row is None or row[0] != request_digest:
                connection.rollback()
                raise ReconciliationPersistenceError("reconciliation claim is unavailable")
            if row[1] is not None and row[1] != payload:
                connection.rollback()
                raise ReconciliationPersistenceError("reconciliation evidence is immutable")
            connection.execute(
                "UPDATE continued_operation_reconciliation SET result_json = ? "
                "WHERE idempotency_key = ? AND request_digest = ? AND result_json IS NULL",
                (payload, idempotency_key, request_digest),
            )
            connection.commit()
        except ReconciliationPersistenceError:
            raise
        except sqlite3.Error as error:
            try:
                connection.rollback()
            except sqlite3.Error:
                pass
            raise ReconciliationCommitStatusUnknown(
                "reconciliation commit status is unknown"
            ) from error
        finally:
            connection.close()


def _trusted_now(trusted_clock: Callable[[], datetime]) -> datetime | None:
    try:
        value = trusted_clock()
        if (not isinstance(value, datetime) or value.tzinfo is None or
                value.utcoffset() is None or value.microsecond):
            return None
        return value.astimezone(timezone.utc)
    except Exception:
        return None


def _trusted_permit(evidence: AuthoritativeExecutionEvidence) -> TrustedContinuedOperationPermit:
    record = evidence.consumption_record
    return TrustedContinuedOperationPermit(
        record.authorization_id, record.authorization_digest, record.enforcement_request_id,
        record.evidence_digest, record.request_binding_digest, record.deployment_id,
        record.consumer_id, record.enforcement_point_id, record.purpose,
        record.operation_reference, record.consumed_at, record.policy_reference,
        record.correlation_id,
    )


def _verify_evidence_binding(
    request: ContinuedOperationReconciliationRequest,
    evidence: AuthoritativeExecutionEvidence,
) -> bool:
    if not evidence.committed:
        return False
    execution_request = evidence.request
    record = evidence.consumption_record
    manifest = evidence.operation_manifest
    attestation = evidence.attestation
    if (
        evidence.evidence_reference != attestation.attestation_digest
        or request.execution_attestation_reference != evidence.evidence_reference
        or not verify_continued_operation_execution_attestation(attestation)
        or operation_manifest_digest(manifest) != execution_request.operation_manifest_digest
    ):
        return False
    command = canonicalize_execution_command(execution_request, _trusted_permit(evidence), manifest)
    return all((
        command.command_digest == attestation.execution_command_digest,
        execution_request.execution_attempt_id == request.execution_attempt_id == attestation.execution_attempt_id,
        execution_request.enforcement_request_id == request.enforcement_request_id == record.enforcement_request_id,
        execution_request.authorization_id == request.authorization_id == record.authorization_id == attestation.authorization_id,
        execution_request.deployment_id == request.deployment_id == record.deployment_id == attestation.deployment_id,
        execution_request.consumer_id == request.consumer_id == record.consumer_id == attestation.consumer_id,
        execution_request.enforcement_point_id == request.enforcement_point_id == record.enforcement_point_id == attestation.enforcement_point_id,
        execution_request.purpose == request.purpose == record.purpose == attestation.purpose,
        execution_request.operation_reference == request.operation_reference == record.operation_reference == attestation.operation_reference,
        execution_request.operation_manifest_reference == request.operation_manifest_reference == manifest.reference,
        execution_request.operation_manifest_digest == request.operation_manifest_digest == attestation.operation_manifest_digest,
        manifest.canonical_operation_input_digest == request.canonical_parameter_digest,
        execution_request.requested_adapter == request.execution_adapter_identity == attestation.adapter_identity,
        execution_request.adapter_contract_version == request.execution_adapter_version == attestation.adapter_contract_version,
        execution_request.correlation_id == request.correlation_id == record.correlation_id == attestation.correlation_id,
        record.evidence_digest == attestation.enforcement_evidence_digest,
    ))


def _semantic_fields(observation: NormalizedObservation) -> tuple[tuple[str, str, Any], ...]:
    return tuple((field.name, field.state.value, field.value) for field in observation.fields)


def _compare(
    expected: ExpectedPostcondition, observations: tuple[NormalizedObservation, ...],
) -> tuple[Outcome, Reason]:
    if not observations:
        return Outcome.INDETERMINATE, Reason.OBSERVATION_UNAVAILABLE
    semantics = {_semantic_fields(value) for value in observations}
    if len(semantics) != 1:
        return Outcome.INDETERMINATE, Reason.OBSERVATIONS_CONFLICT
    observation = max(observations, key=lambda value: value.observed_at)
    if not observation.complete or any(
        field.state is ObservationValueState.UNKNOWN for field in observation.fields
    ):
        return Outcome.INDETERMINATE, Reason.OBSERVATION_PARTIAL
    actual = {field.name: field for field in observation.fields}
    expected_fields = {field.name: field for field in expected.fields}
    exists = actual.get("exists")
    if expected.kind in {PostconditionKind.RESOURCE_EXISTS, PostconditionKind.RESOURCE_ABSENT}:
        if (exists is None or exists.state is not ObservationValueState.PRESENT or
                type(exists.value) is not bool):
            return Outcome.INDETERMINATE, Reason.OBSERVATION_PARTIAL
        wanted = expected.kind is PostconditionKind.RESOURCE_EXISTS
        return ((Outcome.VERIFIED, Reason.EXPECTED_STATE_OBSERVED) if exists.value is wanted else
                (Outcome.MISMATCH, Reason.EXPECTED_STATE_MISMATCH))
    if expected.kind is PostconditionKind.REVISION_ADVANCED:
        baseline = expected_fields.get("revision")
        observed = actual.get("revision")
        if (baseline is None or observed is None or
                baseline.state is not ObservationValueState.PRESENT or
                observed.state is not ObservationValueState.PRESENT or
                type(baseline.value) is not int or type(observed.value) is not int):
            return Outcome.INDETERMINATE, Reason.OBSERVATION_PARTIAL
        return ((Outcome.VERIFIED, Reason.EXPECTED_STATE_OBSERVED)
                if observed.value > baseline.value else
                (Outcome.MISMATCH, Reason.EXPECTED_STATE_MISMATCH))
    for name, wanted in expected_fields.items():
        observed = actual.get(name)
        if observed is None or observed.state is not ObservationValueState.PRESENT:
            return Outcome.INDETERMINATE, Reason.OBSERVATION_PARTIAL
        if wanted.state is not ObservationValueState.PRESENT:
            return Outcome.INVALID, Reason.POSTCONDITION_UNSUPPORTED
        if observed.value != wanted.value:
            return Outcome.MISMATCH, Reason.EXPECTED_STATE_MISMATCH
    return Outcome.VERIFIED, Reason.EXPECTED_STATE_OBSERVED


def _attestation(
    request: ContinuedOperationReconciliationRequest,
    evidence: AuthoritativeExecutionEvidence,
    manifest: OutcomeVerificationManifest,
    policy: ContinuedOperationVerificationPolicy,
    expected: ExpectedPostcondition,
    observer: ContinuedOperationObserver | None,
    observations: tuple[NormalizedObservation, ...],
    outcome: Outcome, reason: Reason, issued_at: datetime,
) -> ContinuedOperationReconciliationAttestation:
    observed_at = max((value.observed_at for value in observations), default=None)
    values = {
        "authorization_id": request.authorization_id,
        "canonical_parameter_digest": request.canonical_parameter_digest,
        "consumer_id": request.consumer_id,
        "consumption_id": evidence.consumption_record.evidence_digest,
        "contract_version": CONTINUED_OPERATION_RECONCILIATION_ATTESTATION_VERSION,
        "correlation_id": request.correlation_id,
        "deployment_id": request.deployment_id,
        "domain": _ATTESTATION_DOMAIN,
        "enforcement_point_id": request.enforcement_point_id,
        "evidence_issued_at": _timestamp(issued_at),
        "execution_adapter_identity": request.execution_adapter_identity,
        "execution_adapter_version": request.execution_adapter_version,
        "execution_attestation_reference": request.execution_attestation_reference,
        "execution_attempt_id": request.execution_attempt_id,
        "expected_postcondition_digest": expected.expected_postcondition_digest,
        "observation_digests": sorted(value.observation_digest for value in observations),
        "observed_at": _timestamp(observed_at) if observed_at else None,
        "observer_identity": getattr(observer, "identity", None),
        "observer_version": getattr(observer, "version", None),
        "operation_manifest_reference": request.operation_manifest_reference,
        "operation_manifest_version": evidence.operation_manifest.version,
        "operation_reference": request.operation_reference,
        "outcome": outcome.value,
        "purpose": request.purpose,
        "reason_code": reason.value,
        "reconciliation_request_id": request.reconciliation_request_id,
        "target_resource_id": request.target_resource_id,
        "verification_manifest_reference": manifest.reference,
        "verification_manifest_version": manifest.version,
        "verification_policy_reference": policy.reference,
        "verification_round_id": request.verification_round_id,
    }
    digest_value = sha256(_canonical(values)).hexdigest()
    reconciliation_id = sha256(_canonical({
        **values, "reconciliation_digest": digest_value,
    })).hexdigest()
    public = {key: value for key, value in values.items() if key != "domain"}
    public.update({
        "outcome": outcome, "reason_code": reason,
        "evidence_issued_at": issued_at, "observed_at": observed_at,
        "observation_digests": tuple(values["observation_digests"]),
    })
    return ContinuedOperationReconciliationAttestation(
        reconciliation_id=reconciliation_id, reconciliation_digest=digest_value, **public,
    )


def verify_reconciliation_attestation(
    value: ContinuedOperationReconciliationAttestation,
) -> bool:
    if type(value) is not ContinuedOperationReconciliationAttestation:
        return False
    document = _attestation_document(value)
    values = {"domain": _ATTESTATION_DOMAIN, **document}
    digest_value = sha256(_canonical(values)).hexdigest()
    identity = sha256(_canonical({
        **values, "reconciliation_digest": digest_value,
    })).hexdigest()
    return value.reconciliation_digest == digest_value and value.reconciliation_id == identity


def _result(
    request: ContinuedOperationReconciliationRequest,
    outcome: Outcome, reason: Reason, evaluated_at: datetime,
    attestation: ContinuedOperationReconciliationAttestation | None = None,
) -> ContinuedOperationReconciliationResult:
    return ContinuedOperationReconciliationResult(
        request.reconciliation_request_id, request.execution_attempt_id,
        request.operation_reference, outcome, reason, evaluated_at, attestation,
    )


def _commit_result(
    request: ContinuedOperationReconciliationRequest, request_digest: str,
    repository: ReconciliationEvidenceRepository,
    result: ContinuedOperationReconciliationResult,
) -> ContinuedOperationReconciliationResult:
    try:
        repository.commit(
            idempotency_key=request.idempotency_key,
            request_digest=request_digest, result=result,
        )
        return result
    except ReconciliationCommitStatusUnknown:
        return _result(
            request, Outcome.INDETERMINATE, Reason.COMMIT_STATUS_UNKNOWN,
            result.evaluated_at,
        )
    except Exception:
        return _result(
            request, Outcome.INDETERMINATE, Reason.RECONCILIATION_STATE_UNAVAILABLE,
            result.evaluated_at,
        )


def reconcile_continued_operation(
    request: ContinuedOperationReconciliationRequest, *,
    execution_repository: AuthoritativeExecutionEvidenceRepository,
    manifest_repository: OutcomeVerificationManifestRepository,
    policy: ContinuedOperationVerificationPolicy,
    observer_registry: ObserverRegistry,
    evidence_repository: ReconciliationEvidenceRepository,
    trusted_clock: Callable[[], datetime],
) -> ContinuedOperationReconciliationResult:
    """Observe and reconcile one A.27 execution without invoking or repairing it."""
    if type(request) is not ContinuedOperationReconciliationRequest:
        raise ContinuedOperationReconciliationError("an exact reconciliation request is required.")
    now = _trusted_now(trusted_clock)
    if now is None:
        return _result(
            request, Outcome.INDETERMINATE, Reason.UNTRUSTED_TIME_SOURCE, request.requested_at,
        )
    if request.requested_at > now:
        return _result(request, Outcome.INVALID, Reason.OBSERVATION_TIME_INVALID, now)
    digest_value = reconciliation_request_digest(request)
    try:
        claim = evidence_repository.claim(
            idempotency_key=request.idempotency_key, request_digest=digest_value,
        )
    except Exception:
        return _result(request, Outcome.INDETERMINATE, Reason.RECONCILIATION_STATE_UNAVAILABLE, now)
    if claim.state is ReconciliationClaimState.REPLAY and claim.result is not None:
        return claim.result
    if claim.state is ReconciliationClaimState.CONFLICT:
        return _result(request, Outcome.INVALID, Reason.RECONCILIATION_REQUEST_CONFLICT, now)
    if claim.state is ReconciliationClaimState.IN_PROGRESS:
        return _result(request, Outcome.INDETERMINATE, Reason.RECONCILIATION_IN_PROGRESS, now)
    if claim.state is not ReconciliationClaimState.NEW:
        return _result(request, Outcome.INDETERMINATE, Reason.RECONCILIATION_STATE_UNAVAILABLE, now)
    try:
        evidence = execution_repository.get_committed(request.execution_attestation_reference)
    except Exception:
        result = _result(request, Outcome.INDETERMINATE, Reason.EXECUTION_EVIDENCE_UNAVAILABLE, now)
        return _commit_result(request, digest_value, evidence_repository, result)
    if evidence is None:
        result = _result(request, Outcome.INVALID, Reason.EXECUTION_EVIDENCE_NOT_FOUND, now)
        return _commit_result(request, digest_value, evidence_repository, result)
    if type(evidence) is not AuthoritativeExecutionEvidence:
        result = _result(request, Outcome.INVALID, Reason.EXECUTION_EVIDENCE_INVALID, now)
        return _commit_result(request, digest_value, evidence_repository, result)
    try:
        binding_valid = _verify_evidence_binding(request, evidence)
    except Exception:
        binding_valid = False
    if not binding_valid:
        result = _result(request, Outcome.INVALID, Reason.EXECUTION_BINDING_MISMATCH, now)
        return _commit_result(request, digest_value, evidence_repository, result)
    try:
        manifest = manifest_repository.get(request.verification_manifest_reference)
    except Exception:
        result = _result(request, Outcome.INDETERMINATE, Reason.MANIFEST_NOT_FOUND, now)
        return _commit_result(request, digest_value, evidence_repository, result)
    if manifest is None:
        result = _result(request, Outcome.INVALID, Reason.MANIFEST_NOT_FOUND, now)
        return _commit_result(request, digest_value, evidence_repository, result)
    if type(manifest) is not OutcomeVerificationManifest:
        result = _result(request, Outcome.INVALID, Reason.MANIFEST_INVALID, now)
        return _commit_result(request, digest_value, evidence_repository, result)
    if request.verification_policy_reference != policy.reference:
        result = _result(request, Outcome.INVALID, Reason.POLICY_MISMATCH, now)
        return _commit_result(request, digest_value, evidence_repository, result)
    if (
        request.target_resource_id != manifest.target_resource_id
        or request.canonical_parameter_digest != manifest.canonical_parameter_digest
        or request.requested_observer_version != manifest.observer_version
    ):
        result = _result(request, Outcome.INVALID, Reason.MANIFEST_INVALID, now)
        return _commit_result(request, digest_value, evidence_repository, result)
    try:
        expected = derive_expected_postcondition(evidence, manifest)
    except Exception:
        result = _result(request, Outcome.INVALID, Reason.MANIFEST_INVALID, now)
        return _commit_result(request, digest_value, evidence_repository, result)
    deadline = evidence.attestation.started_at + timedelta(seconds=policy.verification_window_seconds)
    if now > deadline:
        attestation = _attestation(
            request, evidence, manifest, policy, expected, None, (),
            Outcome.INDETERMINATE, Reason.VERIFICATION_WINDOW_EXPIRED, now,
        )
        result = _result(
            request, Outcome.INDETERMINATE, Reason.VERIFICATION_WINDOW_EXPIRED, now, attestation,
        )
        return _commit_result(request, digest_value, evidence_repository, result)
    observer, observer_error = observer_registry.resolve(
        identity=request.requested_observer_identity,
        version=request.requested_observer_version,
        provider=manifest.provider, resource_type=manifest.resource_type,
        operation_reference=request.operation_reference,
        manifest_version=manifest.operation_manifest_version,
        required_capability=manifest.required_observation_capability,
    )
    if observer is None:
        reason = observer_error or Reason.OBSERVER_NOT_FOUND
        attestation = _attestation(
            request, evidence, manifest, policy, expected, None, (), Outcome.INVALID, reason, now,
        )
        result = _result(request, Outcome.INVALID, reason, now, attestation)
        return _commit_result(request, digest_value, evidence_repository, result)
    observation_deadline = min(
        deadline, now + timedelta(seconds=policy.observation_timeout_seconds),
    )
    observation_request = ObservationRequest(
        request.execution_attempt_id, manifest.provider, manifest.resource_type,
        request.operation_reference, request.target_resource_id,
        manifest.required_observation_capability, evidence.attestation.started_at,
        observation_deadline, expected.expected_postcondition_digest,
    )
    try:
        provider_observations = observer.observe(observation_request)
        if (type(provider_observations) is not tuple or
                any(type(value) is not ProviderObservation for value in provider_observations)):
            raise TypeError
        observations = tuple(sorted(
            (normalize_observation(value) for value in provider_observations),
            key=lambda value: (value.observed_at, value.observation_digest),
        ))
    except Exception:
        observations = ()
        outcome, reason = Outcome.INDETERMINATE, Reason.OBSERVATION_UNAVAILABLE
    else:
        after = _trusted_now(trusted_clock)
        if after is None:
            outcome, reason = Outcome.INDETERMINATE, Reason.UNTRUSTED_TIME_SOURCE
        elif after > observation_deadline:
            outcome, reason = Outcome.INDETERMINATE, Reason.OBSERVATION_UNAVAILABLE
        elif any(
            value.provider != manifest.provider
            or value.resource_type != manifest.resource_type
            or value.target_resource_id != manifest.target_resource_id
            for value in observations
        ):
            outcome, reason = Outcome.INVALID, Reason.OBSERVATION_INVALID
        elif any(value.observed_at > after for value in observations):
            outcome, reason = Outcome.INVALID, Reason.OBSERVATION_TIME_INVALID
        elif any(value.observed_at < evidence.attestation.started_at for value in observations):
            outcome, reason = Outcome.INDETERMINATE, Reason.OBSERVATION_PRECEDES_EXECUTION
        elif any(value.observed_at > deadline for value in observations):
            outcome, reason = Outcome.INDETERMINATE, Reason.VERIFICATION_WINDOW_EXPIRED
        elif any(
            after - value.observed_at > timedelta(
                seconds=policy.maximum_observation_age_seconds,
            ) for value in observations
        ):
            outcome, reason = Outcome.INDETERMINATE, Reason.OBSERVATION_STALE
        else:
            outcome, reason = _compare(expected, observations)
    issued_at = _trusted_now(trusted_clock) or now
    attestation = _attestation(
        request, evidence, manifest, policy, expected, observer, observations,
        outcome, reason, issued_at,
    )
    result = _result(request, outcome, reason, issued_at, attestation)
    return _commit_result(request, digest_value, evidence_repository, result)


def public_continued_operation_reconciliation(
    result: ContinuedOperationReconciliationResult,
) -> PublicContinuedOperationReconciliationV1:
    if type(result) is not ContinuedOperationReconciliationResult:
        raise ContinuedOperationReconciliationError("an exact reconciliation result is required.")
    attestation = result.attestation
    return PublicContinuedOperationReconciliationV1(
        reconciliation_id=attestation.reconciliation_id if attestation else None,
        execution_attempt_id=result.execution_attempt_id,
        operation_reference=result.operation_reference,
        outcome=result.outcome, reason_code=result.reason_code,
        observed_at=attestation.observed_at if attestation else None,
        evidence_issued_at=attestation.evidence_issued_at if attestation else None,
    )


__all__ = [
    "InMemoryAuthoritativeExecutionEvidenceRepository",
    "InMemoryOutcomeVerificationManifestRepository",
    "InMemoryReconciliationEvidenceRepository", "ObserverRegistry",
    "ReconciliationCommitStatusUnknown", "ReconciliationPersistenceError",
    "SqliteReconciliationEvidenceRepository", "derive_expected_postcondition",
    "normalize_observation", "public_continued_operation_reconciliation",
    "reconcile_continued_operation", "reconciliation_request_digest",
    "reconciliation_request_document", "translate_untrusted_reconciliation_request",
    "verify_reconciliation_attestation",
]
