from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from datetime import datetime, timezone
from typing import Any

from src.reference_architecture_evidence_consumption_contract import (
    ConsumptionReasonCode, ConsumptionStatus, EvidenceConsumptionDecision,
    EvidenceConsumptionOutcome, EvidenceConsumptionRequest, EvidenceDisclosurePurpose,
    EvidenceLifecycleState,
)
from src.reference_architecture_evidence_consumption_policy import (
    ConsumptionPolicyRepositoryPort, HoldRepositoryPort, LifecycleRepositoryPort, RequesterResolverPort,
)
from src.reference_architecture_evidence_consumption_translation import (
    EvidenceConsumptionTranslationError, translate_untrusted_evidence_consumption_request,
)
from src.reference_architecture_evidence_ledger import EvidenceLedgerPort, verify_evidence_ledger_chain
from src.reference_architecture_evidence_ledger_contract import EvidenceLedgerEntry
from src.reference_architecture_evidence_package_builder import build_evidence_package
from src.reference_architecture_evidence_package_contract import PackageReasonCode


TrustedClock = Callable[[], datetime]


def _decision(reason: ConsumptionReasonCode, *, policy: str | None = None,
              evidence: Sequence[str] = (), status: ConsumptionStatus = ConsumptionStatus.DENIED,
              hold: str | None = None) -> EvidenceConsumptionDecision:
    return EvidenceConsumptionDecision(status, reason, policy, tuple(evidence), hold)


def _select(request: EvidenceConsumptionRequest, chain: Sequence[EvidenceLedgerEntry]) -> tuple[EvidenceLedgerEntry, ...] | None:
    by_id = {entry.entry_id: entry for entry in chain}
    if request.evidence_ids:
        if any(item not in by_id for item in request.evidence_ids): return None
        selected = [by_id[item] for item in request.evidence_ids]
    else: selected = list(chain)
    if request.run_id is not None: selected = [x for x in selected if x.evaluation_run_id == request.run_id]
    if request.sequence_start is not None: selected = [x for x in selected if x.sequence >= request.sequence_start]
    if request.sequence_end is not None: selected = [x for x in selected if x.sequence <= request.sequence_end]
    selected.sort(key=lambda x: x.sequence)
    return tuple(selected)


def evaluate_evidence_consumption(
    request: EvidenceConsumptionRequest, *, ledger: EvidenceLedgerPort, requester_resolver: RequesterResolverPort,
    policy_repository: ConsumptionPolicyRepositoryPort, lifecycle_repository: LifecycleRepositoryPort,
    hold_repository: HoldRepositoryPort, evaluated_at: datetime,
) -> EvidenceConsumptionDecision:
    """Fixed-order, fail-closed evaluation. Policy internals never enter the returned DTO."""
    try:
        if not isinstance(request, EvidenceConsumptionRequest):
            return _decision(ConsumptionReasonCode.MALFORMED_CONSUMPTION_REQUEST)
        if not isinstance(evaluated_at, datetime) or evaluated_at.tzinfo is None or evaluated_at.utcoffset() is None:
            return _decision(ConsumptionReasonCode.INTERNAL_CONSUMPTION_ERROR, status=ConsumptionStatus.ERROR)
        now = evaluated_at.astimezone(timezone.utc)
        scopes = requester_resolver.resolve(request.requester_id, request.requester_type)
        if not scopes: return _decision(ConsumptionReasonCode.REQUESTER_NOT_FOUND)
        if len(scopes) != 1: return _decision(ConsumptionReasonCode.AMBIGUOUS_REQUESTER)
        scope = scopes[0]
        if not scope.enabled: return _decision(ConsumptionReasonCode.REQUESTER_DISABLED)
        policy = policy_repository.get(request.policy_id, request.policy_version)
        if policy is None:
            known = callable(getattr(policy_repository, "contains_policy", None)) and policy_repository.contains_policy(request.policy_id)
            return _decision(ConsumptionReasonCode.UNSUPPORTED_POLICY_VERSION if known else ConsumptionReasonCode.POLICY_NOT_FOUND)
        policy_ref = f"{policy.policy_id}:{policy.version}"
        if policy.version != request.policy_version:
            return _decision(ConsumptionReasonCode.UNSUPPORTED_POLICY_VERSION)
        if now < policy.effective_at or (policy.expires_at is not None and now >= policy.expires_at):
            return _decision(ConsumptionReasonCode.POLICY_NOT_ACTIVE, policy=policy_ref)
        chain = ledger.chain(request.ledger_id)
        if not chain: return _decision(ConsumptionReasonCode.LEDGER_NOT_FOUND, policy=policy_ref)
        if not verify_evidence_ledger_chain(chain).verified:
            return _decision(ConsumptionReasonCode.LEDGER_VERIFICATION_FAILED, policy=policy_ref)
        selected = _select(request, chain)
        if selected is None: return _decision(ConsumptionReasonCode.EVIDENCE_NOT_FOUND, policy=policy_ref)
        if not selected: return _decision(ConsumptionReasonCode.RUN_SCOPE_MISMATCH, policy=policy_ref)
        refs = tuple(x.entry_id for x in selected)
        if selected[0].sequence != 1 or [x.sequence for x in selected] != list(range(1, selected[-1].sequence + 1)):
            return _decision(ConsumptionReasonCode.PACKAGE_SELECTION_INCOMPLETE, policy=policy_ref, evidence=refs)
        if scope.tenant_id != request.tenant_id:
            return _decision(ConsumptionReasonCode.TENANT_SCOPE_MISMATCH, policy=policy_ref, evidence=refs)
        if scope.allowed_ledger_ids and request.ledger_id not in scope.allowed_ledger_ids:
            return _decision(ConsumptionReasonCode.DISCLOSURE_NOT_ALLOWED, policy=policy_ref, evidence=refs)
        if not scope.may_export: return _decision(ConsumptionReasonCode.DISCLOSURE_NOT_ALLOWED, policy=policy_ref, evidence=refs)
        if request.run_id is not None and scope.allowed_run_ids and request.run_id not in scope.allowed_run_ids:
            return _decision(ConsumptionReasonCode.RUN_SCOPE_MISMATCH, policy=policy_ref, evidence=refs)
        if request.purpose not in policy.allowed_purposes or request.purpose not in scope.allowed_purposes:
            return _decision(ConsumptionReasonCode.PURPOSE_NOT_ALLOWED, policy=policy_ref, evidence=refs)
        if request.target_environment not in policy.allowed_environments or request.target_environment not in scope.allowed_environments:
            return _decision(ConsumptionReasonCode.ENVIRONMENT_NOT_ALLOWED, policy=policy_ref, evidence=refs)
        lifecycle_states = {}
        for entry in selected:
            if entry.evidence_type not in policy.allowed_evidence_types or (scope.allowed_evidence_types and entry.evidence_type not in scope.allowed_evidence_types):
                return _decision(ConsumptionReasonCode.EVIDENCE_TYPE_RESTRICTED, policy=policy_ref, evidence=refs)
            state = lifecycle_repository.state_for(entry.entry_id).state
            lifecycle_states[entry.entry_id] = state
            state_reason = {
                EvidenceLifecycleState.RESTRICTED: ConsumptionReasonCode.EVIDENCE_TYPE_RESTRICTED,
                EvidenceLifecycleState.EXPIRED: ConsumptionReasonCode.EVIDENCE_EXPIRED,
                EvidenceLifecycleState.RETIRED: ConsumptionReasonCode.EVIDENCE_RETIRED,
                EvidenceLifecycleState.REVOKED: ConsumptionReasonCode.EVIDENCE_REVOKED,
            }.get(state)
            if state_reason is not None:
                return _decision(state_reason, policy=policy_ref, evidence=refs)
        active_holds = sorted((x for x in hold_repository.holds_for(selected) if x.active_at(now)), key=lambda x: x.hold_id)
        for hold in active_holds:
            if hold.tenant_id != request.tenant_id or request.purpose not in hold.permitted_purposes:
                return _decision(ConsumptionReasonCode.EVIDENCE_ON_HOLD, policy=policy_ref, evidence=refs, hold=hold.hold_id)
        if any(state is EvidenceLifecycleState.ON_HOLD for state in lifecycle_states.values()) and not active_holds:
            return _decision(ConsumptionReasonCode.EVIDENCE_ON_HOLD, policy=policy_ref, evidence=refs)
        # Holds for an authorized investigation preserve eligibility across normal retention expiration.
        held_ids = {item for hold in active_holds for item in hold.evidence_ids}
        held_runs = {item for hold in active_holds for item in hold.run_ids}
        for entry in selected:
            retained_by_hold = entry.entry_id in held_ids or entry.evaluation_run_id in held_runs
            retention = policy.retention_by_evidence_type.get(entry.evidence_type)
            if retention is None: return _decision(ConsumptionReasonCode.EVIDENCE_TYPE_RESTRICTED, policy=policy_ref, evidence=refs)
            if now >= entry.recorded_at.astimezone(timezone.utc) + retention and not retained_by_hold:
                return _decision(ConsumptionReasonCode.EVIDENCE_EXPIRED, policy=policy_ref, evidence=refs)
        return _decision(ConsumptionReasonCode.CONSUMPTION_AUTHORIZED, policy=policy_ref, evidence=refs,
                         status=ConsumptionStatus.AUTHORIZED)
    except Exception:
        return _decision(ConsumptionReasonCode.INTERNAL_CONSUMPTION_ERROR, status=ConsumptionStatus.ERROR)


def consume_evidence_package(
    payload: Mapping[str, Any], *, ledger: EvidenceLedgerPort, requester_resolver: RequesterResolverPort,
    policy_repository: ConsumptionPolicyRepositoryPort, lifecycle_repository: LifecycleRepositoryPort,
    hold_repository: HoldRepositoryPort, clock: TrustedClock,
) -> EvidenceConsumptionOutcome:
    """Authorize first, then invoke A.07 with its exact cryptographic selection intact."""
    try:
        request = translate_untrusted_evidence_consumption_request(payload)
    except EvidenceConsumptionTranslationError:
        return EvidenceConsumptionOutcome(ConsumptionStatus.DENIED, ConsumptionReasonCode.MALFORMED_CONSUMPTION_REQUEST)
    try:
        evaluated_at = clock()
        decision = evaluate_evidence_consumption(request, ledger=ledger, requester_resolver=requester_resolver,
            policy_repository=policy_repository, lifecycle_repository=lifecycle_repository,
            hold_repository=hold_repository, evaluated_at=evaluated_at)
        if not decision.authorized:
            return EvidenceConsumptionOutcome(decision.status, decision.reason_code, decision.policy_reference,
                                              decision.evidence_references)
        package_payload = {"ledger_id": request.ledger_id, "evidence_ids": list(request.evidence_ids),
                           "run_id": request.run_id, "sequence_start": request.sequence_start,
                           "sequence_end": request.sequence_end, "format_version": request.package_version,
                           "metadata": {"purpose": request.purpose.value, "policy_reference": decision.policy_reference or "unknown"}}
        built = build_evidence_package(package_payload, ledger=ledger,
            authorize=lambda _request, records: tuple(x.entry_id for x in records) == decision.evidence_references)
        if not built.built:
            reason = (ConsumptionReasonCode.PACKAGE_SELECTION_INCOMPLETE
                      if built.reason_code in {PackageReasonCode.PACKAGE_INCOMPLETE, PackageReasonCode.EMPTY_SELECTION}
                      else ConsumptionReasonCode.INTERNAL_CONSUMPTION_ERROR)
            status = ConsumptionStatus.DENIED if reason is ConsumptionReasonCode.PACKAGE_SELECTION_INCOMPLETE else ConsumptionStatus.ERROR
            return EvidenceConsumptionOutcome(status, reason, decision.policy_reference, decision.evidence_references)
        return EvidenceConsumptionOutcome(ConsumptionStatus.AUTHORIZED, ConsumptionReasonCode.CONSUMPTION_AUTHORIZED,
                                          decision.policy_reference, decision.evidence_references, built.package)
    except Exception:
        return EvidenceConsumptionOutcome(ConsumptionStatus.ERROR, ConsumptionReasonCode.INTERNAL_CONSUMPTION_ERROR)
