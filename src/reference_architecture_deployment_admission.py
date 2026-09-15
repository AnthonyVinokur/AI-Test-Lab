from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from threading import Lock
from typing import Any, Callable, Mapping

from src.reference_architecture_deployment_admission_contract import (
    ADMISSION_CONTRACT_VERSION, AdmissionDecision, AdmissionEnforcementPolicy, AdmissionResult,
    AuthorizationUsage, AuthorizationVerifierPort, CanonicalDeploymentRequest,
    DeploymentAdmissionReceipt, DeploymentAdmissionRequest, DeploymentExecutorPort,
    EnforcementPolicyReference, EnforcementStateStore, PublicAdmissionResult,
    VerifiedAuthorizationReference,
)
from src.reference_architecture_deployment_authorization import verify_deployment_authorization
from src.reference_architecture_deployment_authorization_contract import (
    AuthorizationLifecycleRecord, DeploymentAuthorizationAttestation, DeploymentContext,
)


class AdmissionDocumentError(ValueError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def _timestamp(value: datetime) -> str:
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_time(value: object) -> datetime:
    if type(value) is not str or len(value) != 20 or not value.endswith("Z"):
        raise ValueError
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def enforcement_policy_document(policy: AdmissionEnforcementPolicy) -> dict[str, Any]:
    return {
        "allowed_environment_classifications": sorted(policy.allowed_environment_classifications),
        "allowed_operations": sorted(policy.allowed_operations),
        "maximum_clock_skew_seconds": policy.maximum_clock_skew_seconds,
        "minimum_remaining_validity_seconds": policy.minimum_remaining_validity_seconds,
        "policy_id": policy.policy_id, "usage": policy.usage.value, "version": policy.version,
    }


def enforcement_policy_reference(policy: AdmissionEnforcementPolicy) -> EnforcementPolicyReference:
    return EnforcementPolicyReference(policy.policy_id, policy.version,
                                      sha256(_canonical(enforcement_policy_document(policy))).hexdigest())


def admission_request_document(request: DeploymentAdmissionRequest) -> dict[str, Any]:
    return {
        "admission_request_id": request.admission_request_id,
        "artifact_digest": request.artifact_digest, "artifact_id": request.artifact_id,
        "authorization_id": request.authorization_id, "configuration_digest": request.configuration_digest,
        "contract_version": request.contract_version, "correlation_id": request.correlation_id,
        "deployment_attempt_id": request.deployment_attempt_id,
        "deployment_scope": request.deployment_scope,
        "enforcement_policy": asdict(request.enforcement_policy),
        "environment_classification": request.environment_classification,
        "evaluation_time": _timestamp(request.evaluation_time), "idempotency_key": request.idempotency_key,
        "operation": request.operation, "release_id": request.release_id,
        "requested_at": _timestamp(request.requested_at),
        "requested_conditions": list(request.requested_conditions),
        "target_environment": request.target_environment, "tenant_id": request.tenant_id,
    }


def translate_untrusted_admission_request(value: bytes | str | Mapping[str, Any]) -> DeploymentAdmissionRequest:
    try:
        raw = value.encode() if isinstance(value, str) else value if isinstance(value, bytes) else None
        document = json.loads(raw) if raw is not None else dict(value)
        expected = {
            "admission_request_id", "deployment_attempt_id", "authorization_id", "artifact_id",
            "artifact_digest", "release_id", "tenant_id", "target_environment",
            "environment_classification", "deployment_scope", "operation", "configuration_digest",
            "requested_conditions", "requested_at", "evaluation_time", "correlation_id",
            "enforcement_policy", "idempotency_key", "contract_version",
        }
        policy_fields = {"policy_id", "version", "digest"}
        if not isinstance(document, dict) or set(document) != expected:
            raise ValueError
        if not isinstance(document["enforcement_policy"], dict) or set(document["enforcement_policy"]) != policy_fields:
            raise ValueError
        if not isinstance(document["requested_conditions"], list):
            raise ValueError
        request = DeploymentAdmissionRequest(**{
            **document,
            "requested_conditions": tuple(document["requested_conditions"]),
            "requested_at": _parse_time(document["requested_at"]),
            "evaluation_time": _parse_time(document["evaluation_time"]),
            "enforcement_policy": EnforcementPolicyReference(**document["enforcement_policy"]),
        })
        if raw is not None and raw != _canonical(document):
            raise ValueError
        return request
    except Exception as error:
        raise AdmissionDocumentError("Deployment admission request is invalid.") from error


def canonicalize_deployment_request(request: DeploymentAdmissionRequest) -> CanonicalDeploymentRequest:
    document = admission_request_document(request)
    canonical_bytes = _canonical(document)
    return CanonicalDeploymentRequest(sha256(canonical_bytes).hexdigest(), canonical_bytes)


class SafeAuthorizationVerifierAdapter:
    """Narrow ATL-A.14 port; only its approved safe verifier establishes trust."""

    def __init__(self, signature_verifier: Callable[[str, bytes, bytes], bool]) -> None:
        self._signature_verifier = signature_verifier

    def verify(self, authorization: DeploymentAuthorizationAttestation | None, *,
               history: tuple[AuthorizationLifecycleRecord, ...], evaluation_time: datetime,
               request: DeploymentAdmissionRequest) -> tuple[VerifiedAuthorizationReference | None, str]:
        context = DeploymentContext(request.artifact_id, request.artifact_digest, request.tenant_id,
                                    request.target_environment, request.release_id,
                                    request.deployment_scope, request.requested_conditions)
        result = verify_deployment_authorization(
            authorization, history=history, observed_at=evaluation_time,
            signature_verifier=self._signature_verifier, context=context)
        if not result.valid or not result.active or not result.applicable or authorization is None:
            return None, result.reason_code
        return VerifiedAuthorizationReference(
            authorization.authorization_id, authorization.artifact_id, authorization.artifact_digest,
            authorization.release_id, authorization.tenant_id, authorization.environment,
            authorization.scope, authorization.conditions, authorization.authorization_policy_id,
            authorization.valid_from, authorization.expires_at), result.reason_code


def _blocked(request: DeploymentAdmissionRequest, policy_ref: EnforcementPolicyReference,
             decision: AdmissionDecision, reason: str, digest: str | None = None) -> AdmissionResult:
    return AdmissionResult(decision, (reason,), request.authorization_id,
                           request.deployment_attempt_id, digest, policy_ref,
                           request.evaluation_time)


def _binding_reason(request: DeploymentAdmissionRequest,
                    authorization: VerifiedAuthorizationReference) -> str | None:
    checks = (
        (authorization.authorization_id == request.authorization_id, "authorization_invalid"),
        (authorization.artifact_id == request.artifact_id, "artifact_mismatch"),
        (authorization.artifact_digest == request.artifact_digest, "digest_mismatch"),
        (authorization.tenant_id == request.tenant_id, "tenant_mismatch"),
        (authorization.environment == request.target_environment, "environment_mismatch"),
        (authorization.release_id == request.release_id, "release_mismatch"),
        (authorization.scope == request.deployment_scope, "scope_mismatch"),
        (authorization.conditions == request.requested_conditions, "conditions_not_preserved"),
    )
    return next((reason for valid, reason in checks if not valid), None)


def _receipt(request: DeploymentAdmissionRequest, digest: str,
             policy_ref: EnforcementPolicyReference, consumption_reference: str) -> DeploymentAdmissionReceipt:
    values = {
        "authorization_id": request.authorization_id, "consumption_reference": consumption_reference,
        "correlation_id": request.correlation_id, "deployment_attempt_id": request.deployment_attempt_id,
        "enforcement_policy_digest": policy_ref.digest, "enforcement_policy_id": policy_ref.policy_id,
        "enforcement_policy_version": policy_ref.version, "evaluated_at": _timestamp(request.evaluation_time),
        "outcome": AdmissionDecision.PERMITTED.value, "request_binding_digest": digest,
    }
    integrity = sha256(_canonical(values)).hexdigest()
    receipt_id = sha256(_canonical({**values, "integrity_digest": integrity})).hexdigest()
    return DeploymentAdmissionReceipt(receipt_id, request.deployment_attempt_id, request.authorization_id,
                                      digest, AdmissionDecision.PERMITTED, policy_ref.policy_id,
                                      policy_ref.version, policy_ref.digest, request.evaluation_time,
                                      consumption_reference, request.correlation_id, integrity)


class InMemoryEnforcementStateStore:
    """Thread-safe reference adapter. Durable stores must provide the same atomic semantics."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._by_authorization: dict[str, DeploymentAdmissionReceipt] = {}
        self._by_idempotency: dict[tuple[str, str], tuple[str, DeploymentAdmissionReceipt]] = {}

    def consume(self, *, authorization_id: str, attempt_id: str, idempotency_key: str,
                request_digest: str, single_use: bool,
                receipt_factory: Callable[[str], DeploymentAdmissionReceipt],
                ) -> tuple[DeploymentAdmissionReceipt | None, bool, str | None]:
        with self._lock:
            identity = (authorization_id, idempotency_key)
            prior = self._by_idempotency.get(identity)
            if prior is not None:
                return (prior[1], True, None) if prior[0] == request_digest else (None, False, "authorization_replayed")
            if single_use and authorization_id in self._by_authorization:
                return None, False, "authorization_replayed"
            reference = sha256(_canonical({"authorization_id": authorization_id,
                                           "attempt_id": attempt_id,
                                           "idempotency_key": idempotency_key})).hexdigest()
            receipt = receipt_factory(reference)
            self._by_idempotency[identity] = (request_digest, receipt)
            if single_use:
                self._by_authorization[authorization_id] = receipt
            return receipt, False, None


def admit_deployment(request: DeploymentAdmissionRequest, *,
                     authorization: DeploymentAuthorizationAttestation | None,
                     authorization_history: tuple[AuthorizationLifecycleRecord, ...],
                     verifier: AuthorizationVerifierPort, policy: AdmissionEnforcementPolicy,
                     state_store: EnforcementStateStore) -> AdmissionResult:
    canonical = canonicalize_deployment_request(request)
    policy_ref = enforcement_policy_reference(policy)
    if request.enforcement_policy != policy_ref:
        return _blocked(request, policy_ref, AdmissionDecision.INVALID, "enforcement_indeterminate", canonical.digest)
    if request.operation not in policy.allowed_operations:
        return _blocked(request, policy_ref, AdmissionDecision.BLOCKED, "operation_not_authorized", canonical.digest)
    if request.environment_classification not in policy.allowed_environment_classifications:
        return _blocked(request, policy_ref, AdmissionDecision.BLOCKED, "environment_mismatch", canonical.digest)
    if abs((request.evaluation_time - request.requested_at).total_seconds()) > policy.maximum_clock_skew_seconds:
        return _blocked(request, policy_ref, AdmissionDecision.INVALID, "authorization_invalid", canonical.digest)
    try:
        trusted, reason = verifier.verify(authorization, history=authorization_history,
                                          evaluation_time=request.evaluation_time, request=request)
    except Exception:
        return _blocked(request, policy_ref, AdmissionDecision.INDETERMINATE,
                        "verifier_unavailable", canonical.digest)
    if trusted is None:
        normalized = reason if reason in {
            "authorization_missing", "authorization_invalid", "authorization_expired",
            "authorization_revoked", "authorization_superseded",
        } else "authorization_not_active" if reason == "authorization_not_yet_active" else "authorization_invalid"
        decision = AdmissionDecision.INDETERMINATE if reason == "authorization_missing" else AdmissionDecision.INVALID
        return _blocked(request, policy_ref, decision, normalized, canonical.digest)
    mismatch = _binding_reason(request, trusted)
    if mismatch:
        return _blocked(request, policy_ref, AdmissionDecision.BLOCKED, mismatch, canonical.digest)
    if trusted.authorization_policy_id == "" or trusted.expires_at - request.evaluation_time < timedelta(
            seconds=policy.minimum_remaining_validity_seconds):
        return _blocked(request, policy_ref, AdmissionDecision.BLOCKED, "authorization_expired", canonical.digest)
    try:
        receipt, replay, failure = state_store.consume(
            authorization_id=trusted.authorization_id, attempt_id=request.deployment_attempt_id,
            idempotency_key=request.idempotency_key, request_digest=canonical.digest,
            single_use=policy.usage is AuthorizationUsage.SINGLE_USE,
            receipt_factory=lambda reference: _receipt(request, canonical.digest, policy_ref, reference))
    except Exception:
        return _blocked(request, policy_ref, AdmissionDecision.INDETERMINATE,
                        "lifecycle_state_unavailable", canonical.digest)
    if failure or receipt is None:
        return _blocked(request, policy_ref, AdmissionDecision.BLOCKED,
                        failure or "enforcement_indeterminate", canonical.digest)
    return AdmissionResult(AdmissionDecision.PERMITTED, ("deployment_permitted",), trusted.authorization_id,
                           request.deployment_attempt_id, canonical.digest, policy_ref,
                           request.evaluation_time, receipt, replay)


class DeploymentAdmissionGateway:
    def __init__(self, verifier: AuthorizationVerifierPort, policy: AdmissionEnforcementPolicy,
                 state_store: EnforcementStateStore, executor: DeploymentExecutorPort) -> None:
        self._verifier, self._policy = verifier, policy
        self._state_store, self._executor = state_store, executor

    def admit(self, request: DeploymentAdmissionRequest, *,
              authorization: DeploymentAuthorizationAttestation | None,
              authorization_history: tuple[AuthorizationLifecycleRecord, ...] = ()) -> AdmissionResult:
        result = admit_deployment(request, authorization=authorization,
                                  authorization_history=authorization_history, verifier=self._verifier,
                                  policy=self._policy, state_store=self._state_store)
        if result.permitted and not result.idempotent_replay:
            try:
                self._executor.execute(request, result.receipt)  # type: ignore[arg-type]
            except Exception:
                return _blocked(request, result.enforcement_policy, AdmissionDecision.INDETERMINATE,
                                "enforcement_indeterminate", result.request_binding_digest)
        return result


def public_admission_result(request: DeploymentAdmissionRequest,
                            result: AdmissionResult) -> PublicAdmissionResult:
    return PublicAdmissionResult(
        request.admission_request_id, result.deployment_attempt_id, result.authorization_id,
        result.decision, result.permitted, result.reason_codes, result.evaluated_at,
        result.receipt.receipt_id if result.receipt else None, result.request_binding_digest)
