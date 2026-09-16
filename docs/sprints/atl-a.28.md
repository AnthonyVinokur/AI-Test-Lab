# ATL-A.28 — Protected-Operation Outcome Verification and Reconciliation

## Purpose

ATL-A.28 independently verifies the external effect of one authoritative,
committed ATL-A.27 protected-operation execution. It derives the expected state
from the exact execution request, A.27 operation manifest, and registered
verification manifest; obtains fresh state through a registered read-only
observer; and commits an immutable reconciliation attestation.

The trusted continued-operation chain is now:

`ATL-A.22 readiness → A.23 revalidation → A.24 authentication → A.25 authorization → A.26 consumption → A.27 at-most-once execution → A.28 observation and reconciliation`

A.28 never invokes, retries, repairs, compensates, rolls back, or otherwise
modifies the protected operation or provider state.

## Implemented slices

| Slice | Implementation |
| --- | --- |
| ATL-A.28.01 | Frozen, versioned request, field, postcondition, manifest, policy, observation, result, attestation, repository-port, observer-port, and public DTO contracts with strict UTC, identifier, digest, tuple, scalar-value, and ambiguity validation. |
| ATL-A.28.02 | Authoritative repository-only A.27 intake with committed-state, attestation-integrity, A.26 lineage, command digest, request, manifest, adapter, operation, deployment, consumer, enforcement-point, purpose, target, parameter, and correlation verification. |
| ATL-A.28.03 | Deterministic postcondition derivation from an exact A.27 manifest plus a registered verification manifest bound to its reference, version, digest, operation, and canonical parameter digest. |
| ATL-A.28.04 | Exact-match observer registry across identity, version, provider, resource type, operation, manifest version, capability, enabled/revoked state, and an explicit read-only declaration. |
| ATL-A.28.05 | Bounded observation requests with post-invocation ordering, trusted UTC time, freshness, timeout, verification-window, partial-state, and normalized exception handling. |
| ATL-A.28.06 | Deterministic observation normalization with sorted typed fields, explicit present/absent/unknown states, volatile-field removal, binding checks, and domain-separated digests. |
| ATL-A.28.07 | Fail-closed reconciliation for resource existence/absence, lifecycle state, field projections, revision advancement, and manifest-defined attributes, producing only `verified`, `mismatch`, `indeterminate`, or `invalid`. |
| ATL-A.28.08 | Thread-safe and durable SQLite evidence repositories with atomic claims, exact replay, changed-input conflict detection, immutable commits, later-round append semantics, and explicit unknown-commit handling. |
| ATL-A.28.09 | Minimal allowlisted public projection with no authorization material, raw provider state, canonical parameters, internal policy configuration, exceptions, credentials, or internal digests. |
| ATL-A.28.10 | Focused outcome, threat, time, concurrency, durability, determinism, redaction, boundary, and A.22–A.27 compatibility coverage plus sprint documentation. |

## Trust boundary and data flow

1. The caller supplies only a strict reconciliation request whose duplicated
   binding values are assertions, not authority.
2. The service retrieves the committed A.27 execution evidence by attestation
   reference from the authoritative repository.
3. It independently verifies the A.27 attestation, reconstructs the A.27 command
   binding from the committed A.26 record and execution manifest, and exact-matches
   every request binding.
4. It resolves a registered verification manifest that is cryptographically bound
   to the same A.27 manifest and canonical parameter digest.
5. It resolves exactly one enabled, non-revoked, capable, read-only observer.
6. It normalizes fresh observations, reconciles them against the derived
   postcondition, and commits one append-only attestation.
7. The public projection exposes only the safe result identity, execution and
   operation references, outcome, reason, and evidence times.

A caller-created dictionary, reconstructed A.27 result, uncommitted attestation,
caller-supplied expected state, unknown observer, or raw provider success claim
cannot cross this trust boundary as verified evidence.

## State transitions

| Condition | Outcome | Representative reason |
| --- | --- | --- |
| Fresh normalized state satisfies the derived postcondition | `verified` | `expected_state_observed` |
| Fresh complete state contradicts the derived postcondition | `mismatch` | `expected_state_mismatch` |
| State is missing, partial, stale, pre-invocation, conflicting, timed out, or unavailable | `indeterminate` | `observation_unavailable`, `observation_partial`, `observation_stale`, `observation_precedes_execution`, `observations_conflict` |
| A.27 evidence, binding, manifest, observer registration, policy, or observation identity is structurally or cryptographically unusable | `invalid` | `execution_binding_mismatch`, `manifest_invalid`, `observer_not_found`, `observation_invalid` |

Only `verified` establishes that the expected provider state was independently
observed. The A.27 adapter outcome is historical context and never directly selects
the A.28 outcome. Therefore an A.27 `succeeded` execution may reconcile to
`mismatch`, while A.27 `failed` or `outcome_unknown` may reconcile to `verified`.

## Determinism, idempotency, and recovery

Requests, expected postconditions, normalized observations, and attestations use
canonical JSON with domain-separated SHA-256 identities. Volatile observer fields
are removed before comparison and hashing. A normalized observation set is sorted
before reconciliation and evidence generation.

The repository claims an idempotency key against the complete canonical request
digest. An exact retry returns the already committed result without observing the
provider again. Changed input under the same key returns
`reconciliation_request_conflict`. A later verification round uses a new request,
round, and idempotency identity and appends new evidence; it never edits the older
record. A commit whose status cannot be established returns `indeterminate` with
`commit_status_unknown` and does not expose an unconfirmed verified attestation.

## Examples

- The A.27 adapter returned `succeeded`, but the observer sees lifecycle state
  `inactive` instead of `active`: A.28 returns `mismatch`.
- The A.27 adapter timed out after invocation, but a fresh observer sees the exact
  expected state: A.28 returns `verified` without repeating the operation.
- The observer returns a state captured before A.27 invocation began: A.28 returns
  `indeterminate` with `observation_precedes_execution`.
- Two authoritative observations disagree about the relevant state: A.28 returns
  `indeterminate` with `observations_conflict`.

## Explicit exclusions

ATL-A.28 does not invoke or retry the protected operation, consume authorization,
reverse A.26 consumption, modify A.27 evidence, remediate a mismatch, roll back or
compensate, approve a retry, schedule repeated verification, continuously monitor
production, guarantee exactly-once external effects, manage provider credentials or
signing keys, replace provider consistency guarantees, make a deployment/governance
approval, or close an incident.

## Validation

Run:

```powershell
python -m pytest tests/test_reference_architecture_continued_operation_reconciliation.py -q
python -m pytest tests/test_reference_architecture_deployment_readiness.py tests/test_reference_architecture_deployment_readiness_revalidation.py tests/test_reference_architecture_deployment_readiness_authentication.py tests/test_reference_architecture_deployment_continued_operation_authorization.py tests/test_reference_architecture_continued_operation_enforcement.py tests/test_reference_architecture_continued_operation_execution.py tests/test_reference_architecture_continued_operation_reconciliation.py -q
python scripts/check_repository_boundary.py
python scripts/check_public_export_boundary.py
python scripts/check_private_dependency_boundary.py
python -m pytest -m "not integration" -q
```

Implementation validation: **32 ATL-A.28 tests passed**; **205 focused A.22–A.28
tests passed**; **1,615 non-integration tests passed, 10 environment-dependent
tests skipped, and 1 integration test deselected**; repository, public-export, and
private-dependency boundary checks passed.
