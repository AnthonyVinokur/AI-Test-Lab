"""ATL-A.27 protected-operation execution and outcome attestation."""
from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, replace
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path
from threading import Lock
from typing import Any, Callable, Mapping

from src.reference_architecture_continued_operation_enforcement_contract import (
    ContinuedOperationConsumptionRecord,
)
from src.reference_architecture_continued_operation_execution_contract import (
    CONTINUED_OPERATION_EXECUTION_ATTESTATION_VERSION,
    CONTINUED_OPERATION_EXECUTION_CONTRACT_VERSION,
    AtomicExecutionClaimResult,
    AtomicExecutionClaimState,
    ContinuedOperationAdapterResult,
    ContinuedOperationConsumptionRecordRepository,
    ContinuedOperationExecutionAdapter,
    ContinuedOperationExecutionAttestation,
    ContinuedOperationExecutionClaim,
    ContinuedOperationExecutionClaimState,
    ContinuedOperationExecutionCommand,
    ContinuedOperationExecutionError,
    ContinuedOperationExecutionOutcome as Outcome,
    ContinuedOperationExecutionPolicy,
    ContinuedOperationExecutionReasonCode as Reason,
    ContinuedOperationExecutionRequest,
    ContinuedOperationExecutionResult,
    ContinuedOperationExecutionStateStore,
    ProtectedOperationManifest,
    ProtectedOperationManifestRepository,
    PublicContinuedOperationExecutionV1,
    TrustedContinuedOperationPermit,
)


_COMMAND_DOMAIN = "ai-test-lab:atl-a.27:execution-command:v1"
_MANIFEST_DOMAIN = "ai-test-lab:atl-a.27:operation-manifest:v1"
_ATTESTATION_DOMAIN = "ai-test-lab:atl-a.27:execution-attestation:v1"
_MAX_DOCUMENT_BYTES = 64 * 1024


class ExecutionStatePersistenceError(RuntimeError):
    """Execution state could not be durably persisted."""


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError):
        raise ContinuedOperationExecutionError("execution canonical payload is invalid.") from None


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


def execution_request_document(value: ContinuedOperationExecutionRequest) -> dict[str, Any]:
    if type(value) is not ContinuedOperationExecutionRequest:
        raise ContinuedOperationExecutionError("an exact execution request is required.")
    document = asdict(value)
    document["requested_at"] = _timestamp(value.requested_at)
    return document


def translate_untrusted_execution_request(
    value: bytes | str | Mapping[str, Any],
) -> ContinuedOperationExecutionRequest:
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
        required = set(ContinuedOperationExecutionRequest.__dataclass_fields__)
        forbidden = {
            "command", "raw_command", "parameters", "arguments", "credentials", "token",
            "trusted", "permitted", "force_execute", "provider_response", "skip_verification",
        }
        if type(document) is not dict or set(document) != required or set(document) & forbidden:
            raise ValueError
        request = ContinuedOperationExecutionRequest(
            **{**document, "requested_at": _parse_time(document["requested_at"])}
        )
        if raw is not None and raw != _canonical(execution_request_document(request)):
            raise ValueError
        return request
    except Exception as error:
        raise ContinuedOperationExecutionError("execution request is invalid.") from error


def operation_manifest_document(value: ProtectedOperationManifest) -> dict[str, Any]:
    if type(value) is not ProtectedOperationManifest:
        raise ContinuedOperationExecutionError("an exact operation manifest is required.")
    return {
        "canonical_operation_input_digest": value.canonical_operation_input_digest,
        "environment_restrictions": list(value.environment_restrictions),
        "operation_reference": value.operation_reference,
        "permitted_adapter_contract_versions": list(value.permitted_adapter_contract_versions),
        "permitted_adapters": list(value.permitted_adapters),
        "permitted_deployments": list(value.permitted_deployments),
        "reference": value.reference,
        "required_capabilities": list(value.required_capabilities),
        "result_retention_classification": value.result_retention_classification,
        "safe_retry_classification": value.safe_retry_classification,
        "timeout_seconds": value.timeout_seconds,
        "version": value.version,
    }


def operation_manifest_digest(value: ProtectedOperationManifest) -> str:
    return sha256(_canonical({"domain": _MANIFEST_DOMAIN, **operation_manifest_document(value)})).hexdigest()


def _command_document(
    request: ContinuedOperationExecutionRequest,
    permit: TrustedContinuedOperationPermit,
    manifest: ProtectedOperationManifest,
) -> dict[str, Any]:
    return {
        "adapter_contract_version": request.adapter_contract_version,
        "authorization_digest": permit.authorization_digest,
        "authorization_id": permit.authorization_id,
        "canonical_operation_input_digest": manifest.canonical_operation_input_digest,
        "consumer_id": permit.consumer_id,
        "correlation_id": permit.correlation_id,
        "deployment_id": permit.deployment_id,
        "enforcement_evidence_digest": permit.enforcement_evidence_digest,
        "enforcement_point_id": permit.enforcement_point_id,
        "enforcement_request_id": permit.enforcement_request_id,
        "execution_attempt_id": request.execution_attempt_id,
        "execution_policy_reference": request.execution_policy_reference,
        "idempotency_key": request.idempotency_key,
        "operation_manifest_digest": request.operation_manifest_digest,
        "operation_reference": permit.operation_reference,
        "purpose": permit.purpose,
        "request_binding_digest": permit.request_binding_digest,
        "requested_adapter": request.requested_adapter,
        "schema_version": request.schema_version,
    }


def canonicalize_execution_command(
    request: ContinuedOperationExecutionRequest,
    permit: TrustedContinuedOperationPermit,
    manifest: ProtectedOperationManifest,
) -> ContinuedOperationExecutionCommand:
    digest_value = sha256(_canonical({
        "domain": _COMMAND_DOMAIN, **_command_document(request, permit, manifest),
    })).hexdigest()
    return ContinuedOperationExecutionCommand(request, permit, manifest, digest_value)


class InMemoryContinuedOperationConsumptionRecordRepository:
    """Authoritative reference repository keyed by ATL-A.26 evidence digest."""

    def __init__(self, values: tuple[ContinuedOperationConsumptionRecord, ...] = ()) -> None:
        self._lock = Lock()
        self._values = {item.evidence_digest: item for item in values}

    def get_by_evidence_reference(
        self, reference: str,
    ) -> ContinuedOperationConsumptionRecord | None:
        with self._lock:
            return self._values.get(reference)

    def put(self, value: ContinuedOperationConsumptionRecord) -> None:
        if type(value) is not ContinuedOperationConsumptionRecord:
            raise ContinuedOperationExecutionError("consumption record is invalid.")
        with self._lock:
            prior = self._values.get(value.evidence_digest)
            if prior is not None and prior != value:
                raise ContinuedOperationExecutionError("consumption evidence is immutable.")
            self._values[value.evidence_digest] = value


class InMemoryProtectedOperationManifestRepository:
    def __init__(self, values: tuple[ProtectedOperationManifest, ...] = ()) -> None:
        self._values = {item.reference: item for item in values}

    def get(self, reference: str) -> ProtectedOperationManifest | None:
        return self._values.get(reference)


def _same_claim(
    claim: ContinuedOperationExecutionClaim,
    request: ContinuedOperationExecutionRequest,
    command_digest: str,
) -> bool:
    return (
        claim.authorization_id == request.authorization_id and
        claim.enforcement_request_id == request.enforcement_request_id and
        claim.execution_attempt_id == request.execution_attempt_id and
        claim.idempotency_key == request.idempotency_key and
        claim.command_digest == command_digest and
        claim.operation_manifest_digest == request.operation_manifest_digest
    )


class InMemoryContinuedOperationExecutionStateStore:
    """Thread-safe single-winner reference store with all four uniqueness keys."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._claims: dict[str, ContinuedOperationExecutionClaim] = {}
        self._results: dict[str, ContinuedOperationExecutionResult] = {}
        self._indexes: dict[str, dict[str, str]] = {
            "authorization": {}, "enforcement": {}, "attempt": {}, "idempotency": {},
        }

    def claim(self, *, request: ContinuedOperationExecutionRequest,
              command_digest: str, claimed_at: datetime) -> AtomicExecutionClaimResult:
        with self._lock:
            matches = {
                self._indexes["authorization"].get(request.authorization_id),
                self._indexes["enforcement"].get(request.enforcement_request_id),
                self._indexes["attempt"].get(request.execution_attempt_id),
                self._indexes["idempotency"].get(request.idempotency_key),
            } - {None}
            if matches:
                if len(matches) == 1:
                    prior_digest = next(iter(matches))
                    prior = self._claims[prior_digest]
                    if _same_claim(prior, request, command_digest):
                        return AtomicExecutionClaimResult(
                            AtomicExecutionClaimState.EXACT_RETRY, prior,
                            self._results.get(prior_digest),
                        )
                    if (prior.authorization_id == request.authorization_id or
                            prior.enforcement_request_id == request.enforcement_request_id):
                        return AtomicExecutionClaimResult(
                            AtomicExecutionClaimState.ALREADY_CLAIMED, prior,
                            self._results.get(prior_digest),
                        )
                prior = self._claims[next(iter(matches))]
                return AtomicExecutionClaimResult(
                    AtomicExecutionClaimState.REQUEST_CONFLICT, prior,
                    self._results.get(prior.command_digest),
                )
            claim = ContinuedOperationExecutionClaim(
                request.authorization_id, request.enforcement_request_id,
                request.execution_attempt_id, request.idempotency_key, command_digest,
                request.operation_manifest_digest, claimed_at,
                ContinuedOperationExecutionClaimState.CLAIMED,
            )
            self._claims[command_digest] = claim
            self._indexes["authorization"][request.authorization_id] = command_digest
            self._indexes["enforcement"][request.enforcement_request_id] = command_digest
            self._indexes["attempt"][request.execution_attempt_id] = command_digest
            self._indexes["idempotency"][request.idempotency_key] = command_digest
            return AtomicExecutionClaimResult(AtomicExecutionClaimState.CLAIMED, claim)

    def mark_invocation_started(self, *, command_digest: str) -> str:
        with self._lock:
            claim = self._claims.get(command_digest)
            if claim is None or claim.claim_state is not ContinuedOperationExecutionClaimState.CLAIMED:
                raise ExecutionStatePersistenceError("execution claim is unavailable")
            reference = sha256(_canonical({
                "command_digest": command_digest, "state": "invocation_started",
            })).hexdigest()
            self._claims[command_digest] = replace(
                claim, claim_state=ContinuedOperationExecutionClaimState.INVOCATION_STARTED,
            )
            return reference

    def finalize(self, *, command_digest: str, result: ContinuedOperationExecutionResult) -> None:
        with self._lock:
            claim = self._claims.get(command_digest)
            if claim is None or claim.claim_state not in {
                ContinuedOperationExecutionClaimState.INVOCATION_STARTED,
                ContinuedOperationExecutionClaimState.OUTCOME_UNKNOWN,
            }:
                raise ExecutionStatePersistenceError("execution claim is unavailable")
            state = (ContinuedOperationExecutionClaimState.OUTCOME_UNKNOWN
                     if result.outcome is Outcome.OUTCOME_UNKNOWN else
                     ContinuedOperationExecutionClaimState.COMPLETED)
            reference = (result.attestation.attestation_digest if result.attestation else
                         sha256(_canonical({
                             "command_digest": command_digest, "outcome": result.outcome.value,
                         })).hexdigest())
            self._claims[command_digest] = replace(
                claim, claim_state=state, final_result_reference=reference,
            )
            self._results[command_digest] = result

    def get(self, command_digest: str) -> ContinuedOperationExecutionResult | None:
        with self._lock:
            return self._results.get(command_digest)


def _attestation_document(value: ContinuedOperationExecutionAttestation) -> dict[str, Any]:
    document = asdict(value)
    document.pop("attestation_id")
    document.pop("attestation_digest")
    document["outcome"] = value.outcome.value
    document["reason_code"] = value.reason_code.value
    document["started_at"] = _timestamp(value.started_at)
    document["completed_at"] = _timestamp(value.completed_at) if value.completed_at else None
    return document


def _result_document(value: ContinuedOperationExecutionResult) -> dict[str, Any]:
    return {
        "attestation": None if value.attestation is None else {
            **_attestation_document(value.attestation),
            "attestation_digest": value.attestation.attestation_digest,
            "attestation_id": value.attestation.attestation_id,
        },
        "authorization_id": value.authorization_id,
        "correlation_id": value.correlation_id,
        "deployment_id": value.deployment_id,
        "enforcement_request_id": value.enforcement_request_id,
        "evaluated_at": _timestamp(value.evaluated_at),
        "execution_attempt_id": value.execution_attempt_id,
        "idempotent": value.idempotent,
        "operation_reference": value.operation_reference,
        "outcome": value.outcome.value,
        "purpose": value.purpose,
        "reason_codes": [reason.value for reason in value.reason_codes],
    }


def _restore_attestation(document: dict[str, Any]) -> ContinuedOperationExecutionAttestation:
    return ContinuedOperationExecutionAttestation(**{
        **document,
        "outcome": Outcome(document["outcome"]),
        "reason_code": Reason(document["reason_code"]),
        "started_at": _parse_time(document["started_at"]),
        "completed_at": (_parse_time(document["completed_at"])
                         if document["completed_at"] else None),
    })


def _restore_result(document: dict[str, Any]) -> ContinuedOperationExecutionResult:
    return ContinuedOperationExecutionResult(
        execution_attempt_id=document["execution_attempt_id"],
        enforcement_request_id=document["enforcement_request_id"],
        authorization_id=document["authorization_id"], deployment_id=document["deployment_id"],
        purpose=document["purpose"], operation_reference=document["operation_reference"],
        outcome=Outcome(document["outcome"]),
        reason_codes=tuple(Reason(value) for value in document["reason_codes"]),
        evaluated_at=_parse_time(document["evaluated_at"]),
        correlation_id=document["correlation_id"],
        attestation=(_restore_attestation(document["attestation"])
                     if document["attestation"] else None),
        idempotent=document["idempotent"],
    )


class SqliteContinuedOperationExecutionStateStore:
    """Durable claim/result store with storage-level at-most-once constraints."""

    def __init__(self, path: str | Path) -> None:
        self._path = str(path)
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute(
                """CREATE TABLE IF NOT EXISTS continued_operation_execution (
                authorization_id TEXT NOT NULL UNIQUE,
                enforcement_request_id TEXT NOT NULL UNIQUE,
                execution_attempt_id TEXT NOT NULL UNIQUE,
                idempotency_key TEXT NOT NULL UNIQUE,
                command_digest TEXT PRIMARY KEY,
                manifest_digest TEXT NOT NULL,
                claimed_at TEXT NOT NULL,
                claim_state TEXT NOT NULL,
                result_json TEXT
                )"""
            )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._path, timeout=30, isolation_level=None)

    @staticmethod
    def _claim(row: tuple[Any, ...]) -> ContinuedOperationExecutionClaim:
        return ContinuedOperationExecutionClaim(
            row[0], row[1], row[2], row[3], row[4], row[5], _parse_time(row[6]),
            ContinuedOperationExecutionClaimState(row[7]),
            (json.loads(row[8])["attestation"]["attestation_digest"]
             if row[8] and json.loads(row[8])["attestation"] else None),
        )

    @staticmethod
    def _atomic(row: tuple[Any, ...], request: ContinuedOperationExecutionRequest,
                command_digest: str) -> AtomicExecutionClaimResult:
        claim = SqliteContinuedOperationExecutionStateStore._claim(row)
        result = _restore_result(json.loads(row[8])) if row[8] else None
        if _same_claim(claim, request, command_digest):
            state = AtomicExecutionClaimState.EXACT_RETRY
        elif (claim.authorization_id == request.authorization_id or
              claim.enforcement_request_id == request.enforcement_request_id):
            state = AtomicExecutionClaimState.ALREADY_CLAIMED
        else:
            state = AtomicExecutionClaimState.REQUEST_CONFLICT
        return AtomicExecutionClaimResult(state, claim, result)

    def claim(self, *, request: ContinuedOperationExecutionRequest,
              command_digest: str, claimed_at: datetime) -> AtomicExecutionClaimResult:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """SELECT * FROM continued_operation_execution WHERE
                authorization_id = ? OR enforcement_request_id = ? OR
                execution_attempt_id = ? OR idempotency_key = ? LIMIT 1""",
                (request.authorization_id, request.enforcement_request_id,
                 request.execution_attempt_id, request.idempotency_key),
            ).fetchone()
            if row:
                connection.rollback()
                return self._atomic(row, request, command_digest)
            connection.execute(
                "INSERT INTO continued_operation_execution VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL)",
                (request.authorization_id, request.enforcement_request_id,
                 request.execution_attempt_id, request.idempotency_key, command_digest,
                 request.operation_manifest_digest, _timestamp(claimed_at),
                 ContinuedOperationExecutionClaimState.CLAIMED.value),
            )
            connection.commit()
            claim = ContinuedOperationExecutionClaim(
                request.authorization_id, request.enforcement_request_id,
                request.execution_attempt_id, request.idempotency_key, command_digest,
                request.operation_manifest_digest, claimed_at,
                ContinuedOperationExecutionClaimState.CLAIMED,
            )
            return AtomicExecutionClaimResult(AtomicExecutionClaimState.CLAIMED, claim)
        except sqlite3.IntegrityError:
            connection.rollback()
            return self.claim(request=request, command_digest=command_digest, claimed_at=claimed_at)
        except sqlite3.Error as error:
            try:
                connection.rollback()
            except sqlite3.Error:
                pass
            raise ExecutionStatePersistenceError("execution claim failed") from error
        finally:
            connection.close()

    def mark_invocation_started(self, *, command_digest: str) -> str:
        reference = sha256(_canonical({
            "command_digest": command_digest, "state": "invocation_started",
        })).hexdigest()
        try:
            with self._connect() as connection:
                cursor = connection.execute(
                    """UPDATE continued_operation_execution SET claim_state = ?
                    WHERE command_digest = ? AND claim_state = ?""",
                    (ContinuedOperationExecutionClaimState.INVOCATION_STARTED.value,
                     command_digest, ContinuedOperationExecutionClaimState.CLAIMED.value),
                )
                if cursor.rowcount != 1:
                    raise ExecutionStatePersistenceError("execution claim is unavailable")
            return reference
        except sqlite3.Error as error:
            raise ExecutionStatePersistenceError("execution state update failed") from error

    def finalize(self, *, command_digest: str, result: ContinuedOperationExecutionResult) -> None:
        state = (ContinuedOperationExecutionClaimState.OUTCOME_UNKNOWN
                 if result.outcome is Outcome.OUTCOME_UNKNOWN else
                 ContinuedOperationExecutionClaimState.COMPLETED)
        try:
            with self._connect() as connection:
                cursor = connection.execute(
                    """UPDATE continued_operation_execution SET claim_state = ?, result_json = ?
                    WHERE command_digest = ? AND claim_state IN (?, ?)""",
                    (state.value, _canonical(_result_document(result)).decode("utf-8"),
                     command_digest,
                     ContinuedOperationExecutionClaimState.INVOCATION_STARTED.value,
                     ContinuedOperationExecutionClaimState.OUTCOME_UNKNOWN.value),
                )
                if cursor.rowcount != 1:
                    raise ExecutionStatePersistenceError("execution claim is unavailable")
        except sqlite3.Error as error:
            raise ExecutionStatePersistenceError("execution result persistence failed") from error

    def get(self, command_digest: str) -> ContinuedOperationExecutionResult | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT result_json FROM continued_operation_execution WHERE command_digest = ?",
                (command_digest,),
            ).fetchone()
        return None if row is None or row[0] is None else _restore_result(json.loads(row[0]))


def _binding_reason(
    request: ContinuedOperationExecutionRequest,
    record: ContinuedOperationConsumptionRecord,
) -> Reason | None:
    checks = (
        (record.authorization_id == request.authorization_id, Reason.AUTHORIZATION_MISMATCH),
        (record.authorization_digest == request.authorization_digest, Reason.AUTHORIZATION_MISMATCH),
        (record.enforcement_request_id == request.enforcement_request_id,
         Reason.ENFORCEMENT_REQUEST_MISMATCH),
        (record.request_binding_digest == request.request_binding_digest,
         Reason.REQUEST_BINDING_MISMATCH),
        (record.deployment_id == request.deployment_id, Reason.DEPLOYMENT_MISMATCH),
        (record.consumer_id == request.consumer_id, Reason.CONSUMER_MISMATCH),
        (record.enforcement_point_id == request.enforcement_point_id,
         Reason.ENFORCEMENT_POINT_MISMATCH),
        (record.purpose == request.purpose, Reason.PURPOSE_MISMATCH),
        (record.operation_reference == request.operation_reference, Reason.OPERATION_MISMATCH),
        (record.correlation_id == request.correlation_id, Reason.CORRELATION_MISMATCH),
    )
    return next((reason for valid, reason in checks if not valid), None)


def _permit(record: ContinuedOperationConsumptionRecord) -> TrustedContinuedOperationPermit:
    return TrustedContinuedOperationPermit(
        record.authorization_id, record.authorization_digest, record.enforcement_request_id,
        record.evidence_digest, record.request_binding_digest, record.deployment_id,
        record.consumer_id, record.enforcement_point_id, record.purpose,
        record.operation_reference, record.consumed_at, record.policy_reference,
        record.correlation_id,
    )


def _attestation(
    command: ContinuedOperationExecutionCommand,
    adapter_result: ContinuedOperationAdapterResult,
    previous_state_reference: str,
) -> ContinuedOperationExecutionAttestation:
    request, permit = command.request, command.permit
    values = {
        "adapter_contract_version": request.adapter_contract_version,
        "adapter_identity": request.requested_adapter,
        "authorization_digest": permit.authorization_digest,
        "authorization_id": permit.authorization_id,
        "completed_at": (_timestamp(adapter_result.completed_at)
                         if adapter_result.completed_at else None),
        "consumer_id": permit.consumer_id,
        "contract_version": CONTINUED_OPERATION_EXECUTION_ATTESTATION_VERSION,
        "correlation_id": permit.correlation_id,
        "deployment_id": permit.deployment_id,
        "domain": _ATTESTATION_DOMAIN,
        "enforcement_evidence_digest": permit.enforcement_evidence_digest,
        "enforcement_point_id": permit.enforcement_point_id,
        "enforcement_request_id": permit.enforcement_request_id,
        "execution_attempt_id": request.execution_attempt_id,
        "execution_command_digest": command.command_digest,
        "execution_policy_reference": request.execution_policy_reference,
        "operation_manifest_digest": request.operation_manifest_digest,
        "operation_reference": permit.operation_reference,
        "outcome": adapter_result.outcome.value,
        "previous_execution_state_reference": previous_state_reference,
        "provider_operation_reference": adapter_result.provider_operation_reference,
        "purpose": permit.purpose,
        "reason_code": adapter_result.reason_code.value,
        "request_binding_digest": permit.request_binding_digest,
        "sanitized_provider_response_digest": adapter_result.sanitized_provider_response_digest,
        "started_at": _timestamp(adapter_result.started_at),
    }
    digest_value = sha256(_canonical(values)).hexdigest()
    attestation_id = sha256(_canonical({
        **values, "attestation_digest": digest_value,
    })).hexdigest()
    public_values = {key: value for key, value in values.items() if key != "domain"}
    public_values["outcome"] = adapter_result.outcome
    public_values["reason_code"] = adapter_result.reason_code
    public_values["started_at"] = adapter_result.started_at
    public_values["completed_at"] = adapter_result.completed_at
    return ContinuedOperationExecutionAttestation(
        attestation_id=attestation_id, attestation_digest=digest_value, **public_values,
    )


def verify_continued_operation_execution_attestation(
    value: ContinuedOperationExecutionAttestation,
) -> bool:
    if type(value) is not ContinuedOperationExecutionAttestation:
        return False
    document = _attestation_document(value)
    values = {"domain": _ATTESTATION_DOMAIN, **document}
    digest_value = sha256(_canonical(values)).hexdigest()
    attestation_id = sha256(_canonical({
        **values, "attestation_digest": digest_value,
    })).hexdigest()
    return value.attestation_digest == digest_value and value.attestation_id == attestation_id


def _result(
    request: ContinuedOperationExecutionRequest, outcome: Outcome, reason: Reason,
    evaluated_at: datetime, *, attestation: ContinuedOperationExecutionAttestation | None = None,
    idempotent: bool = False,
) -> ContinuedOperationExecutionResult:
    return ContinuedOperationExecutionResult(
        request.execution_attempt_id, request.enforcement_request_id,
        request.authorization_id, request.deployment_id, request.purpose,
        request.operation_reference, outcome, (reason,), evaluated_at,
        request.correlation_id, attestation, idempotent,
    )


def _trusted_now(trusted_clock: Callable[[], datetime]) -> datetime | None:
    try:
        value = trusted_clock()
        if (not isinstance(value, datetime) or value.tzinfo is None or
                value.utcoffset() is None or value.microsecond):
            return None
        return value.astimezone(timezone.utc)
    except Exception:
        return None


def execute_continued_operation(
    request: ContinuedOperationExecutionRequest, *,
    consumption_repository: ContinuedOperationConsumptionRecordRepository,
    manifest_repository: ProtectedOperationManifestRepository,
    policy: ContinuedOperationExecutionPolicy,
    adapters: Mapping[str, ContinuedOperationExecutionAdapter],
    state_store: ContinuedOperationExecutionStateStore,
    trusted_clock: Callable[[], datetime],
) -> ContinuedOperationExecutionResult:
    if type(request) is not ContinuedOperationExecutionRequest:
        raise ContinuedOperationExecutionError("an exact execution request is required.")
    now = _trusted_now(trusted_clock)
    if now is None:
        return _result(
            request, Outcome.INDETERMINATE, Reason.UNTRUSTED_TIME_SOURCE,
            request.requested_at,
        )
    if request.requested_at > now:
        return _result(request, Outcome.INVALID, Reason.INVALID_EXECUTION_REQUEST, now)
    try:
        record = consumption_repository.get_by_evidence_reference(
            request.enforcement_evidence_reference,
        )
    except Exception:
        return _result(request, Outcome.INDETERMINATE, Reason.ENFORCEMENT_STATE_UNAVAILABLE, now)
    if record is None:
        return _result(request, Outcome.BLOCKED, Reason.ENFORCEMENT_RECORD_NOT_FOUND, now)
    if type(record) is not ContinuedOperationConsumptionRecord:
        return _result(request, Outcome.INDETERMINATE, Reason.ENFORCEMENT_STATE_UNAVAILABLE, now)
    if (request.enforcement_evidence_reference != record.evidence_digest or
            request.enforcement_evidence_digest != record.evidence_digest):
        return _result(request, Outcome.BLOCKED, Reason.ENFORCEMENT_EVIDENCE_MISMATCH, now)
    mismatch = _binding_reason(request, record)
    if mismatch is not None:
        return _result(request, Outcome.BLOCKED, mismatch, now)
    permit = _permit(record)
    try:
        manifest = manifest_repository.get(request.operation_manifest_reference)
    except Exception:
        return _result(request, Outcome.INDETERMINATE, Reason.MANIFEST_NOT_FOUND, now)
    if manifest is None:
        return _result(request, Outcome.INVALID, Reason.MANIFEST_NOT_FOUND, now)
    if type(manifest) is not ProtectedOperationManifest:
        return _result(request, Outcome.INDETERMINATE, Reason.MANIFEST_NOT_FOUND, now)
    if operation_manifest_digest(manifest) != request.operation_manifest_digest:
        return _result(request, Outcome.BLOCKED, Reason.MANIFEST_DIGEST_MISMATCH, now)
    if manifest.operation_reference != permit.operation_reference:
        return _result(request, Outcome.BLOCKED, Reason.OPERATION_MISMATCH, now)
    if request.deployment_id not in manifest.permitted_deployments:
        return _result(request, Outcome.BLOCKED, Reason.DEPLOYMENT_NOT_PERMITTED, now)
    if (manifest.environment_restrictions and
            request.deployment_id not in manifest.environment_restrictions):
        return _result(request, Outcome.BLOCKED, Reason.DEPLOYMENT_NOT_PERMITTED, now)
    if request.execution_policy_reference != policy.reference:
        return _result(request, Outcome.BLOCKED, Reason.EXECUTION_POLICY_MISMATCH, now)
    if (request.requested_at < permit.consumed_at or now - permit.consumed_at > timedelta(
            seconds=policy.maximum_permit_to_execution_delay_seconds)):
        return _result(request, Outcome.BLOCKED, Reason.EXECUTION_WINDOW_EXPIRED, now)
    if (request.requested_adapter not in manifest.permitted_adapters or
            request.requested_adapter not in policy.permitted_adapters):
        return _result(request, Outcome.BLOCKED, Reason.ADAPTER_NOT_PERMITTED, now)
    if (request.adapter_contract_version not in manifest.permitted_adapter_contract_versions or
            request.adapter_contract_version not in policy.permitted_adapter_contract_versions):
        return _result(request, Outcome.BLOCKED, Reason.ADAPTER_VERSION_UNSUPPORTED, now)
    adapter = adapters.get(request.requested_adapter)
    if adapter is None or getattr(adapter, "identity", None) != request.requested_adapter:
        return _result(request, Outcome.BLOCKED, Reason.ADAPTER_NOT_FOUND, now)
    if getattr(adapter, "contract_version", None) != request.adapter_contract_version:
        return _result(request, Outcome.BLOCKED, Reason.ADAPTER_VERSION_UNSUPPORTED, now)
    capabilities = getattr(adapter, "capabilities", None)
    if (not isinstance(capabilities, frozenset) or
            not frozenset(manifest.required_capabilities).issubset(capabilities)):
        return _result(request, Outcome.BLOCKED, Reason.ADAPTER_CAPABILITY_MISMATCH, now)
    command = canonicalize_execution_command(request, permit, manifest)
    try:
        claimed = state_store.claim(
            request=request, command_digest=command.command_digest, claimed_at=now,
        )
    except Exception:
        return _result(request, Outcome.INDETERMINATE, Reason.EXECUTION_STATE_UNAVAILABLE, now)
    if claimed.state is AtomicExecutionClaimState.EXACT_RETRY:
        if claimed.result is not None:
            return replace(
                claimed.result, reason_codes=(Reason.IDEMPOTENT_RESULT_RETURNED,), idempotent=True,
            )
        outcome = (Outcome.OUTCOME_UNKNOWN if claimed.claim and claimed.claim.claim_state in {
            ContinuedOperationExecutionClaimState.INVOCATION_STARTED,
            ContinuedOperationExecutionClaimState.OUTCOME_UNKNOWN,
        } else Outcome.INDETERMINATE)
        reason = (Reason.PROVIDER_OUTCOME_UNKNOWN if outcome is Outcome.OUTCOME_UNKNOWN else
                  Reason.EXECUTION_IN_PROGRESS)
        return _result(request, outcome, reason, now, idempotent=True)
    if claimed.state is AtomicExecutionClaimState.ALREADY_CLAIMED:
        return _result(request, Outcome.BLOCKED, Reason.EXECUTION_ALREADY_CLAIMED, now)
    if claimed.state is AtomicExecutionClaimState.REQUEST_CONFLICT:
        return _result(request, Outcome.BLOCKED, Reason.EXECUTION_REQUEST_CONFLICT, now)
    if claimed.state is not AtomicExecutionClaimState.CLAIMED:
        return _result(request, Outcome.INDETERMINATE, Reason.EXECUTION_STATE_UNAVAILABLE, now)
    try:
        previous_state = state_store.mark_invocation_started(command_digest=command.command_digest)
    except Exception:
        return _result(request, Outcome.INDETERMINATE, Reason.EXECUTION_STATE_UNAVAILABLE, now)
    try:
        adapter_result = adapter.execute(command)
        if type(adapter_result) is not ContinuedOperationAdapterResult:
            raise TypeError
    except Exception:
        adapter_result = ContinuedOperationAdapterResult(
            request.execution_attempt_id, Outcome.OUTCOME_UNKNOWN,
            Reason.PROVIDER_OUTCOME_UNKNOWN, now, None, None,
            sha256(b"provider-outcome-unavailable").hexdigest(),
        )
    attestation = _attestation(command, adapter_result, previous_state)
    result = _result(
        request, adapter_result.outcome, adapter_result.reason_code,
        adapter_result.completed_at or adapter_result.started_at, attestation=attestation,
    )
    try:
        state_store.finalize(command_digest=command.command_digest, result=result)
    except Exception:
        uncertain = ContinuedOperationAdapterResult(
            request.execution_attempt_id, Outcome.OUTCOME_UNKNOWN,
            Reason.EXECUTION_STATE_UNAVAILABLE, adapter_result.started_at, None,
            adapter_result.provider_operation_reference,
            adapter_result.sanitized_provider_response_digest,
        )
        return _result(
            request, Outcome.OUTCOME_UNKNOWN, Reason.EXECUTION_STATE_UNAVAILABLE, now,
            attestation=_attestation(command, uncertain, previous_state),
        )
    return result


def public_continued_operation_execution(
    result: ContinuedOperationExecutionResult,
) -> PublicContinuedOperationExecutionV1:
    if type(result) is not ContinuedOperationExecutionResult:
        raise ContinuedOperationExecutionError("an exact execution result is required.")
    attestation = result.attestation
    return PublicContinuedOperationExecutionV1(
        execution_attempt_id=result.execution_attempt_id,
        enforcement_request_id=result.enforcement_request_id,
        authorization_id=result.authorization_id,
        deployment_id=result.deployment_id,
        purpose=result.purpose,
        operation_reference=result.operation_reference,
        outcome=result.outcome,
        reason_codes=result.reason_codes,
        started_at=attestation.started_at if attestation else None,
        completed_at=attestation.completed_at if attestation else None,
        attestation_reference=attestation.attestation_digest if attestation else None,
        correlation_id=result.correlation_id,
        idempotent=result.idempotent,
    )


__all__ = [
    "ExecutionStatePersistenceError",
    "InMemoryContinuedOperationConsumptionRecordRepository",
    "InMemoryContinuedOperationExecutionStateStore",
    "InMemoryProtectedOperationManifestRepository",
    "SqliteContinuedOperationExecutionStateStore",
    "canonicalize_execution_command", "execute_continued_operation",
    "execution_request_document", "operation_manifest_digest",
    "operation_manifest_document", "public_continued_operation_execution",
    "translate_untrusted_execution_request",
    "verify_continued_operation_execution_attestation",
]
