"""ATL-A.29 authoritative protected-operation lifecycle settlement."""
from __future__ import annotations

import hmac
import json
import sqlite3
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path
from threading import Lock
from typing import Any, Callable, Mapping

from src.reference_architecture_continued_operation_execution import (
    operation_manifest_digest,
    verify_continued_operation_execution_attestation,
)
from src.reference_architecture_continued_operation_reconciliation import (
    verify_reconciliation_attestation,
)
from src.reference_architecture_continued_operation_reconciliation_contract import (
    ReconciliationOutcome,
)
from src.reference_architecture_continued_operation_settlement_contract import (
    CONTINUED_OPERATION_SETTLEMENT_EVIDENCE_VERSION,
    AtomicSettlementClaim,
    AuthoritativeVerificationEvidence,
    ContinuedOperationSettlementError,
    ProtectedOperationSettlementEvidence,
    ProtectedOperationSettlementPolicy,
    ProtectedOperationSettlementRequest,
    ProtectedOperationSettlementResult,
    ProtectedOperationSettlementStatus as Status,
    PublicProtectedOperationSettlementV1,
    SettlementClaimState,
    SettlementEvidenceRepository,
    SettlementPolicyRepository,
    SettlementReasonCode as Reason,
    SettlementSigner,
    VerificationEvidenceRepository,
)


_REQUEST_DOMAIN = "ai-test-lab:atl-a.29:settlement-request:v1"
_LIFECYCLE_DOMAIN = "ai-test-lab:atl-a.29:settlement-lifecycle:v1"
_EVIDENCE_DOMAIN = "ai-test-lab:atl-a.29:settlement-evidence:v1"
_MAX_DOCUMENT_BYTES = 64 * 1024


class SettlementPersistenceError(RuntimeError):
    """The settlement repository could not safely complete an operation."""


class SettlementCommitStatusUnknown(SettlementPersistenceError):
    """The repository cannot establish whether settlement committed."""


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError):
        raise ContinuedOperationSettlementError(
            "settlement canonical payload is invalid."
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


def settlement_request_document(value: ProtectedOperationSettlementRequest) -> dict[str, Any]:
    if type(value) is not ProtectedOperationSettlementRequest:
        raise ContinuedOperationSettlementError("an exact settlement request is required.")
    document = asdict(value)
    document["requested_at"] = _timestamp(value.requested_at)
    return document


def settlement_request_digest(value: ProtectedOperationSettlementRequest) -> str:
    return sha256(_canonical({
        "domain": _REQUEST_DOMAIN, **settlement_request_document(value),
    })).hexdigest()


def settlement_lifecycle_key(value: ProtectedOperationSettlementRequest) -> str:
    if type(value) is not ProtectedOperationSettlementRequest:
        raise ContinuedOperationSettlementError("an exact settlement request is required.")
    return sha256(_canonical({
        "domain": _LIFECYCLE_DOMAIN,
        "deployment_id": value.deployment_id,
        "operation_id": value.operation_id,
        "execution_id": value.execution_id,
        "verification_id": value.verification_id,
    })).hexdigest()


def translate_untrusted_settlement_request(
    value: bytes | str | Mapping[str, Any],
) -> ProtectedOperationSettlementRequest:
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
            "verification_evidence", "execution_attestation", "authorization_artifact",
            "provider_response", "observation", "credentials", "token", "secret",
            "settlement_status", "trusted", "verified", "retry", "repair", "rollback",
        }
        if (type(document) is not dict or
                set(document) != set(ProtectedOperationSettlementRequest.__dataclass_fields__) or
                set(document) & forbidden):
            raise ValueError
        request = ProtectedOperationSettlementRequest(**{
            **document, "requested_at": _parse_time(document["requested_at"]),
        })
        if raw is not None and raw != _canonical(settlement_request_document(request)):
            raise ValueError
        return request
    except Exception as error:
        raise ContinuedOperationSettlementError("settlement request is invalid.") from error


class HmacSettlementSigner:
    """Reference signer; production deployments should inject a managed-key adapter."""

    def __init__(self, key: bytes) -> None:
        if type(key) is not bytes or len(key) < 32:
            raise ContinuedOperationSettlementError("settlement signing key is invalid.")
        self._key = key

    def sign(self, payload: bytes) -> str:
        if type(payload) is not bytes:
            raise ContinuedOperationSettlementError("settlement signing payload is invalid.")
        return hmac.new(self._key, payload, sha256).hexdigest()

    def verify(self, payload: bytes, signature: str) -> bool:
        try:
            return hmac.compare_digest(self.sign(payload), signature)
        except Exception:
            return False


class InMemoryVerificationEvidenceRepository:
    def __init__(self, values: tuple[AuthoritativeVerificationEvidence, ...] = ()) -> None:
        self._values = {value.attestation.reconciliation_id: value for value in values}

    def get_committed(self, verification_id: str) -> AuthoritativeVerificationEvidence | None:
        value = self._values.get(verification_id)
        return value if value is not None and value.committed else None


class InMemorySettlementPolicyRepository:
    def __init__(self, values: tuple[ProtectedOperationSettlementPolicy, ...] = ()) -> None:
        self._values = {(value.policy_id, value.version): value for value in values}

    def get(self, policy_id: str, version: str) -> ProtectedOperationSettlementPolicy | None:
        return self._values.get((policy_id, version))


class InMemorySettlementEvidenceRepository:
    """Thread-safe single-winner reference repository."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._records: dict[str, tuple[str, str, ProtectedOperationSettlementResult | None]] = {}
        self._requests: dict[str, tuple[str, str]] = {}

    def claim(
        self, *, lifecycle_key: str, settlement_request_id: str, request_digest: str,
    ) -> AtomicSettlementClaim:
        with self._lock:
            request_owner = self._requests.get(settlement_request_id)
            if request_owner is not None and request_owner != (lifecycle_key, request_digest):
                return AtomicSettlementClaim(SettlementClaimState.CONFLICT)
            current = self._records.get(lifecycle_key)
            if current is None:
                self._records[lifecycle_key] = (settlement_request_id, request_digest, None)
                self._requests[settlement_request_id] = (lifecycle_key, request_digest)
                return AtomicSettlementClaim(SettlementClaimState.NEW)
            existing_request, existing_digest, result = current
            if (existing_request, existing_digest) != (settlement_request_id, request_digest):
                return AtomicSettlementClaim(SettlementClaimState.CONFLICT)
            if result is None:
                return AtomicSettlementClaim(SettlementClaimState.IN_PROGRESS)
            return AtomicSettlementClaim(SettlementClaimState.REPLAY, result)

    def commit(
        self, *, lifecycle_key: str, settlement_request_id: str, request_digest: str,
        result: ProtectedOperationSettlementResult,
    ) -> None:
        with self._lock:
            current = self._records.get(lifecycle_key)
            if current is None or current[:2] != (settlement_request_id, request_digest):
                raise SettlementPersistenceError("settlement claim is unavailable")
            if current[2] is not None and current[2] != result:
                raise SettlementPersistenceError("settlement evidence is immutable")
            self._records[lifecycle_key] = (settlement_request_id, request_digest, result)

    def recover(self, lifecycle_key: str) -> AtomicSettlementClaim:
        with self._lock:
            current = self._records.get(lifecycle_key)
            if current is None:
                return AtomicSettlementClaim(SettlementClaimState.UNAVAILABLE)
            if current[2] is None:
                return AtomicSettlementClaim(SettlementClaimState.IN_PROGRESS)
            return AtomicSettlementClaim(SettlementClaimState.REPLAY, current[2])


def _evidence_document(value: ProtectedOperationSettlementEvidence) -> dict[str, Any]:
    document = asdict(value)
    document.pop("settlement_id")
    document.pop("evidence_digest")
    document.pop("signature")
    document["settlement_status"] = value.settlement_status.value
    document["reason_code"] = value.reason_code.value
    document["settled_at"] = _timestamp(value.settled_at)
    return document


def _result_document(value: ProtectedOperationSettlementResult) -> dict[str, Any]:
    evidence = None
    if value.evidence is not None:
        evidence = {
            **_evidence_document(value.evidence),
            "settlement_id": value.evidence.settlement_id,
            "evidence_digest": value.evidence.evidence_digest,
            "signature": value.evidence.signature,
        }
    return {
        "settlement_request_id": value.settlement_request_id,
        "status": value.status.value,
        "reason_code": value.reason_code.value,
        "evaluated_at": _timestamp(value.evaluated_at),
        "evidence": evidence,
        "committed": value.committed,
        "idempotent": value.idempotent,
    }


def _restore_result(document: dict[str, Any]) -> ProtectedOperationSettlementResult:
    raw = document["evidence"]
    evidence = None
    if raw is not None:
        evidence = ProtectedOperationSettlementEvidence(**{
            **raw,
            "settlement_status": Status(raw["settlement_status"]),
            "reason_code": Reason(raw["reason_code"]),
            "settled_at": _parse_time(raw["settled_at"]),
        })
    return ProtectedOperationSettlementResult(
        settlement_request_id=document["settlement_request_id"],
        status=Status(document["status"]), reason_code=Reason(document["reason_code"]),
        evaluated_at=_parse_time(document["evaluated_at"]), evidence=evidence,
        committed=document["committed"], idempotent=document["idempotent"],
    )


class SqliteSettlementEvidenceRepository:
    """Durable atomic ATL-A.29 repository using SQLite uniqueness and transactions."""

    def __init__(self, path: str | Path) -> None:
        self._path = str(path)
        with self._connect() as connection:
            connection.execute("""CREATE TABLE IF NOT EXISTS continued_operation_settlement (
                lifecycle_key TEXT PRIMARY KEY,
                settlement_request_id TEXT NOT NULL UNIQUE,
                request_digest TEXT NOT NULL,
                result_json TEXT
            )""")

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._path, timeout=30)
        connection.execute("PRAGMA journal_mode=WAL")
        return connection

    def claim(
        self, *, lifecycle_key: str, settlement_request_id: str, request_digest: str,
    ) -> AtomicSettlementClaim:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT settlement_request_id, request_digest, result_json "
                "FROM continued_operation_settlement WHERE lifecycle_key = ?",
                (lifecycle_key,),
            ).fetchone()
            by_request = connection.execute(
                "SELECT lifecycle_key, request_digest FROM continued_operation_settlement "
                "WHERE settlement_request_id = ?", (settlement_request_id,),
            ).fetchone()
            if by_request is not None and by_request != (lifecycle_key, request_digest):
                connection.rollback()
                return AtomicSettlementClaim(SettlementClaimState.CONFLICT)
            if row is None:
                connection.execute(
                    "INSERT INTO continued_operation_settlement VALUES (?, ?, ?, NULL)",
                    (lifecycle_key, settlement_request_id, request_digest),
                )
                connection.commit()
                return AtomicSettlementClaim(SettlementClaimState.NEW)
            connection.rollback()
            if row[:2] != (settlement_request_id, request_digest):
                return AtomicSettlementClaim(SettlementClaimState.CONFLICT)
            if row[2] is None:
                return AtomicSettlementClaim(SettlementClaimState.IN_PROGRESS)
            return AtomicSettlementClaim(
                SettlementClaimState.REPLAY, _restore_result(json.loads(row[2])),
            )
        except sqlite3.Error as error:
            try:
                connection.rollback()
            except sqlite3.Error:
                pass
            raise SettlementPersistenceError("settlement claim failed") from error
        finally:
            connection.close()

    def commit(
        self, *, lifecycle_key: str, settlement_request_id: str, request_digest: str,
        result: ProtectedOperationSettlementResult,
    ) -> None:
        payload = _canonical(_result_document(result)).decode("utf-8")
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT settlement_request_id, request_digest, result_json "
                "FROM continued_operation_settlement WHERE lifecycle_key = ?",
                (lifecycle_key,),
            ).fetchone()
            if row is None or row[:2] != (settlement_request_id, request_digest):
                connection.rollback()
                raise SettlementPersistenceError("settlement claim is unavailable")
            if row[2] is not None and row[2] != payload:
                connection.rollback()
                raise SettlementPersistenceError("settlement evidence is immutable")
            connection.execute(
                "UPDATE continued_operation_settlement SET result_json = ? "
                "WHERE lifecycle_key = ? AND settlement_request_id = ? "
                "AND request_digest = ? AND result_json IS NULL",
                (payload, lifecycle_key, settlement_request_id, request_digest),
            )
            connection.commit()
        except SettlementPersistenceError:
            raise
        except sqlite3.Error as error:
            try:
                connection.rollback()
            except sqlite3.Error:
                pass
            raise SettlementCommitStatusUnknown("settlement commit status is unknown") from error
        finally:
            connection.close()

    def recover(self, lifecycle_key: str) -> AtomicSettlementClaim:
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT result_json FROM continued_operation_settlement WHERE lifecycle_key = ?",
                (lifecycle_key,),
            ).fetchone()
            if row is None:
                return AtomicSettlementClaim(SettlementClaimState.UNAVAILABLE)
            if row[0] is None:
                return AtomicSettlementClaim(SettlementClaimState.IN_PROGRESS)
            return AtomicSettlementClaim(
                SettlementClaimState.REPLAY, _restore_result(json.loads(row[0])),
            )
        finally:
            connection.close()


def _trusted_now(clock: Callable[[], datetime]) -> datetime | None:
    try:
        value = clock()
        if (not isinstance(value, datetime) or value.tzinfo is None or
                value.utcoffset() is None or value.microsecond):
            return None
        return value.astimezone(timezone.utc)
    except Exception:
        return None


def _result(
    request: ProtectedOperationSettlementRequest, status: Status, reason: Reason,
    evaluated_at: datetime, evidence: ProtectedOperationSettlementEvidence | None = None,
) -> ProtectedOperationSettlementResult:
    return ProtectedOperationSettlementResult(
        request.settlement_request_id, status, reason, evaluated_at,
        evidence, evidence is not None, False,
    )


def _admit_lineage(
    request: ProtectedOperationSettlementRequest,
    evidence: AuthoritativeVerificationEvidence,
    policy: ProtectedOperationSettlementPolicy,
) -> Reason | None:
    attestation = evidence.attestation
    if not evidence.committed or not verify_reconciliation_attestation(attestation):
        return Reason.VERIFICATION_EVIDENCE_INVALID
    if request.verification_evidence_digest != attestation.reconciliation_digest:
        return Reason.VERIFICATION_EVIDENCE_INVALID
    if (
        request.verification_id != attestation.reconciliation_id
        or request.deployment_id != attestation.deployment_id
        or request.operation_id != attestation.operation_reference
        or request.execution_id != attestation.execution_attempt_id
        or request.correlation_id != attestation.correlation_id
    ):
        return Reason.LIFECYCLE_BINDING_MISMATCH
    if attestation.verification_policy_reference not in policy.allowed_verification_policy_ids:
        return Reason.SETTLEMENT_POLICY_NOT_ALLOWED
    execution = evidence.execution_evidence
    if execution is None:
        if policy.require_execution_attestation or policy.require_complete_evidence_chain:
            return Reason.UPSTREAM_EVIDENCE_MISSING
        return None
    if (
        not execution.committed
        or not verify_continued_operation_execution_attestation(execution.attestation)
        or execution.evidence_reference != execution.attestation.attestation_digest
        or operation_manifest_digest(execution.operation_manifest) !=
            execution.attestation.operation_manifest_digest
    ):
        return Reason.UPSTREAM_EVIDENCE_INVALID
    record = execution.consumption_record
    execution_request = execution.request
    execution_attestation = execution.attestation
    if (
        attestation.execution_attestation_reference != execution.evidence_reference
        or attestation.consumption_id != record.evidence_digest
        or request.deployment_id != record.deployment_id
        or request.deployment_id != execution_request.deployment_id
        or request.deployment_id != execution_attestation.deployment_id
        or request.operation_id != record.operation_reference
        or request.operation_id != execution_request.operation_reference
        or request.operation_id != execution.operation_manifest.operation_reference
        or request.operation_id != execution_attestation.operation_reference
        or request.execution_id != execution_request.execution_attempt_id
        or request.execution_id != execution_attestation.execution_attempt_id
        or request.correlation_id != record.correlation_id
        or request.correlation_id != execution_request.correlation_id
        or request.correlation_id != execution_attestation.correlation_id
        or record.evidence_digest != execution_attestation.enforcement_evidence_digest
    ):
        return Reason.LIFECYCLE_BINDING_MISMATCH
    return None


def _decision(
    outcome: ReconciliationOutcome, policy: ProtectedOperationSettlementPolicy,
) -> tuple[Status, Reason]:
    if outcome is ReconciliationOutcome.VERIFIED:
        return Status.SETTLED_SUCCESS, Reason.EXPECTED_POSTCONDITION_VERIFIED
    if outcome is ReconciliationOutcome.MISMATCH:
        if policy.mismatch_is_terminal:
            return Status.SETTLED_FAILURE, Reason.EXPECTED_POSTCONDITION_MISMATCH
        return Status.SUSPENDED, Reason.EXPECTED_POSTCONDITION_MISMATCH
    if outcome is ReconciliationOutcome.INDETERMINATE:
        return Status.SUSPENDED, Reason.VERIFICATION_INDETERMINATE
    return Status.REJECTED, Reason.VERIFICATION_EVIDENCE_INVALID


def _make_evidence(
    request: ProtectedOperationSettlementRequest,
    source: AuthoritativeVerificationEvidence,
    policy: ProtectedOperationSettlementPolicy,
    status: Status, reason: Reason, settled_at: datetime, signer: SettlementSigner,
) -> ProtectedOperationSettlementEvidence:
    execution = source.execution_evidence
    if execution is None:
        raise ContinuedOperationSettlementError("complete upstream evidence is required.")
    values = {
        "contract_version": CONTINUED_OPERATION_SETTLEMENT_EVIDENCE_VERSION,
        "deployment_id": request.deployment_id,
        "enforcement_evidence_digest": execution.consumption_record.evidence_digest,
        "execution_evidence_digest": execution.attestation.attestation_digest,
        "operation_id": request.operation_id,
        "execution_id": request.execution_id,
        "reason_code": reason.value,
        "settled_at": _timestamp(settled_at),
        "settlement_policy_id": policy.policy_id,
        "settlement_policy_version": policy.version,
        "settlement_status": status.value,
        "verification_evidence_digest": source.attestation.reconciliation_digest,
        "verification_id": source.attestation.reconciliation_id,
    }
    evidence_digest = sha256(_canonical({"domain": _EVIDENCE_DOMAIN, **values})).hexdigest()
    settlement_id = sha256(_canonical({
        "domain": _EVIDENCE_DOMAIN, **values, "evidence_digest": evidence_digest,
    })).hexdigest()
    signature = signer.sign(bytes.fromhex(evidence_digest))
    return ProtectedOperationSettlementEvidence(
        settlement_id=settlement_id, settlement_status=status,
        deployment_id=request.deployment_id, operation_id=request.operation_id,
        execution_id=request.execution_id, verification_id=request.verification_id,
        enforcement_evidence_digest=execution.consumption_record.evidence_digest,
        execution_evidence_digest=execution.attestation.attestation_digest,
        verification_evidence_digest=source.attestation.reconciliation_digest,
        settlement_policy_id=policy.policy_id, settlement_policy_version=policy.version,
        reason_code=reason, settled_at=settled_at, evidence_digest=evidence_digest,
        signature=signature,
    )


def verify_settlement_evidence(
    value: ProtectedOperationSettlementEvidence, signer: SettlementSigner,
) -> bool:
    if type(value) is not ProtectedOperationSettlementEvidence:
        return False
    try:
        document = _evidence_document(value)
        evidence_digest = sha256(_canonical({
            "domain": _EVIDENCE_DOMAIN, **document,
        })).hexdigest()
        settlement_id = sha256(_canonical({
            "domain": _EVIDENCE_DOMAIN, **document, "evidence_digest": evidence_digest,
        })).hexdigest()
        return (
            value.evidence_digest == evidence_digest
            and value.settlement_id == settlement_id
            and signer.verify(bytes.fromhex(evidence_digest), value.signature)
        )
    except Exception:
        return False


def _commit(
    request: ProtectedOperationSettlementRequest, request_digest: str, lifecycle_key: str,
    repository: SettlementEvidenceRepository, result: ProtectedOperationSettlementResult,
) -> ProtectedOperationSettlementResult:
    try:
        repository.commit(
            lifecycle_key=lifecycle_key, settlement_request_id=request.settlement_request_id,
            request_digest=request_digest, result=result,
        )
        return result
    except SettlementCommitStatusUnknown:
        return _result(
            request, Status.SUSPENDED, Reason.SETTLEMENT_COMMIT_INDETERMINATE,
            result.evaluated_at,
        )
    except Exception:
        return _result(
            request, Status.SUSPENDED, Reason.SETTLEMENT_REPOSITORY_UNAVAILABLE,
            result.evaluated_at,
        )


def settle_protected_operation(
    request: ProtectedOperationSettlementRequest, *,
    verification_repository: VerificationEvidenceRepository,
    policy_repository: SettlementPolicyRepository,
    settlement_repository: SettlementEvidenceRepository,
    signer: SettlementSigner,
    trusted_clock: Callable[[], datetime],
) -> ProtectedOperationSettlementResult:
    """Finalize one A.28 result without executing, observing, retrying, or remediating."""
    if type(request) is not ProtectedOperationSettlementRequest:
        raise ContinuedOperationSettlementError("an exact settlement request is required.")
    now = _trusted_now(trusted_clock)
    if now is None:
        return _result(request, Status.SUSPENDED, Reason.UNTRUSTED_TIME_SOURCE, request.requested_at)
    if request.requested_at > now:
        return _result(request, Status.REJECTED, Reason.LIFECYCLE_BINDING_MISMATCH, now)
    try:
        policy = policy_repository.get(
            request.settlement_policy_id, request.settlement_policy_version,
        )
    except Exception:
        policy = None
    if policy is None or type(policy) is not ProtectedOperationSettlementPolicy:
        return _result(request, Status.REJECTED, Reason.SETTLEMENT_POLICY_NOT_FOUND, now)
    try:
        source = verification_repository.get_committed(request.verification_id)
    except Exception:
        source = None
    if source is None:
        return _result(request, Status.REJECTED, Reason.UPSTREAM_EVIDENCE_MISSING, now)
    if type(source) is not AuthoritativeVerificationEvidence:
        return _result(request, Status.REJECTED, Reason.UPSTREAM_EVIDENCE_INVALID, now)
    admission_error = _admit_lineage(request, source, policy)
    if admission_error is not None:
        return _result(request, Status.REJECTED, admission_error, now)
    if now - source.attestation.evidence_issued_at > timedelta(
        seconds=policy.maximum_verification_age_seconds,
    ):
        status, reason = Status.SUSPENDED, Reason.VERIFICATION_EVIDENCE_EXPIRED
    else:
        status, reason = _decision(source.attestation.outcome, policy)
    request_digest = settlement_request_digest(request)
    lifecycle_key = settlement_lifecycle_key(request)
    try:
        claim = settlement_repository.claim(
            lifecycle_key=lifecycle_key, settlement_request_id=request.settlement_request_id,
            request_digest=request_digest,
        )
    except Exception:
        return _result(request, Status.SUSPENDED, Reason.SETTLEMENT_REPOSITORY_UNAVAILABLE, now)
    if claim.state is SettlementClaimState.REPLAY and claim.result is not None:
        return claim.result
    if claim.state is SettlementClaimState.CONFLICT:
        return _result(request, Status.REJECTED, Reason.CONFLICTING_SETTLEMENT, now)
    if claim.state is SettlementClaimState.IN_PROGRESS:
        return _result(request, Status.SUSPENDED, Reason.SETTLEMENT_COMMIT_INDETERMINATE, now)
    if claim.state is not SettlementClaimState.NEW:
        return _result(request, Status.SUSPENDED, Reason.SETTLEMENT_REPOSITORY_UNAVAILABLE, now)
    try:
        settlement_evidence = _make_evidence(
            request, source, policy, status, reason, now, signer,
        )
    except Exception:
        return _result(request, Status.REJECTED, Reason.UPSTREAM_EVIDENCE_INVALID, now)
    result = _result(request, status, reason, now, settlement_evidence)
    return _commit(request, request_digest, lifecycle_key, settlement_repository, result)


def public_protected_operation_settlement(
    request: ProtectedOperationSettlementRequest,
    result: ProtectedOperationSettlementResult,
) -> PublicProtectedOperationSettlementV1:
    if (type(request) is not ProtectedOperationSettlementRequest or
            type(result) is not ProtectedOperationSettlementResult or
            request.settlement_request_id != result.settlement_request_id):
        raise ContinuedOperationSettlementError("an exact settlement result is required.")
    evidence = result.evidence
    return PublicProtectedOperationSettlementV1(
        settlement_id=evidence.settlement_id if evidence else None,
        settlement_request_id=result.settlement_request_id,
        deployment_id=request.deployment_id, operation_id=request.operation_id,
        execution_id=request.execution_id, verification_id=request.verification_id,
        status=result.status, reason_code=result.reason_code,
        settled_at=evidence.settled_at if evidence else None,
        committed=result.committed, idempotent=result.idempotent,
    )


__all__ = [
    "HmacSettlementSigner", "InMemorySettlementEvidenceRepository",
    "InMemorySettlementPolicyRepository", "InMemoryVerificationEvidenceRepository",
    "SettlementCommitStatusUnknown", "SettlementPersistenceError",
    "SqliteSettlementEvidenceRepository", "public_protected_operation_settlement",
    "settle_protected_operation", "settlement_lifecycle_key", "settlement_request_digest",
    "settlement_request_document", "translate_untrusted_settlement_request",
    "verify_settlement_evidence",
]
