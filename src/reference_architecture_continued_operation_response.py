"""ATL-A.30 settled-outcome response authorization and ATL-A.20 handoff."""
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

from src.reference_architecture_continued_operation_response_contract import (
    CONTINUED_OPERATION_RESPONSE_EVIDENCE_VERSION,
    AtlA20ResponseHandoff,
    AtomicResponseClaim,
    AuthoritativeSettlementRecord,
    ContinuedOperationResponseError,
    PublicSettledOutcomeResponseV1,
    ResponseAuthorizationEvidence,
    ResponseAuthorizationRepository,
    ResponseClaimState,
    ResponseManifest,
    ResponseManifestRepository,
    ResponseOutcome,
    ResponsePolicy,
    ResponsePolicyRepository,
    ResponseReasonCode,
    ResponseSigner,
    ResponseType,
    SettlementRecordRepository,
    SettledOutcomeResponseRequest,
    SettledOutcomeResponseResult,
)
from src.reference_architecture_continued_operation_settlement import verify_settlement_evidence
from src.reference_architecture_continued_operation_settlement_contract import (
    ProtectedOperationSettlementStatus as SettlementStatus,
    SettlementSigner,
)
from src.reference_architecture_deployment_recovery_contract import RemediationRequest


_REQUEST_DOMAIN = "ai-test-lab:atl-a.30:response-request:v1"
_POLICY_DOMAIN = "ai-test-lab:atl-a.30:response-policy:v1"
_MANIFEST_DOMAIN = "ai-test-lab:atl-a.30:response-manifest:v1"
_LIFECYCLE_DOMAIN = "ai-test-lab:atl-a.30:response-lifecycle:v1"
_INCIDENT_DOMAIN = "ai-test-lab:atl-a.30:incident:v1"
_EVIDENCE_DOMAIN = "ai-test-lab:atl-a.30:response-authorization:v1"
_MAX_DOCUMENT_BYTES = 64 * 1024


class ResponsePersistenceError(RuntimeError):
    """The response repository could not safely complete an operation."""


class ResponseCommitStatusUnknown(ResponsePersistenceError):
    """The repository cannot establish whether the authorization committed."""


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                          allow_nan=False).encode("utf-8")
    except (TypeError, ValueError):
        raise ContinuedOperationResponseError("response canonical payload is invalid.") from None


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


def response_request_document(value: SettledOutcomeResponseRequest) -> dict[str, Any]:
    if type(value) is not SettledOutcomeResponseRequest:
        raise ContinuedOperationResponseError("an exact response request is required.")
    document = asdict(value)
    document["requested_response_type"] = value.requested_response_type.value
    document["requested_scope"] = list(value.requested_scope)
    document["requested_at"] = _timestamp(value.requested_at)
    return document


def response_request_digest(value: SettledOutcomeResponseRequest) -> str:
    return sha256(_canonical({"domain": _REQUEST_DOMAIN, **response_request_document(value)})).hexdigest()


def response_lifecycle_key(value: SettledOutcomeResponseRequest) -> str:
    if type(value) is not SettledOutcomeResponseRequest:
        raise ContinuedOperationResponseError("an exact response request is required.")
    return sha256(_canonical({
        "domain": _LIFECYCLE_DOMAIN,
        "settlement_id": value.settlement_id,
        "response_type": value.requested_response_type.value,
    })).hexdigest()


def translate_untrusted_response_request(value: bytes | str | Mapping[str, Any]) -> SettledOutcomeResponseRequest:
    try:
        raw: bytes | None
        if type(value) is bytes:
            raw = value
            if len(raw) > _MAX_DOCUMENT_BYTES:
                raise ValueError
            document = json.loads(raw, object_pairs_hook=_no_duplicates,
                                  parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
        elif type(value) is str:
            raw = value.encode("utf-8")
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
        forbidden = {
            "settlement_evidence", "policy", "manifest", "response_outcome", "authorized",
            "command", "provider_payload", "credentials", "secret", "token", "retry",
        }
        if (type(document) is not dict or
                set(document) != set(SettledOutcomeResponseRequest.__dataclass_fields__) or
                set(document) & forbidden):
            raise ValueError
        request = SettledOutcomeResponseRequest(**{
            **document,
            "requested_response_type": ResponseType(document["requested_response_type"]),
            "requested_scope": tuple(document["requested_scope"]),
            "requested_at": _parse_time(document["requested_at"]),
        })
        if raw is not None and raw != _canonical(response_request_document(request)):
            raise ValueError
        return request
    except Exception as error:
        raise ContinuedOperationResponseError("response request is invalid.") from error


def response_policy_document(value: ResponsePolicy) -> dict[str, Any]:
    if type(value) is not ResponsePolicy:
        raise ContinuedOperationResponseError("an exact response policy is required.")
    return {
        "approved_manifest_references": list(value.approved_manifest_references),
        "authorized_roles": list(value.authorized_roles),
        "maximum_authorization_seconds": value.maximum_authorization_seconds,
        "permitted_failure_types": [item.value for item in value.permitted_failure_types],
        "permitted_scopes": list(value.permitted_scopes),
        "permitted_suspended_types": [item.value for item in value.permitted_suspended_types],
        "policy_id": value.policy_id, "require_manual_review_for_suspended": value.require_manual_review_for_suspended,
        "version": value.version,
    }


def response_policy_digest(value: ResponsePolicy) -> str:
    return sha256(_canonical({"domain": _POLICY_DOMAIN, **response_policy_document(value)})).hexdigest()


def response_manifest_document(value: ResponseManifest) -> dict[str, Any]:
    if type(value) is not ResponseManifest:
        raise ContinuedOperationResponseError("an exact response manifest is required.")
    return {
        "constraints": list(value.constraints), "lifetime_seconds": value.lifetime_seconds,
        "manifest_id": value.manifest_id, "maximum_attempts": value.maximum_attempts,
        "permitted_scopes": list(value.permitted_scopes),
        "permitted_settlement_statuses": [item.value for item in value.permitted_settlement_statuses],
        "post_remediation_verification_required": value.post_remediation_verification_required,
        "prohibited_operations": list(value.prohibited_operations),
        "remediation_capability": value.remediation_capability,
        "required_evidence": list(value.required_evidence), "required_roles": list(value.required_roles),
        "response_type": value.response_type.value, "version": value.version,
    }


def response_manifest_digest(value: ResponseManifest) -> str:
    return sha256(_canonical({"domain": _MANIFEST_DOMAIN, **response_manifest_document(value)})).hexdigest()


class HmacResponseSigner:
    """Reference signer; production deployments should inject a managed-key adapter."""

    def __init__(self, key: bytes) -> None:
        if type(key) is not bytes or len(key) < 32:
            raise ContinuedOperationResponseError("response signing key is invalid.")
        self._key = key

    def sign(self, payload: bytes) -> str:
        if type(payload) is not bytes:
            raise ContinuedOperationResponseError("response signing payload is invalid.")
        return hmac.new(self._key, payload, sha256).hexdigest()

    def verify(self, payload: bytes, signature: str) -> bool:
        try:
            return hmac.compare_digest(self.sign(payload), signature)
        except Exception:
            return False


class InMemorySettlementRecordRepository:
    def __init__(self, values: tuple[AuthoritativeSettlementRecord, ...] = ()) -> None:
        self._values = {value.evidence.settlement_id: value for value in values}

    def get_committed(self, settlement_id: str) -> AuthoritativeSettlementRecord | None:
        value = self._values.get(settlement_id)
        return value if value is not None and value.committed else None


class InMemoryResponsePolicyRepository:
    def __init__(self, values: tuple[ResponsePolicy, ...] = ()) -> None:
        self._values = {(value.policy_id, value.version): value for value in values}

    def get(self, policy_id: str, version: str) -> ResponsePolicy | None:
        return self._values.get((policy_id, version))


class InMemoryResponseManifestRepository:
    def __init__(self, values: tuple[ResponseManifest, ...] = ()) -> None:
        self._values = {(value.manifest_id, value.version): value for value in values}

    def get(self, manifest_id: str, version: str) -> ResponseManifest | None:
        return self._values.get((manifest_id, version))


class InMemoryResponseAuthorizationRepository:
    """Thread-safe single-winner repository across lifecycle, request, and idempotency keys."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._records: dict[str, tuple[str, str, str, SettledOutcomeResponseResult | None]] = {}
        self._requests: dict[str, tuple[str, str]] = {}
        self._idempotency: dict[str, tuple[str, str]] = {}

    def claim(self, *, lifecycle_key: str, response_request_id: str,
              idempotency_key: str, request_digest: str) -> AtomicResponseClaim:
        with self._lock:
            owner = (lifecycle_key, request_digest)
            if self._requests.get(response_request_id, owner) != owner:
                return AtomicResponseClaim(ResponseClaimState.CONFLICT)
            if self._idempotency.get(idempotency_key, owner) != owner:
                return AtomicResponseClaim(ResponseClaimState.CONFLICT)
            current = self._records.get(lifecycle_key)
            if current is None:
                self._records[lifecycle_key] = (response_request_id, idempotency_key, request_digest, None)
                self._requests[response_request_id] = owner
                self._idempotency[idempotency_key] = owner
                return AtomicResponseClaim(ResponseClaimState.NEW)
            if current[:3] != (response_request_id, idempotency_key, request_digest):
                return AtomicResponseClaim(ResponseClaimState.CONFLICT)
            if current[3] is None:
                return AtomicResponseClaim(ResponseClaimState.IN_PROGRESS)
            return AtomicResponseClaim(ResponseClaimState.REPLAY, current[3])

    def commit(self, *, lifecycle_key: str, response_request_id: str,
               idempotency_key: str, request_digest: str,
               result: SettledOutcomeResponseResult) -> None:
        with self._lock:
            expected = (response_request_id, idempotency_key, request_digest)
            current = self._records.get(lifecycle_key)
            if current is None or current[:3] != expected:
                raise ResponsePersistenceError("response claim is unavailable")
            if current[3] is not None and current[3] != result:
                raise ResponsePersistenceError("response authorization is immutable")
            self._records[lifecycle_key] = (*expected, result)

    def recover(self, lifecycle_key: str) -> AtomicResponseClaim:
        with self._lock:
            current = self._records.get(lifecycle_key)
            if current is None:
                return AtomicResponseClaim(ResponseClaimState.UNAVAILABLE)
            return AtomicResponseClaim(ResponseClaimState.REPLAY, current[3]) if current[3] else AtomicResponseClaim(ResponseClaimState.IN_PROGRESS)


def _evidence_document(value: ResponseAuthorizationEvidence) -> dict[str, Any]:
    document = asdict(value)
    for key in ("response_authorization_id", "authorization_digest", "signature"):
        document.pop(key)
    document["settlement_status"] = value.settlement_status.value
    document["response_outcome"] = value.response_outcome.value
    document["response_type"] = value.response_type.value
    document["decision_reason_code"] = value.decision_reason_code.value
    document["scope"] = list(value.scope); document["constraints"] = list(value.constraints)
    document["expires_at"] = _timestamp(value.expires_at); document["created_at"] = _timestamp(value.created_at)
    return document


def _result_document(value: SettledOutcomeResponseResult) -> dict[str, Any]:
    return {
        "response_request_id": value.response_request_id, "outcome": value.outcome.value,
        "reason_code": value.reason_code.value, "decided_at": _timestamp(value.decided_at),
        "evidence": ({**_evidence_document(value.evidence),
                      "response_authorization_id": value.evidence.response_authorization_id,
                      "authorization_digest": value.evidence.authorization_digest,
                      "signature": value.evidence.signature} if value.evidence else None),
        "committed": value.committed, "idempotent": value.idempotent,
    }


def _restore_result(document: Mapping[str, Any]) -> SettledOutcomeResponseResult:
    evidence_document = document["evidence"]
    evidence = None
    if evidence_document is not None:
        evidence = ResponseAuthorizationEvidence(**{
            **evidence_document,
            "settlement_status": SettlementStatus(evidence_document["settlement_status"]),
            "response_outcome": ResponseOutcome(evidence_document["response_outcome"]),
            "response_type": ResponseType(evidence_document["response_type"]),
            "decision_reason_code": ResponseReasonCode(evidence_document["decision_reason_code"]),
            "scope": tuple(evidence_document["scope"]), "constraints": tuple(evidence_document["constraints"]),
            "expires_at": _parse_time(evidence_document["expires_at"]),
            "created_at": _parse_time(evidence_document["created_at"]),
        })
    return SettledOutcomeResponseResult(
        document["response_request_id"], ResponseOutcome(document["outcome"]),
        ResponseReasonCode(document["reason_code"]), _parse_time(document["decided_at"]),
        evidence, document["committed"], document["idempotent"],
    )


class SqliteResponseAuthorizationRepository:
    """Durable atomic response authorization store with crash recovery."""

    def __init__(self, path: str | Path) -> None:
        self._path = str(path)
        connection = self._connect()
        try:
            connection.execute("""CREATE TABLE IF NOT EXISTS continued_operation_response (
                lifecycle_key TEXT PRIMARY KEY, response_request_id TEXT NOT NULL UNIQUE,
                idempotency_key TEXT NOT NULL UNIQUE, request_digest TEXT NOT NULL,
                result_json TEXT)""")
            connection.commit()
        finally:
            connection.close()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._path, timeout=30, isolation_level=None)
        connection.execute("PRAGMA journal_mode=WAL")
        return connection

    def claim(self, *, lifecycle_key: str, response_request_id: str,
              idempotency_key: str, request_digest: str) -> AtomicResponseClaim:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            by_lifecycle = connection.execute(
                "SELECT response_request_id,idempotency_key,request_digest,result_json FROM continued_operation_response WHERE lifecycle_key=?",
                (lifecycle_key,),).fetchone()
            by_request = connection.execute(
                "SELECT lifecycle_key,request_digest FROM continued_operation_response WHERE response_request_id=?",
                (response_request_id,),).fetchone()
            by_key = connection.execute(
                "SELECT lifecycle_key,request_digest FROM continued_operation_response WHERE idempotency_key=?",
                (idempotency_key,),).fetchone()
            owner = (lifecycle_key, request_digest)
            if ((by_request is not None and by_request != owner) or
                    (by_key is not None and by_key != owner)):
                connection.rollback(); return AtomicResponseClaim(ResponseClaimState.CONFLICT)
            if by_lifecycle is None:
                connection.execute("INSERT INTO continued_operation_response VALUES (?,?,?,?,NULL)",
                                   (lifecycle_key, response_request_id, idempotency_key, request_digest))
                connection.commit(); return AtomicResponseClaim(ResponseClaimState.NEW)
            connection.commit()
            if by_lifecycle[:3] != (response_request_id, idempotency_key, request_digest):
                return AtomicResponseClaim(ResponseClaimState.CONFLICT)
            if by_lifecycle[3] is None:
                return AtomicResponseClaim(ResponseClaimState.IN_PROGRESS)
            return AtomicResponseClaim(ResponseClaimState.REPLAY, _restore_result(json.loads(by_lifecycle[3])))
        except sqlite3.IntegrityError:
            try: connection.rollback()
            except sqlite3.Error: pass
            return AtomicResponseClaim(ResponseClaimState.CONFLICT)
        except sqlite3.Error as error:
            try: connection.rollback()
            except sqlite3.Error: pass
            raise ResponsePersistenceError("response claim failed") from error
        finally:
            connection.close()

    def commit(self, *, lifecycle_key: str, response_request_id: str,
               idempotency_key: str, request_digest: str,
               result: SettledOutcomeResponseResult) -> None:
        payload = _canonical(_result_document(result)).decode("utf-8")
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT response_request_id,idempotency_key,request_digest,result_json FROM continued_operation_response WHERE lifecycle_key=?",
                (lifecycle_key,),).fetchone()
            if row is None or row[:3] != (response_request_id, idempotency_key, request_digest):
                connection.rollback(); raise ResponsePersistenceError("response claim is unavailable")
            if row[3] is not None:
                connection.rollback()
                if row[3] != payload:
                    raise ResponsePersistenceError("response authorization is immutable")
                return
            connection.execute("UPDATE continued_operation_response SET result_json=? WHERE lifecycle_key=? AND result_json IS NULL",
                               (payload, lifecycle_key))
            connection.commit()
        except ResponsePersistenceError:
            raise
        except sqlite3.Error as error:
            try: connection.rollback()
            except sqlite3.Error: pass
            raise ResponseCommitStatusUnknown("response commit status is unknown") from error
        finally:
            connection.close()

    def recover(self, lifecycle_key: str) -> AtomicResponseClaim:
        connection = self._connect()
        try:
            row = connection.execute("SELECT result_json FROM continued_operation_response WHERE lifecycle_key=?", (lifecycle_key,)).fetchone()
            if row is None: return AtomicResponseClaim(ResponseClaimState.UNAVAILABLE)
            if row[0] is None: return AtomicResponseClaim(ResponseClaimState.IN_PROGRESS)
            return AtomicResponseClaim(ResponseClaimState.REPLAY, _restore_result(json.loads(row[0])))
        finally:
            connection.close()


def _trusted_now(clock: Callable[[], datetime]) -> datetime | None:
    try:
        value = clock()
        if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None or value.microsecond:
            return None
        return value.astimezone(timezone.utc)
    except Exception:
        return None


def _result(request: SettledOutcomeResponseRequest, outcome: ResponseOutcome,
            reason: ResponseReasonCode, now: datetime,
            evidence: ResponseAuthorizationEvidence | None = None) -> SettledOutcomeResponseResult:
    return SettledOutcomeResponseResult(request.response_request_id, outcome, reason, now,
                                        evidence, evidence is not None, False)


def _make_evidence(request: SettledOutcomeResponseRequest, source: AuthoritativeSettlementRecord,
                   policy: ResponsePolicy, manifest: ResponseManifest, outcome: ResponseOutcome,
                   reason: ResponseReasonCode, now: datetime,
                   signer: ResponseSigner) -> ResponseAuthorizationEvidence:
    settlement = source.evidence
    expiry = now + timedelta(seconds=min(policy.maximum_authorization_seconds, manifest.lifetime_seconds))
    incident_id = sha256(_canonical({"domain": _INCIDENT_DOMAIN, "settlement_id": settlement.settlement_id})).hexdigest()
    values = {
        "schema_version": CONTINUED_OPERATION_RESPONSE_EVIDENCE_VERSION,
        "response_request_id": request.response_request_id,
        "response_idempotency_key": request.response_idempotency_key,
        "settlement_id": settlement.settlement_id, "settlement_digest": settlement.evidence_digest,
        "verification_id": settlement.verification_id,
        "verification_evidence_digest": settlement.verification_evidence_digest,
        "execution_id": settlement.execution_id, "execution_evidence_digest": settlement.execution_evidence_digest,
        "enforcement_request_id": source.enforcement_request_id,
        "enforcement_evidence_digest": settlement.enforcement_evidence_digest,
        "authorization_id": source.authorization_id, "incident_id": incident_id,
        "deployment_id": settlement.deployment_id, "operation_id": settlement.operation_id,
        "settlement_status": settlement.settlement_status.value,
        "response_outcome": outcome.value, "response_type": manifest.response_type.value,
        "response_manifest_id": manifest.manifest_id, "response_manifest_version": manifest.version,
        "response_manifest_digest": response_manifest_digest(manifest),
        "remediation_capability": manifest.remediation_capability,
        "policy_id": policy.policy_id, "policy_version": policy.version,
        "policy_digest": response_policy_digest(policy), "decision_reason_code": reason.value,
        "scope": list(request.requested_scope), "constraints": list(manifest.constraints),
        "maximum_attempts": manifest.maximum_attempts, "expires_at": _timestamp(expiry),
        "created_at": _timestamp(now), "authorized_by": request.requester_id,
    }
    authorization_digest = sha256(_canonical({"domain": _EVIDENCE_DOMAIN, **values})).hexdigest()
    authorization_id = sha256(_canonical({"domain": _EVIDENCE_DOMAIN, **values,
                                          "authorization_digest": authorization_digest})).hexdigest()
    signature = signer.sign(bytes.fromhex(authorization_digest))
    return ResponseAuthorizationEvidence(
        response_authorization_id=authorization_id, response_request_id=request.response_request_id,
        response_idempotency_key=request.response_idempotency_key,
        settlement_id=settlement.settlement_id, settlement_digest=settlement.evidence_digest,
        verification_id=settlement.verification_id,
        verification_evidence_digest=settlement.verification_evidence_digest,
        execution_id=settlement.execution_id, execution_evidence_digest=settlement.execution_evidence_digest,
        enforcement_request_id=source.enforcement_request_id,
        enforcement_evidence_digest=settlement.enforcement_evidence_digest,
        authorization_id=source.authorization_id, incident_id=incident_id,
        deployment_id=settlement.deployment_id, operation_id=settlement.operation_id,
        settlement_status=settlement.settlement_status, response_outcome=outcome,
        response_type=manifest.response_type, response_manifest_id=manifest.manifest_id,
        response_manifest_version=manifest.version, response_manifest_digest=request.response_manifest_digest,
        remediation_capability=manifest.remediation_capability, policy_id=policy.policy_id,
        policy_version=policy.version, policy_digest=request.policy_digest,
        decision_reason_code=reason, scope=request.requested_scope, constraints=manifest.constraints,
        maximum_attempts=manifest.maximum_attempts, expires_at=expiry, created_at=now,
        authorized_by=request.requester_id, authorization_digest=authorization_digest,
        signature=signature,
    )


def verify_response_authorization(value: ResponseAuthorizationEvidence,
                                  signer: ResponseSigner, *, now: datetime | None = None) -> bool:
    if type(value) is not ResponseAuthorizationEvidence:
        return False
    try:
        document = _evidence_document(value)
        authorization_digest = sha256(_canonical({"domain": _EVIDENCE_DOMAIN, **document})).hexdigest()
        authorization_id = sha256(_canonical({"domain": _EVIDENCE_DOMAIN, **document,
                                              "authorization_digest": authorization_digest})).hexdigest()
        valid = (value.authorization_digest == authorization_digest and
                 value.response_authorization_id == authorization_id and
                 signer.verify(bytes.fromhex(authorization_digest), value.signature))
        if now is not None:
            valid = valid and _trusted_now(lambda: now) is not None and now.astimezone(timezone.utc) < value.expires_at
        return valid
    except Exception:
        return False


def authorize_settled_outcome_response(
    request: SettledOutcomeResponseRequest, *, settlement_repository: SettlementRecordRepository,
    policy_repository: ResponsePolicyRepository, manifest_repository: ResponseManifestRepository,
    authorization_repository: ResponseAuthorizationRepository, settlement_signer: SettlementSigner,
    response_signer: ResponseSigner, trusted_clock: Callable[[], datetime],
) -> SettledOutcomeResponseResult:
    """Authorize a response without executing, retrying, observing, or remediating."""
    if type(request) is not SettledOutcomeResponseRequest:
        raise ContinuedOperationResponseError("an exact response request is required.")
    now = _trusted_now(trusted_clock)
    if now is None:
        return _result(request, ResponseOutcome.DEFERRED, ResponseReasonCode.UNTRUSTED_TIME_SOURCE, request.requested_at)
    if request.requested_at > now:
        return _result(request, ResponseOutcome.REJECTED, ResponseReasonCode.SETTLEMENT_BINDING_MISMATCH, now)
    try: source = settlement_repository.get_committed(request.settlement_id)
    except Exception: source = None
    if source is None:
        return _result(request, ResponseOutcome.REJECTED, ResponseReasonCode.SETTLEMENT_NOT_FOUND, now)
    if (type(source) is not AuthoritativeSettlementRecord or not source.committed or
            source.evidence.settlement_id != request.settlement_id or
            source.evidence.evidence_digest != request.settlement_digest or
            not verify_settlement_evidence(source.evidence, settlement_signer)):
        return _result(request, ResponseOutcome.REJECTED, ResponseReasonCode.SETTLEMENT_EVIDENCE_INVALID, now)
    status = source.evidence.settlement_status
    if status is SettlementStatus.SETTLED_SUCCESS:
        return _result(request, ResponseOutcome.INELIGIBLE, ResponseReasonCode.SETTLEMENT_SUCCESS_INELIGIBLE, now)
    if status is SettlementStatus.REJECTED:
        return _result(request, ResponseOutcome.REJECTED, ResponseReasonCode.SETTLEMENT_REJECTED, now)
    try: policy = policy_repository.get(request.policy_id, request.policy_version)
    except Exception: policy = None
    if policy is None or type(policy) is not ResponsePolicy:
        return _result(request, ResponseOutcome.REJECTED, ResponseReasonCode.RESPONSE_POLICY_NOT_FOUND, now)
    if response_policy_digest(policy) != request.policy_digest:
        return _result(request, ResponseOutcome.REJECTED, ResponseReasonCode.RESPONSE_POLICY_INVALID, now)
    try: manifest = manifest_repository.get(request.response_manifest_id, request.response_manifest_version)
    except Exception: manifest = None
    if manifest is None or type(manifest) is not ResponseManifest:
        return _result(request, ResponseOutcome.REJECTED, ResponseReasonCode.RESPONSE_MANIFEST_NOT_FOUND, now)
    manifest_reference = f"{manifest.manifest_id}@{manifest.version}"
    if (response_manifest_digest(manifest) != request.response_manifest_digest or
            manifest_reference not in policy.approved_manifest_references):
        return _result(request, ResponseOutcome.REJECTED, ResponseReasonCode.RESPONSE_MANIFEST_INVALID, now)
    if request.requester_role not in policy.authorized_roles or request.requester_role not in manifest.required_roles:
        return _result(request, ResponseOutcome.REJECTED, ResponseReasonCode.REQUESTER_NOT_AUTHORIZED, now)
    if (not set(request.requested_scope).issubset(source.original_scope) or
            not set(request.requested_scope).issubset(policy.permitted_scopes) or
            not set(request.requested_scope).issubset(manifest.permitted_scopes)):
        return _result(request, ResponseOutcome.REJECTED, ResponseReasonCode.SCOPE_NOT_PERMITTED, now)
    allowed = policy.permitted_failure_types if status is SettlementStatus.SETTLED_FAILURE else policy.permitted_suspended_types
    if (manifest.response_type is not request.requested_response_type or
            status not in manifest.permitted_settlement_statuses or
            request.requested_response_type not in allowed or
            source.evidence.operation_id in manifest.prohibited_operations):
        outcome = (ResponseOutcome.MANUAL_REVIEW_REQUIRED if status is SettlementStatus.SUSPENDED
                   else ResponseOutcome.REJECTED)
        reason = (ResponseReasonCode.MANUAL_REVIEW_REQUIRED if status is SettlementStatus.SUSPENDED
                  else ResponseReasonCode.RESPONSE_NOT_PERMITTED)
        return _result(request, outcome, reason, now)
    outcome = (ResponseOutcome.MANUAL_REVIEW_REQUIRED
               if status is SettlementStatus.SUSPENDED and policy.require_manual_review_for_suspended
               else ResponseOutcome.AUTHORIZED)
    reason = (ResponseReasonCode.MANUAL_REVIEW_REQUIRED if outcome is ResponseOutcome.MANUAL_REVIEW_REQUIRED
              else ResponseReasonCode.RESPONSE_AUTHORIZED)
    if outcome is ResponseOutcome.MANUAL_REVIEW_REQUIRED and manifest.response_type not in {
        ResponseType.MANUAL_REVIEW, ResponseType.INVESTIGATION, ResponseType.REVERIFICATION,
    }:
        return _result(request, outcome, reason, now)
    request_digest = response_request_digest(request); lifecycle_key = response_lifecycle_key(request)
    try:
        claim = authorization_repository.claim(
            lifecycle_key=lifecycle_key, response_request_id=request.response_request_id,
            idempotency_key=request.response_idempotency_key, request_digest=request_digest)
    except Exception:
        return _result(request, ResponseOutcome.DEFERRED, ResponseReasonCode.RESPONSE_REPOSITORY_UNAVAILABLE, now)
    if claim.state is ResponseClaimState.REPLAY and claim.result is not None:
        if claim.result.evidence is not None and now >= claim.result.evidence.expires_at:
            return _result(request, ResponseOutcome.DEFERRED, ResponseReasonCode.RESPONSE_AUTHORIZATION_EXPIRED, now)
        return claim.result
    if claim.state is ResponseClaimState.CONFLICT:
        return _result(request, ResponseOutcome.CONFLICT, ResponseReasonCode.RESPONSE_CONFLICT, now)
    if claim.state is ResponseClaimState.IN_PROGRESS:
        return _result(request, ResponseOutcome.DEFERRED, ResponseReasonCode.RESPONSE_IN_PROGRESS, now)
    if claim.state is not ResponseClaimState.NEW:
        return _result(request, ResponseOutcome.DEFERRED, ResponseReasonCode.RESPONSE_REPOSITORY_UNAVAILABLE, now)
    try: evidence = _make_evidence(request, source, policy, manifest, outcome, reason, now, response_signer)
    except Exception:
        return _result(request, ResponseOutcome.REJECTED, ResponseReasonCode.RESPONSE_MANIFEST_INVALID, now)
    result = _result(request, outcome, reason, now, evidence)
    try:
        authorization_repository.commit(
            lifecycle_key=lifecycle_key, response_request_id=request.response_request_id,
            idempotency_key=request.response_idempotency_key, request_digest=request_digest, result=result)
        return result
    except ResponseCommitStatusUnknown:
        return _result(request, ResponseOutcome.DEFERRED, ResponseReasonCode.RESPONSE_COMMIT_INDETERMINATE, now)
    except Exception:
        return _result(request, ResponseOutcome.DEFERRED, ResponseReasonCode.RESPONSE_REPOSITORY_UNAVAILABLE, now)


def create_atl_a20_handoff(value: ResponseAuthorizationEvidence, *, signer: ResponseSigner,
                           trusted_clock: Callable[[], datetime]) -> AtlA20ResponseHandoff:
    now = _trusted_now(trusted_clock)
    if (now is None or not verify_response_authorization(value, signer, now=now) or
            value.response_outcome is not ResponseOutcome.AUTHORIZED or
            value.response_type not in {ResponseType.REMEDIATION, ResponseType.CONTAINMENT,
                                        ResponseType.COMPENSATION, ResponseType.ROLLBACK}):
        raise ContinuedOperationResponseError("response authorization is not consumable.")
    return AtlA20ResponseHandoff(
        value.response_authorization_id, value.incident_id, value.deployment_id,
        value.enforcement_evidence_digest, value.remediation_capability,
        value.response_manifest_digest, value.scope, value.constraints, value.maximum_attempts,
        value.expires_at, value.authorization_digest, value.signature,
    )


def verify_atl_a20_handoff(value: AtlA20ResponseHandoff,
                           authorization: ResponseAuthorizationEvidence, *,
                           signer: ResponseSigner,
                           trusted_clock: Callable[[], datetime]) -> bool:
    """Verify a handoff against signed evidence instead of caller-supplied claims."""
    if type(value) is not AtlA20ResponseHandoff:
        return False
    try:
        return value == create_atl_a20_handoff(
            authorization, signer=signer, trusted_clock=trusted_clock,
        )
    except Exception:
        return False


def atl_a20_remediation_request(value: AtlA20ResponseHandoff, *,
                                authorization: ResponseAuthorizationEvidence,
                                signer: ResponseSigner,
                                trusted_clock: Callable[[], datetime],
                                requested_at: datetime,
                                tenant_id: str = "trusted-deployment",
                                environment: str = "protected") -> RemediationRequest:
    """Translate a validated A.30 handoff into A.20's existing request contract."""
    if not verify_atl_a20_handoff(
        value, authorization, signer=signer, trusted_clock=trusted_clock,
    ):
        raise ContinuedOperationResponseError("ATL-A.20 handoff is invalid.")
    return RemediationRequest(
        value.incident_id, value.deployment_id, value.artifact_digest, tenant_id, environment,
        value.action, value.action_fingerprint, requested_at,
    )


def public_settled_outcome_response(request: SettledOutcomeResponseRequest,
                                    result: SettledOutcomeResponseResult) -> PublicSettledOutcomeResponseV1:
    if (type(request) is not SettledOutcomeResponseRequest or
            type(result) is not SettledOutcomeResponseResult or
            request.response_request_id != result.response_request_id):
        raise ContinuedOperationResponseError("an exact response result is required.")
    evidence = result.evidence
    return PublicSettledOutcomeResponseV1(
        response_authorization_id=evidence.response_authorization_id if evidence else None,
        response_request_id=result.response_request_id, settlement_id=request.settlement_id,
        incident_id=evidence.incident_id if evidence else None, outcome=result.outcome,
        response_type=evidence.response_type if evidence else None, reason_code=result.reason_code,
        expires_at=evidence.expires_at if evidence else None,
        committed=result.committed, idempotent=result.idempotent,
    )


__all__ = [
    "HmacResponseSigner", "InMemoryResponseAuthorizationRepository",
    "InMemoryResponseManifestRepository", "InMemoryResponsePolicyRepository",
    "InMemorySettlementRecordRepository", "ResponseCommitStatusUnknown",
    "ResponsePersistenceError", "SqliteResponseAuthorizationRepository",
    "atl_a20_remediation_request", "authorize_settled_outcome_response",
    "create_atl_a20_handoff", "public_settled_outcome_response",
    "response_lifecycle_key", "response_manifest_digest", "response_policy_digest",
    "response_request_digest", "response_request_document",
    "translate_untrusted_response_request", "verify_response_authorization",
    "verify_atl_a20_handoff",
]
