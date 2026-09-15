from __future__ import annotations
import json
from dataclasses import asdict
from datetime import datetime
from hashlib import sha256
from typing import Any

from src.reference_architecture_deployment_execution import verify_execution_attestation
from src.reference_architecture_deployment_execution_contract import DeploymentExecutionAttestation
from src.reference_architecture_deployment_outcome_verification import verify_outcome_verification_attestation
from src.reference_architecture_deployment_outcome_verification_contract import DeploymentOutcomeVerificationAttestation, DeploymentOutcomeVerificationState
from src.reference_architecture_deployment_integrity_contract import *

def _canon(v: Any)->bytes: return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode()
def _time(v: datetime)->str: return v.strftime("%Y-%m-%dT%H:%M:%SZ")
def _digest(v: dict[str,Any])->str: return sha256(_canon(v)).hexdigest()

def _baseline_doc(v: dict[str,Any])->dict[str,Any]: return {**v,"established_at":_time(v["established_at"])}
def establish_baseline(execution: DeploymentExecutionAttestation, reconciliation: DeploymentOutcomeVerificationAttestation) -> TrustedDeploymentBaseline:
    if not verify_execution_attestation(execution) or not verify_outcome_verification_attestation(reconciliation): raise ValueError("trusted evidence is invalid.")
    if reconciliation.state is not DeploymentOutcomeVerificationState.VERIFIED or reconciliation.execution_attestation_id != execution.attestation_id: raise ValueError("reconciliation is not verified.")
    if execution.configuration_digest is None: raise ValueError("configuration binding is unavailable.")
    value={"reconciliation_id":reconciliation.verification_id,"execution_attestation_id":execution.attestation_id,"authorization_id":execution.authorization_id,"artifact_digest":execution.artifact_digest,"release_id":execution.release_id,"tenant_id":execution.tenant_id,"environment":execution.environment,"configuration_digest":execution.configuration_digest,"established_at":reconciliation.verification_time}
    base_digest=_digest(_baseline_doc(value)); base_id=_digest({**_baseline_doc(value),"baseline_digest":base_digest})
    return TrustedDeploymentBaseline(baseline_id=base_id,baseline_digest=base_digest,**value)

def _obs_doc(o: IntegrityObservation)->dict[str,Any]:
    d=asdict(o); d.pop("observation_digest"); d["authorization_state"]=o.authorization_state.value; d["observed_at"]=_time(o.observed_at); return d
def normalized_observation(**kwargs: Any)->IntegrityObservation:
    provisional=IntegrityObservation(observation_digest="0"*64,**kwargs)
    return IntegrityObservation(observation_digest=_digest(_obs_doc(provisional)),**kwargs)
def verify_integrity_observation(o: IntegrityObservation)->bool: return _digest(_obs_doc(o))==o.observation_digest

def _result_doc(r: IntegrityResult)->dict[str,Any]:
    return {"baseline_id":r.baseline_id,"status":r.status.value,"drift":r.drift.value,"reason_category":r.reason_category,"remediation":[x.value for x in r.remediation],"evaluated_at":_time(r.evaluated_at),"observation_digest":r.observation_digest,"prior_status":r.prior_status.value if r.prior_status else None,"revocation":r.revocation.record_digest if r.revocation else None}
def verify_integrity_result(r: IntegrityResult)->bool: return _digest(_result_doc(r))==r.result_digest

def _classify(b: TrustedDeploymentBaseline,o: IntegrityObservation)->tuple[DriftClassification,str]:
    if not verify_integrity_observation(o) or o.observed_at is None: return DriftClassification.INVALID,"evidence_invalid"
    if any(v is None for v in (o.artifact_digest,o.release_id,o.tenant_id,o.environment,o.configuration_digest)): return DriftClassification.UNKNOWN,"evidence_unavailable"
    if o.authorization_state is AuthorizationIntegrityState.UNAVAILABLE: return DriftClassification.UNKNOWN,"authorization_unavailable"
    if o.authorization_state is not AuthorizationIntegrityState.ACTIVE: return DriftClassification.MATERIAL,"authorization_inactive"
    if (o.artifact_digest,o.release_id,o.tenant_id,o.environment,o.configuration_digest)!=(b.artifact_digest,b.release_id,b.tenant_id,b.environment,b.configuration_digest): return DriftClassification.MATERIAL,"binding_drift"
    return DriftClassification.NONE,"bindings_match"

def evaluate_integrity(baseline: TrustedDeploymentBaseline, observation: IntegrityObservation | None, *, evaluation_time: datetime, prior_status: TrustStatus | None=None)->IntegrityResult:
    if observation is None: drift,reason=DriftClassification.UNKNOWN,"evidence_unavailable"
    elif observation.deployment_reference != baseline.baseline_id or observation.observed_at>evaluation_time: drift,reason=DriftClassification.INVALID,"evidence_invalid"
    else: drift,reason=_classify(baseline,observation)
    status={DriftClassification.NONE:TrustStatus.TRUSTED,DriftClassification.NON_MATERIAL:TrustStatus.DEGRADED,DriftClassification.MATERIAL:TrustStatus.UNTRUSTED,DriftClassification.UNKNOWN:TrustStatus.INDETERMINATE,DriftClassification.INVALID:TrustStatus.INVALID}[drift]
    remediation=() if status is TrustStatus.TRUSTED else ((RemediationSignal.INVESTIGATE,) if status in {TrustStatus.DEGRADED,TrustStatus.INDETERMINATE} else (RemediationSignal.INVESTIGATE,RemediationSignal.REAUTHORIZE,RemediationSignal.BLOCK_FUTURE_CHANGE))
    rev=None
    if status in {TrustStatus.UNTRUSTED,TrustStatus.INVALID}:
        rv={"baseline_id":baseline.baseline_id,"prior_status":(prior_status or TrustStatus.TRUSTED).value,"status":status.value,"reason_category":reason,"occurred_at":_time(evaluation_time)}; rd=_digest(rv); rev=TrustRevocationRecord(record_id=_digest({**rv,"record_digest":rd}),record_digest=rd,baseline_id=baseline.baseline_id,prior_status=prior_status or TrustStatus.TRUSTED,status=status,reason_category=reason,occurred_at=evaluation_time)
    provisional=IntegrityResult(baseline.baseline_id,status,drift,reason,remediation,evaluation_time,observation.observation_digest if observation else None,"0"*64,prior_status,rev)
    return IntegrityResult(baseline.baseline_id,status,drift,reason,remediation,evaluation_time,provisional.observation_digest,_digest(_result_doc(provisional)),prior_status,rev)
