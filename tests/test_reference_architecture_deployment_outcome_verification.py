from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, replace
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json

from src.reference_architecture_deployment_execution_contract import DeploymentExecutionAttestation, ExecutionOutcome, ExecutionPolicyReference
from src.reference_architecture_deployment_outcome_verification import (InMemoryOutcomeVerificationStateStore, SafeExecutionAttestationVerifierAdapter, normalized_observation, public_outcome_verification_result, verify_deployment_outcome, verify_outcome_verification_attestation)
from src.reference_architecture_deployment_outcome_verification_contract import (DeploymentOutcomeVerificationState, ObservedDeploymentState, ObservedHealthState, OutcomeVerificationPolicy)

NOW = datetime(2026, 9, 15, 17, tzinfo=timezone.utc)

def canonical(value): return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()

def execution_attestation():
    values = {"adapter_identity": "reference", "adapter_version": "1.0", "admission_receipt_id": "a" * 64, "artifact_digest": "b" * 64, "authorization_id": "c" * 64, "completed_at": "2026-09-15T17:00:01Z", "contract_version": "1.0", "environment": "production", "execution_attempt_id": "attempt-1", "execution_command_digest": "d" * 64, "execution_policy": {"policy_id": "execution", "version": "1", "digest": "e" * 64}, "operation": "release", "outcome": "succeeded", "previous_state_reference": "f" * 64, "provider_operation_reference": "operation-1", "provider_response_digest": "0" * 64, "reason_code": "deployment_succeeded", "release_id": "release-1", "started_at": "2026-09-15T17:00:00Z", "tenant_id": "tenant-1", "trace_reference": "trace-1"}
    attestation_digest = sha256(canonical(values)).hexdigest()
    attestation_id = sha256(canonical({**values, "attestation_digest": attestation_digest})).hexdigest()
    return DeploymentExecutionAttestation(attestation_id=attestation_id, attestation_digest=attestation_digest, execution_policy=ExecutionPolicyReference("execution", "1", "e" * 64), **{key: value for key, value in values.items() if key not in {"contract_version", "execution_policy", "outcome", "started_at", "completed_at"}}, outcome=ExecutionOutcome.SUCCEEDED, started_at=NOW, completed_at=NOW + timedelta(seconds=1))

class Observer:
    identity = "reference-observer"; provider_identity = "reference"; target_environment = "production"
    def __init__(self, observation=None, error=None): self.observation, self.error, self.calls = observation, error, 0
    def observe(self, expected, *, verification_time):
        self.calls += 1
        if self.error: raise self.error
        return self.observation or normalized_observation(observer_identity=self.identity, provider_identity=expected.provider_identity, environment=expected.environment, observed_artifact_digest=expected.artifact_digest, observed_release_id=expected.release_id, deployment_state=ObservedDeploymentState.DEPLOYED, health_state=ObservedHealthState.HEALTHY, observed_at=verification_time, correlation_reference="correlation-1", diagnostics_reference="diagnostic-1")

def run(attestation=None, *, observer=None, policy=None, store=None):
    return verify_deployment_outcome(attestation or execution_attestation(), verification_time=NOW, verifier=SafeExecutionAttestationVerifierAdapter(), policy=policy or OutcomeVerificationPolicy("outcome", "1", 60), observers={("reference", "production"): observer or Observer()}, state_store=store or InMemoryOutcomeVerificationStateStore())

def test_verified_execution_intake_expected_projection_and_immutable_attestation():
    result = run()
    assert result.state is DeploymentOutcomeVerificationState.VERIFIED and result.reason_code == "outcome_confirmed" and result.attestation
    assert verify_outcome_verification_attestation(result.attestation)
    assert not verify_outcome_verification_attestation(replace(result.attestation, reason_code="changed"))
    assert run(replace(execution_attestation(), release_id="other")).state is DeploymentOutcomeVerificationState.INVALID

def test_reconciliation_distinguishes_mismatch_indeterminate_and_invalid():
    wrong = normalized_observation(observer_identity="reference-observer", provider_identity="reference", environment="production", observed_artifact_digest="1" * 64, observed_release_id="release-1", deployment_state=ObservedDeploymentState.DEPLOYED, health_state=ObservedHealthState.HEALTHY, observed_at=NOW)
    assert run(observer=Observer(wrong)).reason_code == "artifact_mismatch"
    stale = normalized_observation(observer_identity="reference-observer", provider_identity="reference", environment="production", observed_artifact_digest="b" * 64, observed_release_id="release-1", deployment_state=ObservedDeploymentState.DEPLOYED, health_state=ObservedHealthState.HEALTHY, observed_at=NOW - timedelta(seconds=61))
    assert run(observer=Observer(stale)).reason_code == "evidence_stale"
    bad = normalized_observation(observer_identity="reference-observer", provider_identity="wrong", environment="production", observed_artifact_digest="b" * 64, observed_release_id="release-1", deployment_state=ObservedDeploymentState.DEPLOYED, health_state=ObservedHealthState.HEALTHY, observed_at=NOW)
    assert run(observer=Observer(bad)).reason_code == "observer_binding_invalid"

def test_registry_failure_exception_public_allowlist_and_idempotency():
    attestation = execution_attestation()
    missing = verify_deployment_outcome(attestation, verification_time=NOW, verifier=SafeExecutionAttestationVerifierAdapter(), policy=OutcomeVerificationPolicy("outcome", "1", 60), observers={}, state_store=InMemoryOutcomeVerificationStateStore())
    assert missing.state is DeploymentOutcomeVerificationState.INDETERMINATE and missing.reason_code == "observer_unavailable"
    assert run(observer=Observer(error=TimeoutError("secret"))).reason_code == "observation_unavailable"
    encoded = json.dumps(asdict(public_outcome_verification_result(run())), default=str)
    for protected in ("artifact_digest", "provider_identity", "diagnostic", "observation_fingerprint"): assert protected not in encoded
    store, observer = InMemoryOutcomeVerificationStateStore(), Observer()
    with ThreadPoolExecutor(max_workers=8) as pool: results = list(pool.map(lambda _: run(attestation, observer=observer, store=store), range(8)))
    assert observer.calls == 1
    record = next(item.attestation for item in results if item.attestation)
    replay = run(attestation, observer=observer, store=store)
    assert replay.idempotent_replay and replay.attestation == record
