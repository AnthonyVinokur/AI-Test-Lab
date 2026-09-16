# ATL-A.31 — Authorized-Response Outcome Reconciliation and Closure Handoff

## Purpose

ATL-A.31 reconciles one authoritative ATL-A.30 response authorization with the
corresponding committed ATL-A.20 remediation decision, execution attestation,
and post-remediation verification. It creates one immutable, signed response
outcome and creates a narrow ATL-A.21 handoff only when recovery was
independently verified.

The trusted lifecycle is now:

`A.26 consume → A.27 execute → A.28 verify → A.29 settle → A.30 authorize response → A.20 remediate and verify → A.31 reconcile → A.21 close`

ATL-A.31 does not execute or retry remediation, observe external state, expand
authorization, reinterpret settlement, classify root cause, or close an
incident. ATL-A.21 retains the final closure decision.

## Implemented slices

| Slice | Implementation |
| --- | --- |
| ATL-A.31.1 | Frozen request, policy, authoritative-record, outcome, reason, evidence, atomic-commit, closure-handoff, repository-port, signer-port, and public DTO contracts with strict validation. |
| ATL-A.31.2 | Repository-only committed A.30/A.20 evidence admission with canonical digest, signature, decision, identity, expiry, and lineage verification. |
| ATL-A.31.3 | Exact response-authorization consumption, remediation request, capability, scope, constraint, manifest, attempt, verification-target, incident, and operation reconciliation. |
| ATL-A.31.4 | Deterministic `verified_recovery`, `response_failed`, `response_indeterminate`, `expired_unexecuted`, and `rejected` classification with stable reasons. |
| ATL-A.31.5 | Thread-safe and SQLite atomic create-or-return repositories with lifecycle/request/idempotency uniqueness, immutable replay, concurrent single-winner behavior, lookup, and restart recovery. |
| ATL-A.31.6 | Atomically committed ATL-A.21 handoff only for verified recovery, with independent authoritative reconciliation reload and signature, lineage, policy, scope, capability, and expiry checks. |
| ATL-A.31.7 | Allowlisted public evidence, canonical untrusted request translation, adversarial/concurrency/restart/redaction tests, sprint documentation, and changelog. |

## Deterministic outcome table

| Authoritative state | ATL-A.31 outcome | Closure handoff |
| --- | --- | --- |
| Accepted execution and passed independent verification | `verified_recovery` | Yes |
| Accepted execution and failed verification | `response_failed` | No |
| Accepted execution and unavailable/inconclusive verification | `response_indeterminate` | No |
| Valid authorization expired with no accepted execution | `expired_unexecuted` | No |
| Invalid, tampered, uncommitted, mismatched, widened, late, or over-attempt evidence | `rejected` | No |

Execution success is never treated as recovery. `verified_recovery` requires a
committed ATL-A.20 verification whose canonical digest is valid, which refers to
the exact accepted execution, covers the exact modified scope, and reports
`passed`.

## Authoritative admission and compatibility

ATL-A.20 predates A.30 and does not put standalone IDs, consumed authorization,
scope, constraints, manifest identity, or attempt number directly on its domain
records. A.31 therefore uses immutable authoritative repository records around
the original A.20 contracts. These wrappers bind that required metadata without
changing A.20 or trusting caller-supplied copies.

The A.30 authorization is validated without treating its later expiry as a
signature failure. A.31 separately establishes whether execution began within
the signed authorization interval. An execution after expiry is rejected;
expiry with no accepted execution is preserved as `expired_unexecuted`.

## Atomicity and idempotency

The lifecycle uniqueness boundary is the domain-separated A.30 response
authorization ID. Request IDs and semantic idempotency keys are also globally
unique. Exact retries return the original byte-equivalent commit. Changed reuse
conflicts and cannot replace the first result.

The reconciliation evidence and optional closure handoff are one
`ReconciliationCommit`. In-memory persistence publishes both while holding one
lock. SQLite uses `BEGIN IMMEDIATE` and one row update for both serialized
artifacts, so a handoff cannot become visible without its reconciliation.

## ATL-A.21 boundary

The handoff carries only closure capability, exact scope, required policy,
expiry, and A.29–A.31/A.20 lineage references. The A.21-side validator reloads
the authoritative commit by reconciliation ID and checks:

- reconciliation identity, digest, signer, and signature;
- authoritative repository presence and exact stored handoff equality;
- `verified_recovery` plus closure eligibility;
- incident, settlement, authorization, remediation, execution, and verification lineage;
- exact closure scope and required A.21 policy version;
- handoff identity, digest, signature, and expiry.

This handoff establishes eligibility only. Existing A.21 root-cause,
preventive-action, closure-authorization, and final closure controls still apply.

## Public evidence

The public DTO exposes safe outcome, reason, policy, time, and operator lineage
references. It excludes signatures, signing identities, evidence digests,
manifest details, remediation parameters, constraints, before/after state,
repository keys, exceptions, and raw security evidence.

## Validation

```powershell
python -m pytest tests/test_reference_architecture_response_outcome_reconciliation.py -q
python -m pytest tests/test_reference_architecture_continued_operation_enforcement.py tests/test_reference_architecture_continued_operation_execution.py tests/test_reference_architecture_continued_operation_reconciliation.py tests/test_reference_architecture_continued_operation_settlement.py tests/test_reference_architecture_continued_operation_response.py tests/test_reference_architecture_response_outcome_reconciliation.py -q
python scripts/check_repository_boundary.py
python scripts/check_public_export_boundary.py
python scripts/check_private_dependency_boundary.py
python -m pytest -m "not integration" -q
```

Implementation validation: **17 ATL-A.31 tests passed**; **145 focused
A.26–A.31 tests passed**; **1,662 non-integration tests passed, 10
cross-repository tests skipped, and 1 integration test deselected**;
repository, public-export, and private-dependency boundary checks passed.
