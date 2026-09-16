"""ATL-A.31 authorized-response reconciliation and ATL-A.21 handoff."""
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

from src.reference_architecture_continued_operation_response import verify_response_authorization
from src.reference_architecture_continued_operation_response_contract import ResponseOutcome, ResponseSigner
from src.reference_architecture_deployment_recovery import sign_decision
from src.reference_architecture_deployment_recovery_contract import (
    RecoveryDecisionStatus,
    RecoveryExecutionStatus,
    RecoveryVerificationStatus,
)
from src.reference_architecture_response_outcome_reconciliation_contract import *


_REQUEST_DOMAIN = "ai-test-lab:atl-a.31:request:v1"
_POLICY_DOMAIN = "ai-test-lab:atl-a.31:policy:v1"
_DECISION_DOMAIN = "ai-test-lab:atl-a.31:remediation-decision:v1"
_EXECUTION_DOMAIN = "ai-test-lab:atl-a.31:execution-attestation:v1"
_VERIFICATION_DOMAIN = "ai-test-lab:atl-a.31:post-remediation-verification:v1"
_LIFECYCLE_DOMAIN = "ai-test-lab:atl-a.31:lifecycle:v1"
_EVIDENCE_DOMAIN = "ai-test-lab:atl-a.31:reconciliation-evidence:v1"
_HANDOFF_DOMAIN = "ai-test-lab:atl-a.31:closure-handoff:v1"
_MAX_DOCUMENT_BYTES = 64 * 1024


class ReconciliationPersistenceError(RuntimeError):
    """The repository could not safely complete reconciliation persistence."""


class ReconciliationCommitStatusUnknown(ReconciliationPersistenceError):
    """The repository cannot establish whether the atomic commit completed."""


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                          allow_nan=False).encode("utf-8")
    except (TypeError, ValueError):
        raise ResponseOutcomeReconciliationError("canonical reconciliation payload is invalid.") from None


def _hash(value: Any) -> str:
    return sha256(_canonical(value)).hexdigest()


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


def reconciliation_request_document(value: ResponseOutcomeReconciliationRequest) -> dict[str, Any]:
    if type(value) is not ResponseOutcomeReconciliationRequest:
        raise ResponseOutcomeReconciliationError("an exact reconciliation request is required.")
    document = asdict(value)
    document["requested_at"] = _timestamp(value.requested_at)
    return document


def reconciliation_request_digest(value: ResponseOutcomeReconciliationRequest) -> str:
    return _hash({"domain": _REQUEST_DOMAIN, **reconciliation_request_document(value)})


def reconciliation_lifecycle_key(value: ResponseOutcomeReconciliationRequest) -> str:
    if type(value) is not ResponseOutcomeReconciliationRequest:
        raise ResponseOutcomeReconciliationError("an exact reconciliation request is required.")
    return _hash({"domain": _LIFECYCLE_DOMAIN,
                  "response_authorization_id": value.response_authorization_id})


def translate_untrusted_reconciliation_request(
    value: bytes | str | Mapping[str, Any],
) -> ResponseOutcomeReconciliationRequest:
    try:
        raw: bytes | None
        if type(value) is bytes:
            raw = value
            if len(raw) > _MAX_DOCUMENT_BYTES:
                raise ValueError
            document = json.loads(raw, object_pairs_hook=_no_duplicates,
                                  parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
        elif type(value) is str:
            raw = value.encode()
            if len(raw) > _MAX_DOCUMENT_BYTES:
                raise ValueError
            document = json.loads(raw, object_pairs_hook=_no_duplicates,
                                  parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
        elif type(value) is dict:
            raw = None
            document = dict(value)
            if len(_canonical(document)) > _MAX_DOCUMENT_BYTES:
                raise ValueError
        else:
            raise ValueError
        forbidden = {"authorization", "decision", "execution", "verification", "outcome",
                     "closure_eligible", "signature", "manifest", "scope", "capability"}
        if (type(document) is not dict or
                set(document) != set(ResponseOutcomeReconciliationRequest.__dataclass_fields__) or
                set(document) & forbidden):
            raise ValueError
        request = ResponseOutcomeReconciliationRequest(
            **{**document, "requested_at": _parse_time(document["requested_at"])}
        )
        if raw is not None and raw != _canonical(reconciliation_request_document(request)):
            raise ValueError
        return request
    except Exception as error:
        raise ResponseOutcomeReconciliationError("reconciliation request is invalid.") from error


def reconciliation_policy_document(value: ReconciliationPolicy) -> dict[str, Any]:
    if type(value) is not ReconciliationPolicy:
        raise ResponseOutcomeReconciliationError("an exact reconciliation policy is required.")
    return asdict(value)


def reconciliation_policy_digest(value: ReconciliationPolicy) -> str:
    return _hash({"domain": _POLICY_DOMAIN, **reconciliation_policy_document(value)})


def _remediation_request_document(value: Any) -> dict[str, Any]:
    return {
        "incident_id": value.incident_id, "deployment_id": value.deployment_id,
        "artifact_digest": value.artifact_digest, "tenant_id": value.tenant_id,
        "environment": value.environment, "action": value.action,
        "action_fingerprint": value.action_fingerprint,
        "requested_at": _timestamp(value.requested_at), "status": value.status.value,
    }


def remediation_decision_digest(value: Any) -> str:
    return _hash({"domain": _DECISION_DOMAIN, "request": _remediation_request_document(value.request),
                  "status": value.status.value, "expires_at": _timestamp(value.expires_at),
                  "authority_id": value.authority_id, "signature": value.signature})


def remediation_execution_digest(value: Any) -> str:
    return _hash({"domain": _EXECUTION_DOMAIN, "request": _remediation_request_document(value.request),
                  "status": value.status.value, "before_digest": value.before_digest,
                  "after_digest": value.after_digest, "executed_at": _timestamp(value.executed_at)})


def post_remediation_verification_digest(value: Any) -> str:
    return _hash({"domain": _VERIFICATION_DOMAIN,
                  "execution_digest": remediation_execution_digest(value.execution),
                  "integrity_evidence_digest": value.integrity_evidence_digest,
                  "outcome_evidence_digest": value.outcome_evidence_digest,
                  "status": value.status.value, "verified_at": _timestamp(value.verified_at)})


class HmacReconciliationSigner:
    """Reference signer; production deployments should inject managed keys."""

    def __init__(self, key: bytes, signer_id: str = "atl-a31-reference-signer") -> None:
        if type(key) is not bytes or len(key) < 32:
            raise ResponseOutcomeReconciliationError("reconciliation signing key is invalid.")
        identifier(signer_id, "signer_id")
        self._key = key
        self.signer_id = signer_id

    def sign(self, payload: bytes) -> str:
        if type(payload) is not bytes:
            raise ResponseOutcomeReconciliationError("reconciliation signing payload is invalid.")
        return hmac.new(self._key, payload, sha256).hexdigest()

    def verify(self, payload: bytes, signature: str) -> bool:
        try:
            return hmac.compare_digest(self.sign(payload), signature)
        except Exception:
            return False


class InMemoryResponseAuthorizationRecordRepository:
    def __init__(self, values: tuple[AuthoritativeResponseAuthorizationRecord, ...] = ()) -> None:
        self._values = {value.evidence.response_authorization_id: value for value in values}

    def get(self, record_id: str) -> AuthoritativeResponseAuthorizationRecord | None:
        return self._values.get(record_id)


class InMemoryRemediationDecisionRecordRepository:
    def __init__(self, values: tuple[AuthoritativeRemediationDecisionRecord, ...] = ()) -> None:
        self._values = {value.remediation_decision_id: value for value in values}

    def get(self, record_id: str) -> AuthoritativeRemediationDecisionRecord | None:
        return self._values.get(record_id)


class InMemoryRemediationExecutionRecordRepository:
    def __init__(self, values: tuple[AuthoritativeRemediationExecutionRecord, ...] = ()) -> None:
        self._values = {value.execution_attestation_id: value for value in values}

    def get(self, record_id: str) -> AuthoritativeRemediationExecutionRecord | None:
        return self._values.get(record_id)


class InMemoryPostRemediationVerificationRecordRepository:
    def __init__(self, values: tuple[AuthoritativePostRemediationVerificationRecord, ...] = ()) -> None:
        self._values = {value.post_remediation_verification_id: value for value in values}

    def get(self, record_id: str) -> AuthoritativePostRemediationVerificationRecord | None:
        return self._values.get(record_id)


class InMemoryReconciliationPolicyRepository:
    def __init__(self, values: tuple[ReconciliationPolicy, ...] = ()) -> None:
        self._values = {value.version: value for value in values}

    def get(self, version: str) -> ReconciliationPolicy | None:
        return self._values.get(version)


class InMemoryResponseReconciliationRepository:
    """Thread-safe atomic store for reconciliation plus optional handoff."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._records: dict[str, tuple[str, str, str, ReconciliationCommit | None]] = {}
        self._requests: dict[str, tuple[str, str]] = {}
        self._keys: dict[str, tuple[str, str]] = {}
        self._by_id: dict[str, ReconciliationCommit] = {}
        self._handoffs: dict[str, IncidentClosureHandoff] = {}

    def claim(self, *, lifecycle_key: str, request_id: str, idempotency_key: str,
              request_digest: str) -> AtomicReconciliationClaim:
        with self._lock:
            owner = (lifecycle_key, request_digest)
            if self._requests.get(request_id, owner) != owner or self._keys.get(idempotency_key, owner) != owner:
                return AtomicReconciliationClaim(ReconciliationClaimState.CONFLICT)
            current = self._records.get(lifecycle_key)
            if current is None:
                self._records[lifecycle_key] = (request_id, idempotency_key, request_digest, None)
                self._requests[request_id] = owner
                self._keys[idempotency_key] = owner
                return AtomicReconciliationClaim(ReconciliationClaimState.NEW)
            if current[:3] != (request_id, idempotency_key, request_digest):
                return AtomicReconciliationClaim(ReconciliationClaimState.CONFLICT)
            if current[3] is None:
                return AtomicReconciliationClaim(ReconciliationClaimState.IN_PROGRESS)
            return AtomicReconciliationClaim(ReconciliationClaimState.REPLAY, current[3])

    def commit(self, *, lifecycle_key: str, request_id: str, idempotency_key: str,
               request_digest: str, value: ReconciliationCommit) -> None:
        with self._lock:
            expected = (request_id, idempotency_key, request_digest)
            current = self._records.get(lifecycle_key)
            if current is None or current[:3] != expected:
                raise ReconciliationPersistenceError("reconciliation claim is unavailable")
            if current[3] is not None and current[3] != value:
                raise ReconciliationPersistenceError("reconciliation is immutable")
            self._records[lifecycle_key] = (*expected, value)
            self._by_id[value.evidence.reconciliation_id] = value
            if value.closure_handoff is not None:
                self._handoffs[value.closure_handoff.handoff_id] = value.closure_handoff

    def recover(self, lifecycle_key: str) -> AtomicReconciliationClaim:
        with self._lock:
            current = self._records.get(lifecycle_key)
            if current is None:
                return AtomicReconciliationClaim(ReconciliationClaimState.UNAVAILABLE)
            return (AtomicReconciliationClaim(ReconciliationClaimState.REPLAY, current[3])
                    if current[3] else AtomicReconciliationClaim(ReconciliationClaimState.IN_PROGRESS))

    def get_by_reconciliation_id(self, reconciliation_id: str) -> ReconciliationCommit | None:
        with self._lock:
            return self._by_id.get(reconciliation_id)

    def get_handoff(self, handoff_id: str) -> IncidentClosureHandoff | None:
        with self._lock:
            return self._handoffs.get(handoff_id)


def _evidence_document(value: ResponseOutcomeReconciliationEvidence) -> dict[str, Any]:
    document = asdict(value)
    for key in ("reconciliation_id", "evidence_digest", "signature"):
        document.pop(key)
    document["outcome"] = value.outcome.value
    document["reason_codes"] = [item.value for item in value.reason_codes]
    document["authorized_scope"] = list(value.authorized_scope)
    document["actual_scope"] = list(value.actual_scope)
    for key in ("authorization_issued_at", "authorization_expires_at", "created_at"):
        document[key] = _timestamp(getattr(value, key))
    return document


def _handoff_document(value: IncidentClosureHandoff) -> dict[str, Any]:
    document = asdict(value)
    for key in ("handoff_id", "handoff_digest", "signature"):
        document.pop(key)
    document["closure_scope"] = list(value.closure_scope)
    document["expires_at"] = _timestamp(value.expires_at)
    return document


def verify_reconciliation_evidence(value: ResponseOutcomeReconciliationEvidence,
                                   signer: ReconciliationSigner) -> bool:
    if type(value) is not ResponseOutcomeReconciliationEvidence:
        return False
    try:
        document = _evidence_document(value)
        evidence_digest = _hash({"domain": _EVIDENCE_DOMAIN, **document})
        reconciliation_id = _hash({"domain": _EVIDENCE_DOMAIN, **document,
                                   "evidence_digest": evidence_digest})
        return (value.evidence_digest == evidence_digest and
                value.reconciliation_id == reconciliation_id and
                value.signer_id == signer.signer_id and
                signer.verify(bytes.fromhex(evidence_digest), value.signature))
    except Exception:
        return False


def verify_closure_handoff(value: IncidentClosureHandoff, *,
                           reconciliation_repository: ResponseReconciliationRepository,
                           signer: ReconciliationSigner, trusted_clock: Callable[[], datetime],
                           required_policy_version: str) -> bool:
    """ATL-A.21-side validation reloads reconciliation instead of trusting the caller."""
    if type(value) is not IncidentClosureHandoff:
        return False
    try:
        now = _trusted_now(trusted_clock)
        commit = reconciliation_repository.get_by_reconciliation_id(value.reconciliation_id)
        document = _handoff_document(value)
        handoff_digest = _hash({"domain": _HANDOFF_DOMAIN, **document})
        handoff_id = _hash({"domain": _HANDOFF_DOMAIN, **document,
                            "handoff_digest": handoff_digest})
        evidence = commit.evidence if commit else None
        return bool(
            now is not None and now < value.expires_at and commit and
            commit.closure_handoff == value and evidence and
            verify_reconciliation_evidence(evidence, signer) and
            evidence.outcome is ReconciliationOutcome.VERIFIED_RECOVERY and
            evidence.closure_eligible and value.reconciliation_digest == evidence.evidence_digest and
            value.incident_id == evidence.incident_id and
            value.settlement_id == evidence.settlement_id and
            value.response_authorization_id == evidence.response_authorization_id and
            value.remediation_decision_id == evidence.remediation_decision_id and
            value.execution_attestation_id == evidence.execution_attestation_id and
            value.post_remediation_verification_id == evidence.post_remediation_verification_id and
            value.closure_scope == evidence.actual_scope and
            value.required_atl_a21_policy_version == required_policy_version and
            value.handoff_digest == handoff_digest and value.handoff_id == handoff_id and
            signer.verify(bytes.fromhex(handoff_digest), value.signature)
        )
    except Exception:
        return False


def _commit_document(value: ReconciliationCommit) -> dict[str, Any]:
    evidence = {**_evidence_document(value.evidence),
                "reconciliation_id": value.evidence.reconciliation_id,
                "evidence_digest": value.evidence.evidence_digest,
                "signature": value.evidence.signature}
    handoff = None
    if value.closure_handoff:
        handoff = {**_handoff_document(value.closure_handoff),
                   "handoff_id": value.closure_handoff.handoff_id,
                   "handoff_digest": value.closure_handoff.handoff_digest,
                   "signature": value.closure_handoff.signature}
    return {"evidence": evidence, "closure_handoff": handoff}


def _restore_commit(document: Mapping[str, Any]) -> ReconciliationCommit:
    raw = document["evidence"]
    evidence = ResponseOutcomeReconciliationEvidence(**{
        **raw, "outcome": ReconciliationOutcome(raw["outcome"]),
        "reason_codes": tuple(ReconciliationReasonCode(item) for item in raw["reason_codes"]),
        "authorized_scope": tuple(raw["authorized_scope"]), "actual_scope": tuple(raw["actual_scope"]),
        "authorization_issued_at": _parse_time(raw["authorization_issued_at"]),
        "authorization_expires_at": _parse_time(raw["authorization_expires_at"]),
        "created_at": _parse_time(raw["created_at"]),
    })
    handoff_raw = document["closure_handoff"]
    handoff = None if handoff_raw is None else IncidentClosureHandoff(**{
        **handoff_raw, "closure_scope": tuple(handoff_raw["closure_scope"]),
        "expires_at": _parse_time(handoff_raw["expires_at"]),
    })
    return ReconciliationCommit(evidence, handoff)


class SqliteResponseReconciliationRepository:
    """Durable atomic reconciliation/handoff store with restart recovery."""

    def __init__(self, path: str | Path) -> None:
        self._path = str(path)
        connection = self._connect()
        try:
            connection.execute("""CREATE TABLE IF NOT EXISTS response_reconciliation (
                lifecycle_key TEXT PRIMARY KEY, request_id TEXT NOT NULL UNIQUE,
                idempotency_key TEXT NOT NULL UNIQUE, request_digest TEXT NOT NULL,
                reconciliation_id TEXT UNIQUE, handoff_id TEXT UNIQUE, commit_json TEXT)""")
            connection.commit()
        finally:
            connection.close()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._path, timeout=30, isolation_level=None)
        connection.execute("PRAGMA journal_mode=WAL")
        return connection

    def claim(self, *, lifecycle_key: str, request_id: str, idempotency_key: str,
              request_digest: str) -> AtomicReconciliationClaim:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT request_id,idempotency_key,request_digest,commit_json FROM response_reconciliation WHERE lifecycle_key=?",
                (lifecycle_key,)).fetchone()
            by_request = connection.execute(
                "SELECT lifecycle_key,request_digest FROM response_reconciliation WHERE request_id=?", (request_id,)).fetchone()
            by_key = connection.execute(
                "SELECT lifecycle_key,request_digest FROM response_reconciliation WHERE idempotency_key=?", (idempotency_key,)).fetchone()
            owner = (lifecycle_key, request_digest)
            if ((by_request is not None and by_request != owner) or (by_key is not None and by_key != owner)):
                connection.rollback()
                return AtomicReconciliationClaim(ReconciliationClaimState.CONFLICT)
            if row is None:
                connection.execute("INSERT INTO response_reconciliation VALUES (?,?,?,?,NULL,NULL,NULL)",
                                   (lifecycle_key, request_id, idempotency_key, request_digest))
                connection.commit()
                return AtomicReconciliationClaim(ReconciliationClaimState.NEW)
            connection.commit()
            if row[:3] != (request_id, idempotency_key, request_digest):
                return AtomicReconciliationClaim(ReconciliationClaimState.CONFLICT)
            if row[3] is None:
                return AtomicReconciliationClaim(ReconciliationClaimState.IN_PROGRESS)
            return AtomicReconciliationClaim(ReconciliationClaimState.REPLAY, _restore_commit(json.loads(row[3])))
        except sqlite3.IntegrityError:
            try: connection.rollback()
            except sqlite3.Error: pass
            return AtomicReconciliationClaim(ReconciliationClaimState.CONFLICT)
        except sqlite3.Error as error:
            try: connection.rollback()
            except sqlite3.Error: pass
            raise ReconciliationPersistenceError("reconciliation claim failed") from error
        finally:
            connection.close()

    def commit(self, *, lifecycle_key: str, request_id: str, idempotency_key: str,
               request_digest: str, value: ReconciliationCommit) -> None:
        payload = _canonical(_commit_document(value)).decode()
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT request_id,idempotency_key,request_digest,commit_json FROM response_reconciliation WHERE lifecycle_key=?",
                (lifecycle_key,)).fetchone()
            if row is None or row[:3] != (request_id, idempotency_key, request_digest):
                connection.rollback()
                raise ReconciliationPersistenceError("reconciliation claim is unavailable")
            if row[3] is not None:
                connection.rollback()
                if row[3] != payload:
                    raise ReconciliationPersistenceError("reconciliation is immutable")
                return
            connection.execute(
                "UPDATE response_reconciliation SET reconciliation_id=?,handoff_id=?,commit_json=? WHERE lifecycle_key=? AND commit_json IS NULL",
                (value.evidence.reconciliation_id,
                 value.closure_handoff.handoff_id if value.closure_handoff else None,
                 payload, lifecycle_key))
            connection.commit()
        except ReconciliationPersistenceError:
            raise
        except sqlite3.Error as error:
            try: connection.rollback()
            except sqlite3.Error: pass
            raise ReconciliationCommitStatusUnknown("reconciliation commit status is unknown") from error
        finally:
            connection.close()

    def recover(self, lifecycle_key: str) -> AtomicReconciliationClaim:
        connection = self._connect()
        try:
            row = connection.execute("SELECT commit_json FROM response_reconciliation WHERE lifecycle_key=?",
                                     (lifecycle_key,)).fetchone()
            if row is None:
                return AtomicReconciliationClaim(ReconciliationClaimState.UNAVAILABLE)
            if row[0] is None:
                return AtomicReconciliationClaim(ReconciliationClaimState.IN_PROGRESS)
            return AtomicReconciliationClaim(ReconciliationClaimState.REPLAY, _restore_commit(json.loads(row[0])))
        finally:
            connection.close()

    def _lookup(self, column: str, value: str) -> ReconciliationCommit | None:
        connection = self._connect()
        try:
            row = connection.execute(f"SELECT commit_json FROM response_reconciliation WHERE {column}=?", (value,)).fetchone()
            return _restore_commit(json.loads(row[0])) if row and row[0] else None
        finally:
            connection.close()

    def get_by_reconciliation_id(self, reconciliation_id: str) -> ReconciliationCommit | None:
        return self._lookup("reconciliation_id", reconciliation_id)

    def get_handoff(self, handoff_id: str) -> IncidentClosureHandoff | None:
        commit = self._lookup("handoff_id", handoff_id)
        return commit.closure_handoff if commit else None


def _trusted_now(clock: Callable[[], datetime]) -> datetime | None:
    try:
        value = clock()
        if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None or value.microsecond:
            return None
        return value.astimezone(timezone.utc)
    except Exception:
        return None


def _load(repository: Any, record_id: str) -> Any | None:
    try:
        return repository.get(record_id)
    except Exception:
        return None


def _valid_decision(record: AuthoritativeRemediationDecisionRecord, authorization: Any) -> bool:
    try:
        decision = record.decision
        return bool(
            record.committed and record.response_authorization_id == authorization.response_authorization_id and
            record.decision_digest == remediation_decision_digest(decision) and
            decision == sign_decision(decision.request, decision.status, decision.expires_at, decision.authority_id) and
            decision.status is RecoveryDecisionStatus.APPROVED and
            decision.request.incident_id == authorization.incident_id and
            decision.request.deployment_id == authorization.deployment_id and
            decision.request.artifact_digest == authorization.enforcement_evidence_digest and
            decision.request.action == authorization.remediation_capability and
            decision.request.action_fingerprint == authorization.response_manifest_digest
        )
    except Exception:
        return False


def _execution_reason(record: AuthoritativeRemediationExecutionRecord, decision: Any,
                      authorization: Any) -> ReconciliationReasonCode | None:
    try:
        if (not record.committed or record.response_authorization_id != authorization.response_authorization_id or
                record.remediation_decision_id == "" or
                record.execution_digest != remediation_execution_digest(record.execution) or
                record.execution.request != decision.request):
            return ReconciliationReasonCode.EXECUTION_EVIDENCE_INVALID
        if record.execution.executed_at > authorization.expires_at:
            return ReconciliationReasonCode.EXECUTION_AFTER_EXPIRY
        if record.capability != authorization.remediation_capability:
            return ReconciliationReasonCode.CAPABILITY_MISMATCH
        if not set(record.scope).issubset(authorization.scope):
            return ReconciliationReasonCode.SCOPE_EXPANSION
        if not set(authorization.constraints).issubset(record.constraints):
            return ReconciliationReasonCode.CONSTRAINTS_WEAKENED
        if record.manifest_digest != authorization.response_manifest_digest:
            return ReconciliationReasonCode.MANIFEST_MISMATCH
        if record.attempt_number > authorization.maximum_attempts:
            return ReconciliationReasonCode.ATTEMPT_LIMIT_EXCEEDED
        return None
    except Exception:
        return ReconciliationReasonCode.EXECUTION_EVIDENCE_INVALID


def _verification_valid(record: AuthoritativePostRemediationVerificationRecord,
                        execution_record: AuthoritativeRemediationExecutionRecord) -> bool:
    try:
        return bool(
            record.committed and record.execution_attestation_id == execution_record.execution_attestation_id and
            record.verification.execution == execution_record.execution and
            record.verification_digest == post_remediation_verification_digest(record.verification) and
            record.target_scope == execution_record.scope and
            record.verification.verified_at >= execution_record.execution.executed_at
        )
    except Exception:
        return False


def _make_evidence(*, request: ResponseOutcomeReconciliationRequest, authorization: Any,
                   decision_record: AuthoritativeRemediationDecisionRecord,
                   execution_record: AuthoritativeRemediationExecutionRecord,
                   verification_record: AuthoritativePostRemediationVerificationRecord,
                   policy: ReconciliationPolicy, outcome: ReconciliationOutcome,
                   reason: ReconciliationReasonCode, now: datetime,
                   signer: ReconciliationSigner) -> ResponseOutcomeReconciliationEvidence:
    values = {
        "schema_version": RESPONSE_RECONCILIATION_EVIDENCE_VERSION,
        "request_id": request.request_id, "idempotency_key": request.idempotency_key,
        "incident_id": authorization.incident_id, "protected_operation_id": authorization.operation_id,
        "settlement_id": authorization.settlement_id, "settlement_digest": authorization.settlement_digest,
        "response_authorization_id": authorization.response_authorization_id,
        "response_authorization_digest": authorization.authorization_digest,
        "remediation_decision_id": decision_record.remediation_decision_id,
        "remediation_decision_digest": decision_record.decision_digest,
        "execution_attestation_id": execution_record.execution_attestation_id,
        "execution_attestation_digest": execution_record.execution_digest,
        "post_remediation_verification_id": verification_record.post_remediation_verification_id,
        "post_remediation_verification_digest": verification_record.verification_digest,
        "authorized_capability": authorization.remediation_capability,
        "authorized_scope": list(authorization.scope), "actual_capability": execution_record.capability,
        "actual_scope": list(execution_record.scope),
        "authorization_issued_at": _timestamp(authorization.created_at),
        "authorization_expires_at": _timestamp(authorization.expires_at),
        "consumed_attempt": execution_record.attempt_number,
        "maximum_attempts": authorization.maximum_attempts,
        "policy_id": policy.policy_id, "policy_version": policy.version,
        "outcome": outcome.value, "reason_codes": [reason.value],
        "closure_eligible": outcome is ReconciliationOutcome.VERIFIED_RECOVERY,
        "created_at": _timestamp(now), "signer_id": signer.signer_id,
    }
    evidence_digest = _hash({"domain": _EVIDENCE_DOMAIN, **values})
    reconciliation_id = _hash({"domain": _EVIDENCE_DOMAIN, **values,
                               "evidence_digest": evidence_digest})
    return ResponseOutcomeReconciliationEvidence(
        reconciliation_id=reconciliation_id, request_id=request.request_id,
        idempotency_key=request.idempotency_key, incident_id=authorization.incident_id,
        protected_operation_id=authorization.operation_id, settlement_id=authorization.settlement_id,
        settlement_digest=authorization.settlement_digest,
        response_authorization_id=authorization.response_authorization_id,
        response_authorization_digest=authorization.authorization_digest,
        remediation_decision_id=decision_record.remediation_decision_id,
        remediation_decision_digest=decision_record.decision_digest,
        execution_attestation_id=execution_record.execution_attestation_id,
        execution_attestation_digest=execution_record.execution_digest,
        post_remediation_verification_id=verification_record.post_remediation_verification_id,
        post_remediation_verification_digest=verification_record.verification_digest,
        authorized_capability=authorization.remediation_capability, authorized_scope=authorization.scope,
        actual_capability=execution_record.capability, actual_scope=execution_record.scope,
        authorization_issued_at=authorization.created_at, authorization_expires_at=authorization.expires_at,
        consumed_attempt=execution_record.attempt_number, maximum_attempts=authorization.maximum_attempts,
        policy_id=policy.policy_id, policy_version=policy.version, outcome=outcome,
        reason_codes=(reason,), closure_eligible=outcome is ReconciliationOutcome.VERIFIED_RECOVERY,
        created_at=now, evidence_digest=evidence_digest, signer_id=signer.signer_id,
        signature=signer.sign(bytes.fromhex(evidence_digest)),
    )


def _make_handoff(evidence: ResponseOutcomeReconciliationEvidence, policy: ReconciliationPolicy,
                  signer: ReconciliationSigner) -> IncidentClosureHandoff:
    expires_at = evidence.created_at + timedelta(seconds=policy.closure_handoff_lifetime_seconds)
    values = {
        "reconciliation_id": evidence.reconciliation_id,
        "reconciliation_digest": evidence.evidence_digest, "incident_id": evidence.incident_id,
        "settlement_id": evidence.settlement_id,
        "response_authorization_id": evidence.response_authorization_id,
        "remediation_decision_id": evidence.remediation_decision_id,
        "execution_attestation_id": evidence.execution_attestation_id,
        "post_remediation_verification_id": evidence.post_remediation_verification_id,
        "closure_capability": policy.closure_capability,
        "closure_scope": list(evidence.actual_scope),
        "required_atl_a21_policy_version": policy.required_atl_a21_policy_version,
        "expires_at": _timestamp(expires_at),
    }
    handoff_digest = _hash({"domain": _HANDOFF_DOMAIN, **values})
    handoff_id = _hash({"domain": _HANDOFF_DOMAIN, **values, "handoff_digest": handoff_digest})
    return IncidentClosureHandoff(
        handoff_id, evidence.reconciliation_id, evidence.evidence_digest, evidence.incident_id,
        evidence.settlement_id, evidence.response_authorization_id, evidence.remediation_decision_id,
        evidence.execution_attestation_id, evidence.post_remediation_verification_id,
        policy.closure_capability, evidence.actual_scope, policy.required_atl_a21_policy_version,
        expires_at, handoff_digest, signer.sign(bytes.fromhex(handoff_digest)),
    )


def _make_expired_unexecuted_evidence(
    *, request: ResponseOutcomeReconciliationRequest, authorization: Any,
    decision_record: AuthoritativeRemediationDecisionRecord, policy: ReconciliationPolicy,
    now: datetime, signer: ReconciliationSigner,
) -> ResponseOutcomeReconciliationEvidence:
    """Bind an expired lifecycle without inventing accepted execution evidence."""
    absent_execution_digest = _hash({"domain": _EXECUTION_DOMAIN, "status": "absent",
                                     "reference": request.execution_attestation_id})
    absent_verification_digest = _hash({"domain": _VERIFICATION_DOMAIN, "status": "absent",
                                        "reference": request.post_remediation_verification_id})
    reason = ReconciliationReasonCode.AUTHORIZATION_EXPIRED_UNEXECUTED
    values = {
        "schema_version": RESPONSE_RECONCILIATION_EVIDENCE_VERSION,
        "request_id": request.request_id, "idempotency_key": request.idempotency_key,
        "incident_id": authorization.incident_id, "protected_operation_id": authorization.operation_id,
        "settlement_id": authorization.settlement_id, "settlement_digest": authorization.settlement_digest,
        "response_authorization_id": authorization.response_authorization_id,
        "response_authorization_digest": authorization.authorization_digest,
        "remediation_decision_id": decision_record.remediation_decision_id,
        "remediation_decision_digest": decision_record.decision_digest,
        "execution_attestation_id": request.execution_attestation_id,
        "execution_attestation_digest": absent_execution_digest,
        "post_remediation_verification_id": request.post_remediation_verification_id,
        "post_remediation_verification_digest": absent_verification_digest,
        "authorized_capability": authorization.remediation_capability,
        "authorized_scope": list(authorization.scope), "actual_capability": "not-executed",
        "actual_scope": list(authorization.scope),
        "authorization_issued_at": _timestamp(authorization.created_at),
        "authorization_expires_at": _timestamp(authorization.expires_at),
        "consumed_attempt": 0, "maximum_attempts": authorization.maximum_attempts,
        "policy_id": policy.policy_id, "policy_version": policy.version,
        "outcome": ReconciliationOutcome.EXPIRED_UNEXECUTED.value,
        "reason_codes": [reason.value], "closure_eligible": False,
        "created_at": _timestamp(now), "signer_id": signer.signer_id,
    }
    evidence_digest = _hash({"domain": _EVIDENCE_DOMAIN, **values})
    reconciliation_id = _hash({"domain": _EVIDENCE_DOMAIN, **values,
                               "evidence_digest": evidence_digest})
    return ResponseOutcomeReconciliationEvidence(
        reconciliation_id, request.request_id, request.idempotency_key,
        authorization.incident_id, authorization.operation_id, authorization.settlement_id,
        authorization.settlement_digest, authorization.response_authorization_id,
        authorization.authorization_digest, decision_record.remediation_decision_id,
        decision_record.decision_digest, request.execution_attestation_id,
        absent_execution_digest, request.post_remediation_verification_id,
        absent_verification_digest, authorization.remediation_capability, authorization.scope,
        "not-executed", authorization.scope, authorization.created_at, authorization.expires_at,
        0, authorization.maximum_attempts, policy.policy_id, policy.version,
        ReconciliationOutcome.EXPIRED_UNEXECUTED, (reason,), False, now, evidence_digest,
        signer.signer_id, signer.sign(bytes.fromhex(evidence_digest)),
    )


def reconcile_authorized_response(
    request: ResponseOutcomeReconciliationRequest, *,
    authorization_repository: ResponseAuthorizationRecordRepository,
    decision_repository: RemediationDecisionRecordRepository,
    execution_repository: RemediationExecutionRecordRepository,
    verification_repository: PostRemediationVerificationRecordRepository,
    policy_repository: ReconciliationPolicyRepository,
    reconciliation_repository: ResponseReconciliationRepository,
    response_signer: ResponseSigner, reconciliation_signer: ReconciliationSigner,
    trusted_clock: Callable[[], datetime],
) -> ReconciliationCommit:
    """Reconcile repository-loaded evidence; never execute or retry remediation."""
    if type(request) is not ResponseOutcomeReconciliationRequest:
        raise ResponseOutcomeReconciliationError("an exact reconciliation request is required.")
    now = _trusted_now(trusted_clock)
    if now is None:
        raise ResponseOutcomeReconciliationError(ReconciliationReasonCode.UNTRUSTED_TIME_SOURCE.value)
    if request.requested_at > now:
        raise ResponseOutcomeReconciliationError(ReconciliationReasonCode.LINEAGE_MISMATCH.value)
    request_digest = reconciliation_request_digest(request)
    lifecycle_key = reconciliation_lifecycle_key(request)
    try:
        claim = reconciliation_repository.claim(
            lifecycle_key=lifecycle_key, request_id=request.request_id,
            idempotency_key=request.idempotency_key, request_digest=request_digest)
    except Exception as error:
        raise ResponseOutcomeReconciliationError(ReconciliationReasonCode.REPOSITORY_UNAVAILABLE.value) from error
    if claim.state is ReconciliationClaimState.REPLAY and claim.commit is not None:
        return claim.commit
    if claim.state is ReconciliationClaimState.CONFLICT:
        raise ResponseOutcomeReconciliationError(ReconciliationReasonCode.IDEMPOTENCY_CONFLICT.value)
    if claim.state is ReconciliationClaimState.IN_PROGRESS:
        raise ResponseOutcomeReconciliationError(ReconciliationReasonCode.RECONCILIATION_IN_PROGRESS.value)
    if claim.state is not ReconciliationClaimState.NEW:
        raise ResponseOutcomeReconciliationError(ReconciliationReasonCode.REPOSITORY_UNAVAILABLE.value)

    authorization_record = _load(authorization_repository, request.response_authorization_id)
    decision_record = _load(decision_repository, request.remediation_decision_id)
    execution_record = _load(execution_repository, request.execution_attestation_id)
    verification_record = _load(verification_repository, request.post_remediation_verification_id)
    try:
        policy = policy_repository.get(request.reconciliation_policy_version)
    except Exception:
        policy = None
    if policy is None or type(policy) is not ReconciliationPolicy:
        raise ResponseOutcomeReconciliationError(ReconciliationReasonCode.POLICY_NOT_FOUND.value)
    if not all((authorization_record, decision_record, execution_record, verification_record)):
        # Expiry is authoritative only when the authorization and decision are valid and
        # the trusted execution repository has no accepted attestation.
        if (authorization_record is not None and decision_record is not None and
                execution_record is None and now >= authorization_record.evidence.expires_at and
                authorization_record.committed and
                verify_response_authorization(authorization_record.evidence, response_signer) and
                _valid_decision(decision_record, authorization_record.evidence)):
            evidence = _make_expired_unexecuted_evidence(
                request=request, authorization=authorization_record.evidence,
                decision_record=decision_record, policy=policy, now=now,
                signer=reconciliation_signer,
            )
            commit = ReconciliationCommit(evidence, None)
            try:
                reconciliation_repository.commit(
                    lifecycle_key=lifecycle_key, request_id=request.request_id,
                    idempotency_key=request.idempotency_key, request_digest=request_digest,
                    value=commit,
                )
            except Exception as error:
                raise ResponseOutcomeReconciliationError(
                    ReconciliationReasonCode.REPOSITORY_UNAVAILABLE.value
                ) from error
            return commit
        raise ResponseOutcomeReconciliationError(ReconciliationReasonCode.LINEAGE_MISMATCH.value)

    authorization = authorization_record.evidence
    reason: ReconciliationReasonCode | None = None
    if (not authorization_record.committed or authorization.response_outcome is not ResponseOutcome.AUTHORIZED or
            not verify_response_authorization(authorization, response_signer)):
        reason = ReconciliationReasonCode.AUTHORIZATION_INVALID
    elif not _valid_decision(decision_record, authorization):
        reason = ReconciliationReasonCode.REMEDIATION_DECISION_INVALID
    elif decision_record.remediation_decision_id != execution_record.remediation_decision_id:
        reason = ReconciliationReasonCode.LINEAGE_MISMATCH
    else:
        reason = _execution_reason(execution_record, decision_record.decision, authorization)
    if reason is None and not _verification_valid(verification_record, execution_record):
        reason = ReconciliationReasonCode.VERIFICATION_EVIDENCE_INVALID

    if reason is not None:
        outcome = ReconciliationOutcome.REJECTED
    elif execution_record.execution.status is not RecoveryExecutionStatus.EXECUTED:
        outcome = ReconciliationOutcome.RESPONSE_FAILED
        reason = ReconciliationReasonCode.RECOVERY_VERIFICATION_FAILED
    elif verification_record.verification.status is RecoveryVerificationStatus.PASSED:
        outcome = ReconciliationOutcome.VERIFIED_RECOVERY
        reason = ReconciliationReasonCode.RECOVERY_INDEPENDENTLY_VERIFIED
    elif verification_record.verification.status is RecoveryVerificationStatus.FAILED:
        outcome = ReconciliationOutcome.RESPONSE_FAILED
        reason = ReconciliationReasonCode.RECOVERY_VERIFICATION_FAILED
    else:
        outcome = ReconciliationOutcome.RESPONSE_INDETERMINATE
        reason = ReconciliationReasonCode.RECOVERY_VERIFICATION_INCONCLUSIVE

    evidence = _make_evidence(
        request=request, authorization=authorization, decision_record=decision_record,
        execution_record=execution_record, verification_record=verification_record,
        policy=policy, outcome=outcome, reason=reason, now=now, signer=reconciliation_signer,
    )
    handoff = (_make_handoff(evidence, policy, reconciliation_signer)
               if outcome is ReconciliationOutcome.VERIFIED_RECOVERY else None)
    commit = ReconciliationCommit(evidence, handoff)
    try:
        reconciliation_repository.commit(
            lifecycle_key=lifecycle_key, request_id=request.request_id,
            idempotency_key=request.idempotency_key, request_digest=request_digest, value=commit)
    except ReconciliationCommitStatusUnknown as error:
        raise ResponseOutcomeReconciliationError(ReconciliationReasonCode.COMMIT_INDETERMINATE.value) from error
    except Exception as error:
        raise ResponseOutcomeReconciliationError(ReconciliationReasonCode.REPOSITORY_UNAVAILABLE.value) from error
    return commit


def public_response_outcome_reconciliation(
    value: ResponseOutcomeReconciliationEvidence,
) -> PublicResponseOutcomeReconciliationV1:
    if type(value) is not ResponseOutcomeReconciliationEvidence:
        raise ResponseOutcomeReconciliationError("reconciliation evidence is invalid.")
    return PublicResponseOutcomeReconciliationV1(
        reconciliation_id=value.reconciliation_id, incident_id=value.incident_id,
        outcome=value.outcome, reason_codes=value.reason_codes,
        closure_eligible=value.closure_eligible, policy_version=value.policy_version,
        created_at=value.created_at, protected_operation_id=value.protected_operation_id,
        settlement_id=value.settlement_id,
        response_authorization_id=value.response_authorization_id,
        remediation_decision_id=value.remediation_decision_id,
        execution_attestation_id=value.execution_attestation_id,
        post_remediation_verification_id=value.post_remediation_verification_id,
    )


__all__ = [name for name in globals() if not name.startswith("_")]
