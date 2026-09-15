from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from hashlib import sha256
from threading import Lock
from typing import Any, Mapping

from src.reference_architecture_deployment_execution import verify_execution_attestation
from src.reference_architecture_deployment_execution_contract import DeploymentExecutionAttestation
from src.reference_architecture_deployment_outcome_verification_contract import (
    OUTCOME_VERIFICATION_CONTRACT_VERSION, DeploymentOutcomeObservation,
    DeploymentOutcomeObserverPort, DeploymentOutcomeVerificationAttestation,
    DeploymentOutcomeVerificationResult, DeploymentOutcomeVerificationState,
    ExecutionAttestationVerifierPort, ExpectedDeploymentState, ObservedDeploymentState,
    ObservedHealthState, OutcomeVerificationPolicy, OutcomeVerificationStateStore,
    PublicDeploymentOutcomeVerificationResult,
)


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def _time(value: datetime | None) -> str | None:
    return value.strftime("%Y-%m-%dT%H:%M:%SZ") if value else None


def _policy_window(policy: OutcomeVerificationPolicy, verification_time: datetime) -> str:
    return sha256(_canonical({"policy_id": policy.policy_id, "version": policy.version,
        "verification_time": _time(verification_time)})).hexdigest()


def expected_deployment_state(attestation: DeploymentExecutionAttestation,
                              policy: OutcomeVerificationPolicy) -> ExpectedDeploymentState:
    values = {"artifact_digest": attestation.artifact_digest, "environment": attestation.environment,
        "execution_attestation_fingerprint": attestation.attestation_digest,
        "execution_attestation_id": attestation.attestation_id, "provider_identity": attestation.adapter_identity,
        "release_id": attestation.release_id, "tenant_id": attestation.tenant_id,
        "configuration_digest": attestation.configuration_digest}
    fingerprint = sha256(_canonical({**values, "required_health": policy.required_health.value})).hexdigest()
    return ExpectedDeploymentState(**values, required_health=policy.required_health, expected_state_fingerprint=fingerprint)


def _observation_document(observation: DeploymentOutcomeObservation) -> dict[str, Any]:
    return {"correlation_reference": observation.correlation_reference, "deployment_state": observation.deployment_state.value,
        "diagnostics_reference": observation.diagnostics_reference, "environment": observation.environment,
        "health_state": observation.health_state.value, "observed_artifact_digest": observation.observed_artifact_digest,
        "observed_at": _time(observation.observed_at), "observed_release_id": observation.observed_release_id,
        "observer_identity": observation.observer_identity, "provider_identity": observation.provider_identity}


def normalized_observation(*, observer_identity: str, provider_identity: str, environment: str,
                           observed_artifact_digest: str | None, observed_release_id: str | None,
                           deployment_state: ObservedDeploymentState, health_state: ObservedHealthState,
                           observed_at: datetime, correlation_reference: str | None = None,
                           diagnostics_reference: str | None = None) -> DeploymentOutcomeObservation:
    provisional = {"observer_identity": observer_identity, "provider_identity": provider_identity, "environment": environment,
        "observed_artifact_digest": observed_artifact_digest, "observed_release_id": observed_release_id,
        "deployment_state": deployment_state, "health_state": health_state, "observed_at": observed_at,
        "correlation_reference": correlation_reference, "diagnostics_reference": diagnostics_reference,
        "observation_fingerprint": "0" * 64}
    unsigned = DeploymentOutcomeObservation(**provisional)
    return DeploymentOutcomeObservation(**{**provisional, "observation_fingerprint": sha256(_canonical(_observation_document(unsigned))).hexdigest()})


def _reconcile(expected: ExpectedDeploymentState, observation: DeploymentOutcomeObservation,
               policy: OutcomeVerificationPolicy, verification_time: datetime) -> tuple[DeploymentOutcomeVerificationState, str]:
    if sha256(_canonical(_observation_document(observation))).hexdigest() != observation.observation_fingerprint:
        return DeploymentOutcomeVerificationState.INVALID, "observation_integrity_invalid"
    if observation.observed_at > verification_time:
        return DeploymentOutcomeVerificationState.INVALID, "evidence_time_invalid"
    if (verification_time - observation.observed_at).total_seconds() > policy.maximum_evidence_age_seconds:
        return DeploymentOutcomeVerificationState.INDETERMINATE, "evidence_stale"
    if observation.provider_identity != expected.provider_identity or observation.environment != expected.environment:
        return DeploymentOutcomeVerificationState.INVALID, "observer_binding_invalid"
    if observation.deployment_state is ObservedDeploymentState.UNKNOWN or observation.health_state is ObservedHealthState.UNKNOWN:
        return DeploymentOutcomeVerificationState.INDETERMINATE, "observation_inconclusive"
    if observation.deployment_state is not ObservedDeploymentState.DEPLOYED:
        return DeploymentOutcomeVerificationState.MISMATCH, "deployment_state_mismatch"
    if observation.observed_artifact_digest is None or observation.observed_release_id is None:
        return DeploymentOutcomeVerificationState.INDETERMINATE, "identity_incomplete"
    if observation.observed_artifact_digest != expected.artifact_digest:
        return DeploymentOutcomeVerificationState.MISMATCH, "artifact_mismatch"
    if observation.observed_release_id != expected.release_id:
        return DeploymentOutcomeVerificationState.MISMATCH, "release_mismatch"
    if observation.health_state is not expected.required_health:
        return DeploymentOutcomeVerificationState.MISMATCH, "health_mismatch"
    return DeploymentOutcomeVerificationState.VERIFIED, "outcome_confirmed"


def _attestation(expected: ExpectedDeploymentState, policy: OutcomeVerificationPolicy, verification_time: datetime,
                 state: DeploymentOutcomeVerificationState, reason_code: str,
                 observation: DeploymentOutcomeObservation | None) -> DeploymentOutcomeVerificationAttestation:
    diagnostics = (observation.diagnostics_reference,) if observation and observation.diagnostics_reference else ()
    values = {"contract_version": OUTCOME_VERIFICATION_CONTRACT_VERSION,
        "diagnostic_references": list(diagnostics), "evidence_timestamp": _time(observation.observed_at) if observation else None,
        "execution_attestation_fingerprint": expected.execution_attestation_fingerprint,
        "execution_attestation_id": expected.execution_attestation_id,
        "expected_state_fingerprint": expected.expected_state_fingerprint,
        "observation_fingerprint": observation.observation_fingerprint if observation else None,
        "observer_identity": observation.observer_identity if observation else None,
        "policy_id": policy.policy_id, "policy_version": policy.version, "reason_code": reason_code,
        "state": state.value, "verification_time": _time(verification_time)}
    digest = sha256(_canonical(values)).hexdigest()
    verification_id = sha256(_canonical({**values, "attestation_digest": digest})).hexdigest()
    return DeploymentOutcomeVerificationAttestation(verification_id=verification_id, attestation_digest=digest,
        diagnostic_references=diagnostics, evidence_timestamp=observation.observed_at if observation else None,
        execution_attestation_fingerprint=expected.execution_attestation_fingerprint,
        execution_attestation_id=expected.execution_attestation_id, expected_state_fingerprint=expected.expected_state_fingerprint,
        observation_fingerprint=observation.observation_fingerprint if observation else None,
        observer_identity=observation.observer_identity if observation else None, policy_id=policy.policy_id,
        policy_version=policy.version, reason_code=reason_code, state=state, verification_time=verification_time)


def verify_outcome_verification_attestation(attestation: DeploymentOutcomeVerificationAttestation) -> bool:
    values = {"contract_version": attestation.contract_version, "diagnostic_references": list(attestation.diagnostic_references),
        "evidence_timestamp": _time(attestation.evidence_timestamp), "execution_attestation_fingerprint": attestation.execution_attestation_fingerprint,
        "execution_attestation_id": attestation.execution_attestation_id, "expected_state_fingerprint": attestation.expected_state_fingerprint,
        "observation_fingerprint": attestation.observation_fingerprint, "observer_identity": attestation.observer_identity,
        "policy_id": attestation.policy_id, "policy_version": attestation.policy_version, "reason_code": attestation.reason_code,
        "state": attestation.state.value, "verification_time": _time(attestation.verification_time)}
    digest = sha256(_canonical(values)).hexdigest()
    return digest == attestation.attestation_digest and sha256(_canonical({**values, "attestation_digest": digest})).hexdigest() == attestation.verification_id


class SafeExecutionAttestationVerifierAdapter:
    def verify(self, attestation: DeploymentExecutionAttestation | None) -> bool:
        return attestation is not None and verify_execution_attestation(attestation)


class InMemoryOutcomeVerificationStateStore:
    def __init__(self) -> None:
        self._lock = Lock(); self._records: dict[tuple[str, str], DeploymentOutcomeVerificationAttestation | None] = {}

    def claim(self, *, execution_attestation_id: str, verification_window: str) -> tuple[str, DeploymentOutcomeVerificationAttestation | None]:
        with self._lock:
            key = (execution_attestation_id, verification_window)
            if key not in self._records:
                self._records[key] = None
                return "new", None
            value = self._records[key]
            return ("replay", value) if value is not None else ("busy", None)

    def finalize(self, *, execution_attestation_id: str, verification_window: str,
                 attestation: DeploymentOutcomeVerificationAttestation) -> None:
        with self._lock:
            key = (execution_attestation_id, verification_window)
            if self._records.get(key) is not None:
                raise ValueError("verification already finalized")
            self._records[key] = attestation


def verify_deployment_outcome(attestation: DeploymentExecutionAttestation | None, *, verification_time: datetime,
                              verifier: ExecutionAttestationVerifierPort, policy: OutcomeVerificationPolicy,
                              observers: Mapping[tuple[str, str], DeploymentOutcomeObserverPort],
                              state_store: OutcomeVerificationStateStore) -> DeploymentOutcomeVerificationResult:
    def result(state: DeploymentOutcomeVerificationState, reason: str,
               expected: ExpectedDeploymentState | None = None, observation: DeploymentOutcomeObservation | None = None) -> DeploymentOutcomeVerificationResult:
        if expected is None:
            return DeploymentOutcomeVerificationResult(state, reason, verification_time, None)
        record = _attestation(expected, policy, verification_time, state, reason, observation)
        return DeploymentOutcomeVerificationResult(state, reason, verification_time, record)
    try:
        if not verifier.verify(attestation):
            return result(DeploymentOutcomeVerificationState.INVALID, "execution_attestation_invalid")
    except Exception:
        return result(DeploymentOutcomeVerificationState.INVALID, "execution_attestation_unverifiable")
    assert attestation is not None
    try:
        expected = expected_deployment_state(attestation, policy)
    except Exception:
        return result(DeploymentOutcomeVerificationState.INVALID, "expected_state_invalid")
    try:
        window = _policy_window(policy, verification_time)
        claim, prior = state_store.claim(execution_attestation_id=attestation.attestation_id, verification_window=window)
    except Exception:
        return result(DeploymentOutcomeVerificationState.INDETERMINATE, "verification_state_unavailable", expected)
    if claim == "replay" and prior is not None:
        return DeploymentOutcomeVerificationResult(prior.state, prior.reason_code, verification_time, prior, True)
    if claim != "new":
        return result(DeploymentOutcomeVerificationState.INDETERMINATE, "verification_in_progress", expected)
    observer = observers.get((expected.provider_identity, expected.environment))
    if observer is None:
        outcome = result(DeploymentOutcomeVerificationState.INDETERMINATE, "observer_unavailable", expected)
    elif observer.provider_identity != expected.provider_identity or observer.target_environment != expected.environment:
        outcome = result(DeploymentOutcomeVerificationState.INVALID, "observer_binding_invalid", expected)
    else:
        try:
            observation = observer.observe(expected, verification_time=verification_time)
            if not isinstance(observation, DeploymentOutcomeObservation): raise TypeError
            if observation.observer_identity != observer.identity:
                outcome = result(DeploymentOutcomeVerificationState.INVALID, "observer_identity_invalid", expected, observation)
            else:
                state, reason = _reconcile(expected, observation, policy, verification_time)
                outcome = result(state, reason, expected, observation)
        except Exception:
            outcome = result(DeploymentOutcomeVerificationState.INDETERMINATE, "observation_unavailable", expected)
    try:
        assert outcome.attestation is not None
        state_store.finalize(execution_attestation_id=attestation.attestation_id, verification_window=window, attestation=outcome.attestation)
    except Exception:
        return result(DeploymentOutcomeVerificationState.INDETERMINATE, "verification_state_unavailable", expected)
    return outcome


def public_outcome_verification_result(result: DeploymentOutcomeVerificationResult) -> PublicDeploymentOutcomeVerificationResult:
    record = result.attestation
    return PublicDeploymentOutcomeVerificationResult(OUTCOME_VERIFICATION_CONTRACT_VERSION,
        record.verification_id if record else None, record.execution_attestation_id if record else None,
        result.state, result.reason_code, result.verification_time, record.evidence_timestamp if record else None)
