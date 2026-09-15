from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from threading import Lock
from typing import Any, Mapping

from src.reference_architecture_deployment_admission_contract import DeploymentAdmissionReceipt, DeploymentAdmissionRequest
from src.reference_architecture_deployment_execution_contract import (
    ATTESTATION_CONTRACT_VERSION, EXECUTION_CONTRACT_VERSION, AdmissionReceiptVerifierPort,
    DeploymentAdapterPort, DeploymentExecutionAttestation, DeploymentExecutionRequest,
    DeploymentExecutionResult, ExecutionClaimState, ExecutionCommand, ExecutionOutcome,
    ExecutionPolicy, ExecutionPolicyReference, ExecutionStateStore, ProviderExecutionResult,
    PublicDeploymentExecutionResult, ReceiptVerification, VerifiedAdmissionReference,
)


MAX_EXECUTION_DOCUMENT_BYTES = 32_768


class ExecutionDocumentError(ValueError): pass


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def _time(value: datetime) -> str: return value.strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_time(value: object) -> datetime:
    if type(value) is not str or len(value) != 20 or not value.endswith("Z"): raise ValueError
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def execution_policy_document(policy: ExecutionPolicy) -> dict[str, Any]:
    return {"adapter_contract_versions": sorted(policy.adapter_contract_versions),
        "dry_run_required": policy.dry_run_required,
        "environment_classifications": sorted(policy.environment_classifications),
        "maximum_attempts": policy.maximum_attempts,
        "minimum_receipt_lifetime_seconds": policy.minimum_receipt_lifetime_seconds,
        "permitted_adapters": sorted(policy.permitted_adapters),
        "permitted_operations": sorted(policy.permitted_operations),
        "policy_id": policy.policy_id, "reconcile_uncertain_outcomes": policy.reconcile_uncertain_outcomes,
        "required_capabilities": sorted(policy.required_capabilities),
        "retained_provider_fields": sorted(policy.retained_provider_fields),
        "retry_eligible": policy.retry_eligible, "timeout_seconds": policy.timeout_seconds,
        "version": policy.version}


def execution_policy_reference(policy: ExecutionPolicy) -> ExecutionPolicyReference:
    return ExecutionPolicyReference(policy.policy_id, policy.version,
                                    sha256(_canonical(execution_policy_document(policy))).hexdigest())


def execution_request_document(request: DeploymentExecutionRequest) -> dict[str, Any]:
    return {"adapter_contract_version": request.adapter_contract_version,
        "admission_receipt_id": request.admission_receipt_id,
        "artifact_digest": request.artifact_digest, "artifact_id": request.artifact_id,
        "authorization_id": request.authorization_id, "configuration_digest": request.configuration_digest,
        "contract_version": request.contract_version, "deployment_request_digest": request.deployment_request_digest,
        "deployment_scope": request.deployment_scope, "dry_run": request.dry_run,
        "environment_classification": request.environment_classification,
        "evaluation_time": _time(request.evaluation_time), "execution_attempt_id": request.execution_attempt_id,
        "execution_policy": asdict(request.execution_policy), "idempotency_key": request.idempotency_key,
        "operation": request.operation, "release_id": request.release_id,
        "requested_adapter": request.requested_adapter, "required_conditions": list(request.required_conditions),
        "target_environment": request.target_environment, "tenant_id": request.tenant_id,
        "trace_reference": request.trace_reference}


def _no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result: raise ValueError
        result[key] = value
    return result


def translate_untrusted_execution_request(value: bytes | str | Mapping[str, Any]) -> DeploymentExecutionRequest:
    try:
        raw = value.encode("utf-8") if isinstance(value, str) else value if isinstance(value, bytes) else None
        if raw is not None:
            if len(raw) > MAX_EXECUTION_DOCUMENT_BYTES: raise ValueError
            document = json.loads(raw, object_pairs_hook=_no_duplicates,
                                  parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
        else:
            document = dict(value)
            if len(_canonical(document)) > MAX_EXECUTION_DOCUMENT_BYTES: raise ValueError
        forbidden = {"trusted", "verified", "admitted", "authorized", "skip_verification",
                     "force_execute", "provider_success", "execution_confirmed"}
        required = {"adapter_contract_version", "admission_receipt_id", "artifact_digest", "artifact_id",
            "authorization_id", "configuration_digest", "contract_version", "deployment_request_digest",
            "deployment_scope", "dry_run", "environment_classification", "evaluation_time",
            "execution_attempt_id", "execution_policy", "idempotency_key", "operation", "release_id",
            "requested_adapter", "required_conditions", "target_environment", "tenant_id", "trace_reference"}
        if not isinstance(document, dict) or set(document) != required or set(document) & forbidden: raise ValueError
        policy = document["execution_policy"]
        if not isinstance(policy, dict) or set(policy) != {"policy_id", "version", "digest"}: raise ValueError
        if not isinstance(document["required_conditions"], list): raise ValueError
        request = DeploymentExecutionRequest(**{**document,
            "evaluation_time": _parse_time(document["evaluation_time"]),
            "required_conditions": tuple(document["required_conditions"]),
            "execution_policy": ExecutionPolicyReference(**policy)})
        if raw is not None and raw != _canonical(document): raise ValueError
        return request
    except Exception as error:
        raise ExecutionDocumentError("Deployment execution request is invalid.") from error


class SafeAdmissionReceiptVerifierAdapter:
    """Narrow ATL-A.15 boundary. The injected approved verifier alone establishes trust."""
    def __init__(self, verifier: ReceiptVerification) -> None: self._verifier = verifier
    def verify(self, receipt: DeploymentAdmissionReceipt | None,
               request: DeploymentExecutionRequest) -> VerifiedAdmissionReference | None:
        if receipt is None or receipt.outcome.value != "permitted" or receipt.receipt_id != request.admission_receipt_id:
            return None
        return self._verifier(receipt, request)


def _command_document(request: DeploymentExecutionRequest, admission: VerifiedAdmissionReference) -> dict[str, Any]:
    return {"adapter_contract_version": request.adapter_contract_version,
        "adapter_identity": request.requested_adapter, "admission_receipt_id": admission.receipt_id,
        "artifact_digest": request.artifact_digest, "artifact_id": request.artifact_id,
        "authorization_id": request.authorization_id, "configuration_digest": request.configuration_digest,
        "deployment_request_digest": request.deployment_request_digest,
        "deployment_scope": request.deployment_scope, "dry_run": request.dry_run,
        "environment": request.target_environment, "execution_attempt_id": request.execution_attempt_id,
        "execution_policy": asdict(request.execution_policy), "idempotency_key": request.idempotency_key,
        "operation": request.operation, "release_id": request.release_id,
        "required_conditions": list(request.required_conditions), "tenant_id": request.tenant_id,
        "trace_reference": request.trace_reference}


def canonicalize_execution_command(request: DeploymentExecutionRequest,
                                   admission: VerifiedAdmissionReference) -> ExecutionCommand:
    value = _canonical(_command_document(request, admission))
    return ExecutionCommand(request, admission, request.execution_policy, sha256(value).hexdigest())


def _binding_reason(request: DeploymentExecutionRequest, admission: VerifiedAdmissionReference) -> str | None:
    checks = ((admission.outcome == "permitted", "admission_not_permitted"),
        (admission.receipt_id == request.admission_receipt_id, "receipt_mismatch"),
        (admission.deployment_request_digest == request.deployment_request_digest, "request_digest_mismatch"),
        (admission.authorization_id == request.authorization_id, "authorization_mismatch"),
        (admission.artifact_id == request.artifact_id, "artifact_mismatch"),
        (admission.artifact_digest == request.artifact_digest, "artifact_digest_mismatch"),
        (admission.tenant_id == request.tenant_id, "tenant_mismatch"),
        (admission.environment == request.target_environment, "environment_mismatch"),
        (admission.environment_classification == request.environment_classification, "environment_classification_mismatch"),
        (admission.release_id == request.release_id, "release_mismatch"),
        (admission.operation == request.operation, "operation_mismatch"),
        (admission.scope == request.deployment_scope, "scope_mismatch"),
        (admission.configuration_digest == request.configuration_digest, "configuration_mismatch"),
        (admission.conditions == request.required_conditions, "conditions_mismatch"),
        (admission.admission_contract_version == "1.0", "admission_version_unsupported"),
        (admission.admitted_at <= request.evaluation_time < admission.valid_until, "admission_expired"))
    return next((reason for valid, reason in checks if not valid), None)


class InMemoryExecutionStateStore:
    def __init__(self) -> None:
        self._lock = Lock(); self._by_key: dict[tuple[str, str], tuple[str, DeploymentExecutionResult | None]] = {}
        self._states: dict[str, ExecutionClaimState] = {}; self._by_receipt: dict[str, str] = {}

    def claim(self, *, receipt_id: str, command_digest: str, idempotency_key: str,
              attempt_id: str) -> tuple[str, DeploymentExecutionResult | None]:
        with self._lock:
            key = (receipt_id, idempotency_key); prior = self._by_key.get(key)
            if prior:
                if prior[0] != command_digest: return "conflict", None
                return ("replay", prior[1]) if prior[1] is not None else ("busy", None)
            receipt_command = self._by_receipt.get(receipt_id)
            if receipt_command is not None:
                return ("busy", None) if receipt_command == command_digest else ("conflict", None)
            if command_digest in self._states: return "busy", None
            self._by_key[key] = (command_digest, None); self._by_receipt[receipt_id] = command_digest
            self._states[command_digest] = ExecutionClaimState.CLAIMED
            return "new", None

    def mark_executing(self, *, command_digest: str) -> str:
        with self._lock:
            if self._states.get(command_digest) is not ExecutionClaimState.CLAIMED: raise ValueError("invalid state")
            self._states[command_digest] = ExecutionClaimState.EXECUTING
            return sha256(_canonical({"command_digest": command_digest, "state": "executing"})).hexdigest()

    def finalize(self, *, command_digest: str, result: DeploymentExecutionResult) -> None:
        with self._lock:
            state = ExecutionClaimState.COMPLETED if result.outcome is ExecutionOutcome.SUCCEEDED else (
                ExecutionClaimState.OUTCOME_UNKNOWN if result.outcome is ExecutionOutcome.OUTCOME_UNKNOWN else ExecutionClaimState.FAILED)
            self._states[command_digest] = state
            for key, (stored, _) in tuple(self._by_key.items()):
                if stored == command_digest: self._by_key[key] = (stored, result)


def _attestation(command: ExecutionCommand, provider: ProviderExecutionResult,
                 previous_state: str) -> DeploymentExecutionAttestation:
    req = command.request
    values = {"adapter_identity": req.requested_adapter, "adapter_version": req.adapter_contract_version,
        "admission_receipt_id": req.admission_receipt_id, "artifact_digest": req.artifact_digest,
        "authorization_id": req.authorization_id, "completed_at": _time(provider.completed_at) if provider.completed_at else None,
        "contract_version": ATTESTATION_CONTRACT_VERSION, "environment": req.target_environment,
        "execution_attempt_id": req.execution_attempt_id, "execution_command_digest": command.execution_command_digest,
        "execution_policy": asdict(req.execution_policy), "operation": req.operation,
        "outcome": provider.outcome.value, "previous_state_reference": previous_state,
        "provider_operation_reference": provider.provider_operation_reference,
        "provider_response_digest": provider.provider_response_digest, "reason_code": provider.reason_code,
        "release_id": req.release_id, "started_at": _time(provider.started_at),
        "tenant_id": req.tenant_id, "trace_reference": req.trace_reference}
    attestation_digest = sha256(_canonical(values)).hexdigest()
    attestation_id = sha256(_canonical({**values, "attestation_digest": attestation_digest})).hexdigest()
    return DeploymentExecutionAttestation(attestation_id=attestation_id, attestation_digest=attestation_digest,
        execution_policy=req.execution_policy, **{k: v for k, v in values.items() if k not in {"contract_version", "execution_policy",
        "started_at", "completed_at", "outcome"}}, outcome=provider.outcome, started_at=provider.started_at,
        completed_at=provider.completed_at)


def verify_execution_attestation(attestation: DeploymentExecutionAttestation) -> bool:
    values = {"adapter_identity": attestation.adapter_identity, "adapter_version": attestation.adapter_version,
        "admission_receipt_id": attestation.admission_receipt_id, "artifact_digest": attestation.artifact_digest,
        "authorization_id": attestation.authorization_id,
        "completed_at": _time(attestation.completed_at) if attestation.completed_at else None,
        "contract_version": attestation.contract_version, "environment": attestation.environment,
        "execution_attempt_id": attestation.execution_attempt_id,
        "execution_command_digest": attestation.execution_command_digest,
        "execution_policy": asdict(attestation.execution_policy), "operation": attestation.operation,
        "outcome": attestation.outcome.value, "previous_state_reference": attestation.previous_state_reference,
        "provider_operation_reference": attestation.provider_operation_reference,
        "provider_response_digest": attestation.provider_response_digest, "reason_code": attestation.reason_code,
        "release_id": attestation.release_id, "started_at": _time(attestation.started_at),
        "tenant_id": attestation.tenant_id, "trace_reference": attestation.trace_reference}
    expected_digest = sha256(_canonical(values)).hexdigest()
    expected_id = sha256(_canonical({**values, "attestation_digest": expected_digest})).hexdigest()
    return expected_digest == attestation.attestation_digest and expected_id == attestation.attestation_id


def execute_deployment(request: DeploymentExecutionRequest, *, receipt: DeploymentAdmissionReceipt | None,
                       verifier: AdmissionReceiptVerifierPort, policy: ExecutionPolicy,
                       adapters: Mapping[str, DeploymentAdapterPort], state_store: ExecutionStateStore) -> DeploymentExecutionResult:
    def stop(outcome: ExecutionOutcome, reason: str, command_digest: str | None = None) -> DeploymentExecutionResult:
        return DeploymentExecutionResult(outcome, reason, request.execution_attempt_id,
                                         command_digest, request.evaluation_time)
    try: admission = verifier.verify(receipt, request)
    except Exception: return stop(ExecutionOutcome.INDETERMINATE, "admission_verifier_unavailable")
    if admission is None: return stop(ExecutionOutcome.INVALID, "admission_invalid")
    command = canonicalize_execution_command(request, admission)
    mismatch = _binding_reason(request, admission)
    if mismatch: return stop(ExecutionOutcome.BLOCKED, mismatch, command.execution_command_digest)
    policy_ref = execution_policy_reference(policy)
    if request.execution_policy != policy_ref: return stop(ExecutionOutcome.INVALID, "execution_policy_mismatch", command.execution_command_digest)
    if request.requested_adapter not in policy.permitted_adapters: return stop(ExecutionOutcome.BLOCKED, "adapter_not_permitted", command.execution_command_digest)
    if request.operation not in policy.permitted_operations: return stop(ExecutionOutcome.BLOCKED, "operation_not_permitted", command.execution_command_digest)
    if request.environment_classification not in policy.environment_classifications: return stop(ExecutionOutcome.BLOCKED, "environment_not_permitted", command.execution_command_digest)
    if admission.valid_until - request.evaluation_time < timedelta(seconds=policy.minimum_receipt_lifetime_seconds):
        return stop(ExecutionOutcome.BLOCKED, "admission_expired", command.execution_command_digest)
    if policy.dry_run_required and not request.dry_run: return stop(ExecutionOutcome.BLOCKED, "dry_run_required", command.execution_command_digest)
    adapter = adapters.get(request.requested_adapter)
    if adapter is None or adapter.identity != request.requested_adapter: return stop(ExecutionOutcome.BLOCKED, "adapter_unknown", command.execution_command_digest)
    if adapter.contract_version != request.adapter_contract_version or adapter.contract_version not in policy.adapter_contract_versions:
        return stop(ExecutionOutcome.BLOCKED, "adapter_version_unsupported", command.execution_command_digest)
    if not policy.required_capabilities.issubset(adapter.capabilities): return stop(ExecutionOutcome.BLOCKED, "adapter_capability_mismatch", command.execution_command_digest)
    try: claim, prior = state_store.claim(receipt_id=request.admission_receipt_id,
        command_digest=command.execution_command_digest, idempotency_key=request.idempotency_key,
        attempt_id=request.execution_attempt_id)
    except Exception: return stop(ExecutionOutcome.INDETERMINATE, "execution_state_unavailable", command.execution_command_digest)
    if claim == "replay" and prior is not None:
        return DeploymentExecutionResult(prior.outcome, prior.reason_code, prior.execution_attempt_id,
            prior.execution_command_digest, prior.evaluated_at, prior.attestation, True)
    if claim == "conflict": return stop(ExecutionOutcome.BLOCKED, "idempotency_conflict", command.execution_command_digest)
    if claim != "new": return stop(ExecutionOutcome.INDETERMINATE, "execution_in_progress", command.execution_command_digest)
    try: previous = state_store.mark_executing(command_digest=command.execution_command_digest)
    except Exception: return stop(ExecutionOutcome.INDETERMINATE, "execution_state_unavailable", command.execution_command_digest)
    try:
        provider = adapter.execute(command)
        if not isinstance(provider, ProviderExecutionResult): raise TypeError
    except Exception:
        now = request.evaluation_time
        provider = ProviderExecutionResult(request.execution_attempt_id, None, ExecutionOutcome.OUTCOME_UNKNOWN,
            now, None, sha256(b"provider-outcome-unavailable").hexdigest(), "provider_outcome_unknown")
    attestation = _attestation(command, provider, previous)
    result = DeploymentExecutionResult(provider.outcome, provider.reason_code, request.execution_attempt_id,
        command.execution_command_digest, request.evaluation_time, attestation)
    try: state_store.finalize(command_digest=command.execution_command_digest, result=result)
    except Exception:
        return DeploymentExecutionResult(ExecutionOutcome.OUTCOME_UNKNOWN, "execution_state_unavailable",
            request.execution_attempt_id, command.execution_command_digest, request.evaluation_time, attestation)
    return result


def public_execution_result(request: DeploymentExecutionRequest,
                            result: DeploymentExecutionResult) -> PublicDeploymentExecutionResult:
    attestation = result.attestation
    return PublicDeploymentExecutionResult(EXECUTION_CONTRACT_VERSION, request.execution_attempt_id,
        request.admission_receipt_id, attestation.attestation_id if attestation else None,
        result.outcome, result.reason_code, request.artifact_id, request.target_environment,
        request.release_id, attestation.started_at if attestation else None,
        attestation.completed_at if attestation else None, request.trace_reference)


class ATL16DeploymentExecutorAdapter:
    """Preserves ATL-A.15 DeploymentExecutorPort.execute(request, receipt)."""
    def __init__(self, *, verifier: AdmissionReceiptVerifierPort, policy: ExecutionPolicy,
                 adapters: Mapping[str, DeploymentAdapterPort], state_store: ExecutionStateStore,
                 request_factory: Any) -> None:
        self._verifier, self._policy, self._adapters = verifier, policy, dict(adapters)
        self._state_store, self._request_factory = state_store, request_factory
        self.last_result: DeploymentExecutionResult | None = None

    def execute(self, request: DeploymentAdmissionRequest, receipt: DeploymentAdmissionReceipt) -> None:
        execution_request = self._request_factory(request, receipt)
        self.last_result = execute_deployment(execution_request, receipt=receipt, verifier=self._verifier,
            policy=self._policy, adapters=self._adapters, state_store=self._state_store)
        if self.last_result.outcome in {ExecutionOutcome.BLOCKED, ExecutionOutcome.INVALID, ExecutionOutcome.INDETERMINATE}:
            raise RuntimeError("trusted deployment execution was not established")
