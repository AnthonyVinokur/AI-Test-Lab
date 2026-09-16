"""ATL-A.26 fail-closed continued-operation enforcement and atomic consumption."""
from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, replace
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from threading import Lock
from typing import Any, Callable, Mapping

from src.reference_architecture_continued_operation_enforcement_contract import (
    CONTINUED_OPERATION_ENFORCEMENT_CONTRACT_VERSION,
    AtomicConsumptionResult,
    AtomicConsumptionState,
    ContinuedOperationAuthorizationRepository,
    ContinuedOperationConsumptionLedger,
    ContinuedOperationConsumptionRecord,
    ContinuedOperationEnforcementBinding,
    ContinuedOperationEnforcementError,
    ContinuedOperationEnforcementEvidence,
    ContinuedOperationEnforcementPolicy,
    ContinuedOperationEnforcementReasonCode as Reason,
    ContinuedOperationEnforcementRequest,
    ContinuedOperationEnforcementResult,
    ContinuedOperationEnforcementState as State,
    PublicContinuedOperationEnforcementV1,
    StoredContinuedOperationAuthorization,
)
from src.reference_architecture_deployment_continued_operation_authorization import (
    continued_operation_authorization_document,
    verify_continued_operation_authorization,
)
from src.reference_architecture_deployment_continued_operation_authorization_contract import (
    ContinuedOperationLifecycleState as Lifecycle,
)


_BINDING_DOMAIN = "ai-test-lab:atl-a.26:enforcement-binding:v1"
_EVIDENCE_DOMAIN = "ai-test-lab:atl-a.26:enforcement-evidence:v1"


class ConsumptionPersistenceError(RuntimeError):
    """The consumption transaction definitely did not commit."""


class ConsumptionOutcomeUnknownError(RuntimeError):
    """The store cannot establish whether the transaction committed."""


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                          allow_nan=False).encode("utf-8")
    except (TypeError, ValueError):
        raise ContinuedOperationEnforcementError("enforcement canonical payload is invalid.") from None


def _timestamp(value: datetime) -> str:
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_time(value: object) -> datetime:
    if type(value) is not str or len(value) != 20 or not value.endswith("Z"):
        raise ValueError
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def continued_operation_authorization_digest(value: StoredContinuedOperationAuthorization | Any) -> str:
    artifact = value.artifact if type(value) is StoredContinuedOperationAuthorization else value
    return sha256(_canonical(continued_operation_authorization_document(artifact))).hexdigest()


def enforcement_request_document(value: ContinuedOperationEnforcementRequest) -> dict[str, Any]:
    if type(value) is not ContinuedOperationEnforcementRequest:
        raise ContinuedOperationEnforcementError("an exact enforcement request is required.")
    return {
        "authorization_digest": value.authorization_digest,
        "authorization_reference": value.authorization_reference,
        "consumer_id": value.consumer_id,
        "correlation_id": value.correlation_id,
        "deployment_id": value.deployment_id,
        "enforcement_point_id": value.enforcement_point_id,
        "enforcement_request_id": value.enforcement_request_id,
        "operation_reference": value.operation_reference,
        "policy_reference": value.policy_reference,
        "purpose": value.purpose,
        "requested_at": _timestamp(value.requested_at),
        "schema_version": value.schema_version,
    }


def translate_untrusted_enforcement_request(
    value: bytes | str | Mapping[str, Any],
) -> ContinuedOperationEnforcementRequest:
    try:
        raw: bytes | None
        if type(value) is bytes:
            raw, document = value, json.loads(value)
        elif type(value) is str:
            raw, document = value.encode("utf-8"), json.loads(value)
        elif type(value) is dict:
            raw, document = None, dict(value)
        else:
            raise ValueError
        fields = {
            "authorization_reference", "authorization_digest", "enforcement_request_id",
            "deployment_id", "consumer_id", "enforcement_point_id", "purpose",
            "requested_at", "operation_reference", "policy_reference", "correlation_id",
            "schema_version",
        }
        if type(document) is not dict or set(document) != fields:
            raise ValueError
        request = ContinuedOperationEnforcementRequest(
            **{**document, "requested_at": _parse_time(document["requested_at"])}
        )
        if raw is not None and raw != _canonical(enforcement_request_document(request)):
            raise ValueError
        return request
    except Exception as error:
        raise ContinuedOperationEnforcementError("enforcement request is invalid.") from error


def canonical_enforcement_binding(value: ContinuedOperationEnforcementRequest) -> bytes:
    return _canonical({"domain": _BINDING_DOMAIN, **enforcement_request_document(value)})


def enforcement_binding_digest(value: ContinuedOperationEnforcementRequest) -> str:
    return sha256(canonical_enforcement_binding(value)).hexdigest()


class InMemoryContinuedOperationAuthorizationRepository:
    """Thread-safe reference repository; production adapters must durably retain artifacts."""

    def __init__(self, values: tuple[StoredContinuedOperationAuthorization, ...] = ()) -> None:
        self._lock = Lock()
        self._values = {item.reference: item for item in values}

    def get(self, reference: str) -> StoredContinuedOperationAuthorization | None:
        with self._lock:
            return self._values.get(reference)

    def put(self, value: StoredContinuedOperationAuthorization) -> None:
        if type(value) is not StoredContinuedOperationAuthorization:
            raise ContinuedOperationEnforcementError("stored authorization is invalid.")
        with self._lock:
            prior = self._values.get(value.reference)
            if prior is not None and prior.artifact_digest != value.artifact_digest:
                raise ContinuedOperationEnforcementError("authorization reference is immutable.")
            self._values[value.reference] = value

    def set_lifecycle(self, reference: str, lifecycle: Lifecycle, *, upstream_active: bool) -> None:
        with self._lock:
            current = self._values[reference]
            if current.lifecycle_state is not Lifecycle.ACTIVE and lifecycle is Lifecycle.ACTIVE:
                raise ContinuedOperationEnforcementError("authorization lifecycle cannot reactivate.")
            self._values[reference] = replace(
                current, lifecycle_state=lifecycle, upstream_active=upstream_active
            )


def _same_attempt(record: ContinuedOperationConsumptionRecord,
                  request: ContinuedOperationEnforcementRequest, request_digest: str) -> bool:
    return (
        record.authorization_digest == request.authorization_digest and
        record.enforcement_request_id == request.enforcement_request_id and
        record.request_binding_digest == request_digest and
        record.deployment_id == request.deployment_id and
        record.consumer_id == request.consumer_id and
        record.enforcement_point_id == request.enforcement_point_id and
        record.purpose == request.purpose and
        record.operation_reference == request.operation_reference and
        record.policy_reference == request.policy_reference
    )


class InMemoryContinuedOperationConsumptionLedger:
    """Atomic reference ledger. A durable adapter must preserve the same uniqueness rules."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._by_authorization: dict[str, ContinuedOperationConsumptionRecord] = {}
        self._by_request: dict[str, ContinuedOperationConsumptionRecord] = {}

    def consume(self, *, authorization: StoredContinuedOperationAuthorization,
                request: ContinuedOperationEnforcementRequest, request_binding_digest: str,
                consumed_at: datetime,
                lifecycle_recheck: Callable[[], Reason | None],
                record_factory: Callable[[str], ContinuedOperationConsumptionRecord],
                ) -> AtomicConsumptionResult:
        with self._lock:
            lifecycle_reason = lifecycle_recheck()
            if lifecycle_reason is not None:
                return AtomicConsumptionResult(AtomicConsumptionState.LIFECYCLE_BLOCKED, None,
                                               lifecycle_reason=lifecycle_reason)
            by_request = self._by_request.get(request.enforcement_request_id)
            if by_request is not None:
                if _same_attempt(by_request, request, request_binding_digest):
                    return AtomicConsumptionResult(AtomicConsumptionState.IDEMPOTENT, by_request,
                                                   by_request)
                return AtomicConsumptionResult(AtomicConsumptionState.REQUEST_CONFLICT, None,
                                               by_request)
            prior = self._by_authorization.get(authorization.artifact.authorization_id)
            if prior is not None:
                return AtomicConsumptionResult(AtomicConsumptionState.ALREADY_CONSUMED, None, prior)
            record = record_factory(sha256(_canonical({
                "authorization_id": authorization.artifact.authorization_id,
                "enforcement_request_id": request.enforcement_request_id,
                "request_binding_digest": request_binding_digest,
            })).hexdigest())
            self._by_authorization[record.authorization_id] = record
            self._by_request[record.enforcement_request_id] = record
            return AtomicConsumptionResult(AtomicConsumptionState.CONSUMED, record)

    def get(self, authorization_id: str) -> ContinuedOperationConsumptionRecord | None:
        with self._lock:
            return self._by_authorization.get(authorization_id)


class SqliteContinuedOperationConsumptionLedger:
    """Durable single-winner ledger using one transaction and storage-level unique keys."""

    def __init__(self, path: str | Path) -> None:
        self._path = str(path)
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute(
                """CREATE TABLE IF NOT EXISTS continued_operation_consumption (
                authorization_id TEXT PRIMARY KEY,
                enforcement_request_id TEXT NOT NULL UNIQUE,
                request_binding_digest TEXT NOT NULL,
                record_json TEXT NOT NULL
                )"""
            )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._path, timeout=30, isolation_level=None)

    @staticmethod
    def _document(record: ContinuedOperationConsumptionRecord) -> dict[str, Any]:
        document = asdict(record)
        document["consumed_at"] = _timestamp(record.consumed_at)
        return document

    @staticmethod
    def _record(raw: str) -> ContinuedOperationConsumptionRecord:
        document = json.loads(raw)
        document["consumed_at"] = _parse_time(document["consumed_at"])
        return ContinuedOperationConsumptionRecord(**document)

    def consume(self, *, authorization: StoredContinuedOperationAuthorization,
                request: ContinuedOperationEnforcementRequest, request_binding_digest: str,
                consumed_at: datetime,
                lifecycle_recheck: Callable[[], Reason | None],
                record_factory: Callable[[str], ContinuedOperationConsumptionRecord],
                ) -> AtomicConsumptionResult:
        connection = self._connect()
        committed = False
        commit_started = False
        try:
            connection.execute("BEGIN IMMEDIATE")
            lifecycle_reason = lifecycle_recheck()
            if lifecycle_reason is not None:
                connection.rollback()
                return AtomicConsumptionResult(AtomicConsumptionState.LIFECYCLE_BLOCKED, None,
                                               lifecycle_reason=lifecycle_reason)
            request_row = connection.execute(
                "SELECT record_json FROM continued_operation_consumption WHERE enforcement_request_id = ?",
                (request.enforcement_request_id,),
            ).fetchone()
            if request_row:
                prior = self._record(request_row[0])
                connection.rollback()
                state = (AtomicConsumptionState.IDEMPOTENT if
                         _same_attempt(prior, request, request_binding_digest) else
                         AtomicConsumptionState.REQUEST_CONFLICT)
                return AtomicConsumptionResult(state, prior if state is AtomicConsumptionState.IDEMPOTENT else None,
                                               prior)
            row = connection.execute(
                "SELECT record_json FROM continued_operation_consumption WHERE authorization_id = ?",
                (authorization.artifact.authorization_id,),
            ).fetchone()
            if row:
                prior = self._record(row[0])
                connection.rollback()
                return AtomicConsumptionResult(AtomicConsumptionState.ALREADY_CONSUMED, None, prior)
            evidence_digest = sha256(_canonical({
                "authorization_id": authorization.artifact.authorization_id,
                "enforcement_request_id": request.enforcement_request_id,
                "request_binding_digest": request_binding_digest,
            })).hexdigest()
            record = record_factory(evidence_digest)
            connection.execute(
                "INSERT INTO continued_operation_consumption VALUES (?, ?, ?, ?)",
                (record.authorization_id, record.enforcement_request_id,
                 record.request_binding_digest,
                 _canonical(self._document(record)).decode("utf-8")),
            )
            commit_started = True
            connection.commit()
            committed = True
            return AtomicConsumptionResult(AtomicConsumptionState.CONSUMED, record)
        except sqlite3.IntegrityError:
            connection.rollback()
            return self.consume(
                authorization=authorization, request=request,
                request_binding_digest=request_binding_digest, consumed_at=consumed_at,
                lifecycle_recheck=lifecycle_recheck, record_factory=record_factory,
            )
        except sqlite3.Error as error:
            try:
                connection.rollback()
            except sqlite3.Error:
                raise ConsumptionOutcomeUnknownError("consumption outcome is unknown") from error
            if committed or commit_started:
                raise ConsumptionOutcomeUnknownError("consumption outcome is unknown") from error
            raise ConsumptionPersistenceError("consumption transaction failed") from error
        finally:
            connection.close()

    def get(self, authorization_id: str) -> ContinuedOperationConsumptionRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT record_json FROM continued_operation_consumption WHERE authorization_id = ?",
                (authorization_id,),
            ).fetchone()
        return None if row is None else self._record(row[0])


def _evidence(
    request: ContinuedOperationEnforcementRequest, request_digest: str,
    *, authorization_id: str | None, lifecycle_state: str, consumption_result: str,
    state: State, reasons: tuple[Reason, ...], decided_at: datetime,
    previous: ContinuedOperationConsumptionRecord | None = None,
) -> ContinuedOperationEnforcementEvidence:
    values = {
        "authorization_digest": request.authorization_digest,
        "authorization_id": authorization_id,
        "authorization_reference": request.authorization_reference,
        "consumption_result": consumption_result,
        "correlation_id": request.correlation_id,
        "decided_at": _timestamp(decided_at),
        "domain": _EVIDENCE_DOMAIN,
        "enforcement_point_id": request.enforcement_point_id,
        "enforcement_request_id": request.enforcement_request_id,
        "enforcement_state": state.value,
        "lifecycle_state": lifecycle_state,
        "policy_reference": request.policy_reference,
        "previous_consumption_reference": previous.evidence_digest if previous else None,
        "reason_codes": [reason.value for reason in reasons],
        "request_binding_digest": request_digest,
        "schema_version": CONTINUED_OPERATION_ENFORCEMENT_CONTRACT_VERSION,
    }
    return ContinuedOperationEnforcementEvidence(
        sha256(_canonical(values)).hexdigest(), request.authorization_reference,
        request.authorization_digest, authorization_id, request.enforcement_request_id,
        request_digest, lifecycle_state, consumption_result, state, reasons, decided_at,
        request.policy_reference, request.enforcement_point_id,
        previous.evidence_digest if previous else None, request.correlation_id,
    )


def _result(request: ContinuedOperationEnforcementRequest, request_digest: str, *,
            authorization_id: str | None, state: State, reasons: tuple[Reason, ...],
            decided_at: datetime, lifecycle_state: str, consumption_result: str,
            record: ContinuedOperationConsumptionRecord | None = None,
            previous: ContinuedOperationConsumptionRecord | None = None,
            idempotent: bool = False) -> ContinuedOperationEnforcementResult:
    evidence = _evidence(
        request, request_digest, authorization_id=authorization_id,
        lifecycle_state=lifecycle_state, consumption_result=consumption_result,
        state=state, reasons=reasons, decided_at=decided_at, previous=previous,
    )
    return ContinuedOperationEnforcementResult(
        authorization_id, request.enforcement_request_id, request.deployment_id,
        request.purpose, state, reasons, decided_at, request_digest, evidence,
        record, idempotent,
    )


def _lifecycle_reason(stored: StoredContinuedOperationAuthorization | None,
                      request: ContinuedOperationEnforcementRequest,
                      policy: ContinuedOperationEnforcementPolicy,
                      now: datetime) -> Reason | None:
    if stored is None:
        return Reason.AUTHORIZATION_NOT_FOUND
    if stored.artifact_digest != request.authorization_digest:
        return Reason.AUTHORIZATION_DIGEST_MISMATCH
    if stored.lifecycle_state is Lifecycle.REVOKED:
        return Reason.AUTHORIZATION_REVOKED
    if stored.lifecycle_state is Lifecycle.SUPERSEDED:
        return Reason.AUTHORIZATION_SUPERSEDED
    if not stored.upstream_active:
        return Reason.UPSTREAM_STATE_INACTIVE
    if now < stored.artifact.not_before:
        return Reason.AUTHORIZATION_NOT_YET_VALID
    if now >= stored.artifact.expires_at:
        return Reason.AUTHORIZATION_EXPIRED
    if policy.lifecycle_state is not Lifecycle.ACTIVE or not policy.active_from <= now < policy.expires_at:
        return Reason.POLICY_MISMATCH
    return None


def _binding_reason(artifact: Any, request: ContinuedOperationEnforcementRequest,
                    policy: ContinuedOperationEnforcementPolicy) -> Reason | None:
    checks = (
        (artifact.deployment_id == request.deployment_id, Reason.DEPLOYMENT_MISMATCH),
        (artifact.consumer_id == request.consumer_id, Reason.CONSUMER_MISMATCH),
        (artifact.purpose == request.purpose, Reason.PURPOSE_MISMATCH),
        (artifact.authorization_policy_id == policy.accepted_authorization_policy_id and
         artifact.authorization_policy_version == policy.accepted_authorization_policy_version,
         Reason.POLICY_MISMATCH),
        (request.policy_reference == policy.policy_reference, Reason.POLICY_MISMATCH),
    )
    mismatch = next((reason for valid, reason in checks if not valid), None)
    if mismatch:
        return mismatch
    candidate = ContinuedOperationEnforcementBinding(
        request.deployment_id, request.consumer_id, request.enforcement_point_id,
        request.purpose, request.operation_reference,
    )
    if candidate in policy.bindings:
        return None
    same_except_point = any(
        item.deployment_id == request.deployment_id and item.consumer_id == request.consumer_id and
        item.purpose == request.purpose and item.operation_reference == request.operation_reference
        for item in policy.bindings
    )
    return Reason.ENFORCEMENT_POINT_MISMATCH if same_except_point else Reason.OPERATION_MISMATCH


def enforce_continued_operation(
    request: ContinuedOperationEnforcementRequest, *,
    authorization_repository: ContinuedOperationAuthorizationRepository,
    consumption_ledger: ContinuedOperationConsumptionLedger,
    policy: ContinuedOperationEnforcementPolicy,
    trusted_clock: Callable[[], datetime],
) -> ContinuedOperationEnforcementResult:
    if type(request) is not ContinuedOperationEnforcementRequest:
        raise ContinuedOperationEnforcementError("an exact enforcement request is required.")
    request_digest = enforcement_binding_digest(request)
    try:
        now = trusted_clock()
        if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None or now.microsecond:
            raise ValueError
        now = now.astimezone(timezone.utc)
    except Exception:
        fallback = request.requested_at
        return _result(
            request, request_digest, authorization_id=None, state=State.INDETERMINATE,
            reasons=(Reason.UNTRUSTED_TIME_SOURCE,), decided_at=fallback,
            lifecycle_state="unknown", consumption_result="not_attempted",
        )
    if request.requested_at > now:
        return _result(
            request, request_digest, authorization_id=None, state=State.BLOCKED,
            reasons=(Reason.INVALID_ENFORCEMENT_REQUEST,), decided_at=now,
            lifecycle_state="unknown", consumption_result="not_attempted",
        )
    try:
        stored = authorization_repository.get(request.authorization_reference)
    except Exception:
        return _result(
            request, request_digest, authorization_id=None, state=State.INDETERMINATE,
            reasons=(Reason.CONSUMPTION_STATE_UNAVAILABLE,), decided_at=now,
            lifecycle_state="unknown", consumption_result="not_attempted",
        )
    lifecycle_reason = _lifecycle_reason(stored, request, policy, now)
    if lifecycle_reason is not None:
        return _result(
            request, request_digest,
            authorization_id=stored.artifact.authorization_id if stored else None,
            state=State.BLOCKED, reasons=(lifecycle_reason,), decided_at=now,
            lifecycle_state=stored.lifecycle_state.value if stored else "missing",
            consumption_result="not_attempted",
        )
    assert stored is not None
    if continued_operation_authorization_digest(stored.artifact) != request.authorization_digest:
        return _result(
            request, request_digest, authorization_id=stored.artifact.authorization_id,
            state=State.BLOCKED, reasons=(Reason.AUTHORIZATION_DIGEST_MISMATCH,),
            decided_at=now, lifecycle_state=stored.lifecycle_state.value,
            consumption_result="not_attempted",
        )
    verification = verify_continued_operation_authorization(
        stored.artifact, resolved_key=stored.resolved_key, verification_time=now,
    )
    if not (verification.valid and verification.active and verification.applicable):
        normalized = {
            "authorization_expired": Reason.AUTHORIZATION_EXPIRED,
            "authorization_not_yet_valid": Reason.AUTHORIZATION_NOT_YET_VALID,
            "authorization_not_applicable": Reason.AUTHORIZATION_NOT_AUTHORIZED,
        }.get(verification.internal_reason.value if verification.internal_reason else "",
              Reason.AUTHORIZATION_NOT_AUTHORIZED)
        return _result(
            request, request_digest, authorization_id=stored.artifact.authorization_id,
            state=State.BLOCKED, reasons=(normalized,), decided_at=now,
            lifecycle_state=stored.lifecycle_state.value, consumption_result="not_attempted",
        )
    mismatch = _binding_reason(stored.artifact, request, policy)
    if mismatch is not None:
        return _result(
            request, request_digest, authorization_id=stored.artifact.authorization_id,
            state=State.BLOCKED, reasons=(mismatch,), decided_at=now,
            lifecycle_state=stored.lifecycle_state.value, consumption_result="not_attempted",
        )

    def recheck() -> Reason | None:
        current = authorization_repository.get(request.authorization_reference)
        if (current is not None and
                (current.artifact.authorization_id != stored.artifact.authorization_id or
                 current.artifact_digest != stored.artifact_digest)):
            return Reason.AUTHORIZATION_DIGEST_MISMATCH
        return _lifecycle_reason(current, request, policy, now)

    success_evidence_digest = _evidence(
        request, request_digest, authorization_id=stored.artifact.authorization_id,
        lifecycle_state=stored.lifecycle_state.value, consumption_result="committed",
        state=State.PERMITTED, reasons=(Reason.AUTHORIZATION_CONSUMED,), decided_at=now,
    ).evidence_digest

    def record_factory(_storage_reference: str) -> ContinuedOperationConsumptionRecord:
        return ContinuedOperationConsumptionRecord(
            stored.artifact.authorization_id, request.authorization_digest,
            request.enforcement_request_id, request_digest, request.deployment_id,
            request.consumer_id, request.enforcement_point_id, request.purpose,
            request.operation_reference, now, request.policy_reference,
            success_evidence_digest, request.correlation_id,
        )

    try:
        consumed = consumption_ledger.consume(
            authorization=stored, request=request, request_binding_digest=request_digest,
            consumed_at=now, lifecycle_recheck=recheck, record_factory=record_factory,
        )
    except ConsumptionPersistenceError:
        return _result(
            request, request_digest, authorization_id=stored.artifact.authorization_id,
            state=State.INDETERMINATE, reasons=(Reason.CONSUMPTION_PERSISTENCE_FAILED,),
            decided_at=now, lifecycle_state=stored.lifecycle_state.value,
            consumption_result="rolled_back",
        )
    except Exception:
        return _result(
            request, request_digest, authorization_id=stored.artifact.authorization_id,
            state=State.INDETERMINATE, reasons=(Reason.CONSUMPTION_STATE_UNAVAILABLE,),
            decided_at=now, lifecycle_state="unknown", consumption_result="unknown",
        )
    if consumed.state is AtomicConsumptionState.CONSUMED:
        return _result(
            request, request_digest, authorization_id=stored.artifact.authorization_id,
            state=State.PERMITTED, reasons=(Reason.AUTHORIZATION_CONSUMED,),
            decided_at=now, lifecycle_state=stored.lifecycle_state.value,
            consumption_result="committed", record=consumed.record,
        )
    if consumed.state is AtomicConsumptionState.IDEMPOTENT:
        assert consumed.record is not None
        return _result(
            request, request_digest, authorization_id=stored.artifact.authorization_id,
            state=State.PERMITTED, reasons=(Reason.IDEMPOTENT_RESULT_RETURNED,),
            decided_at=consumed.record.consumed_at, lifecycle_state=stored.lifecycle_state.value,
            consumption_result="idempotent", record=consumed.record,
            previous=consumed.previous_record, idempotent=True,
        )
    if consumed.state is AtomicConsumptionState.LIFECYCLE_BLOCKED:
        return _result(
            request, request_digest, authorization_id=stored.artifact.authorization_id,
            state=State.BLOCKED,
            reasons=(consumed.lifecycle_reason or Reason.UPSTREAM_STATE_INACTIVE,),
            decided_at=now, lifecycle_state="inactive", consumption_result="not_committed",
        )
    reason = (Reason.REQUEST_ID_CONFLICT if
              consumed.state is AtomicConsumptionState.REQUEST_CONFLICT else
              Reason.AUTHORIZATION_ALREADY_CONSUMED)
    return _result(
        request, request_digest, authorization_id=stored.artifact.authorization_id,
        state=State.BLOCKED, reasons=(reason,), decided_at=now,
        lifecycle_state=stored.lifecycle_state.value, consumption_result="conflict",
        previous=consumed.previous_record,
    )


def public_continued_operation_enforcement(
    result: ContinuedOperationEnforcementResult,
) -> PublicContinuedOperationEnforcementV1:
    if type(result) is not ContinuedOperationEnforcementResult:
        raise ContinuedOperationEnforcementError("an exact enforcement result is required.")
    return PublicContinuedOperationEnforcementV1(
        authorization_id=result.authorization_id,
        enforcement_request_id=result.enforcement_request_id,
        deployment_id=result.deployment_id,
        purpose=result.purpose,
        enforcement_state=result.enforcement_state,
        reason_codes=result.reason_codes,
        decided_at=result.decided_at,
        consumed_at=(result.consumption_record.consumed_at
                     if result.consumption_record else None),
        evidence_reference=result.evidence.evidence_digest,
        correlation_id=result.evidence.correlation_id,
    )


__all__ = [
    "ConsumptionOutcomeUnknownError", "ConsumptionPersistenceError",
    "InMemoryContinuedOperationAuthorizationRepository",
    "InMemoryContinuedOperationConsumptionLedger",
    "SqliteContinuedOperationConsumptionLedger",
    "canonical_enforcement_binding", "continued_operation_authorization_digest",
    "enforce_continued_operation", "enforcement_binding_digest",
    "enforcement_request_document", "public_continued_operation_enforcement",
    "translate_untrusted_enforcement_request",
]
