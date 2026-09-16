# ATL-A.26 — Continued-Operation Enforcement and Atomic Authorization Consumption

## Purpose

ATL-A.26 converts one valid ATL-A.25 continued-operation authorization into at most
one enforceable permission. Permission is returned only after the authorization is
successfully consumed through a single-winner atomic ledger operation. Invalid,
inactive, mismatched, replayed, unavailable, and uncertain state fails closed.

The trusted-deployment chain is now:

`ATL-A.22 readiness → ATL-A.23 revalidation → ATL-A.24 authentication → ATL-A.25 authorization → ATL-A.26 enforcement`

ATL-A.26 permits entry to a protected operation. It does not perform that operation,
report that the operation completed, recompute readiness, or recreate authorization
policy.

## Implemented slices

| Slice | Implementation |
| --- | --- |
| ATL-A.26.1 | Frozen, versioned request, result, evidence, consumption, binding, policy, state, reason-code, storage-port, and public DTO contracts; strict canonical request translation and binding digest. |
| ATL-A.26.2 | Artifact lookup, exact canonical digest verification, independent ATL-A.25 signature verification, validity-window checks, lifecycle checks, upstream-active checks, and fail-closed normalization. |
| ATL-A.26.3 | Storage-neutral atomic ledger contract, thread-safe reference ledger, and durable SQLite adapter using a transaction plus unique authorization-ID and request-ID constraints. |
| ATL-A.26.4 | Single-winner concurrency, exact retry recognition, changed-payload request-ID conflicts, replay blocking, and immutable consumed-state behavior. |
| ATL-A.26.5 | Domain-separated deterministic evidence fingerprints, previous-consumption trace references, explicit safe public projection, and non-secret normalized errors. |
| ATL-A.26.6 | Definite rollback, unknown-outcome fail-closed behavior, persisted-result recovery, authoritative lifecycle recheck inside the atomic boundary, and reconciliation-ready records. |

## Binding model

ATL-A.25 already signs the deployment, consumer, purpose, authorization policy,
authenticated-readiness references, validity interval, and authorization authority.
It deliberately does not contain an operation or enforcement-point claim. ATL-A.26
therefore adds a versioned enforcement policy containing exact tuples of:

```text
(deployment, consumer, enforcement point, purpose, operation)
```

The request must match both the signed ATL-A.25 claims and one complete A.26 tuple.
No identifier normalization, wildcarding, inference, or partial tuple match is used.

## Atomic and recovery semantics

The ledger owns two storage-level uniqueness invariants:

```text
UNIQUE(authorization_id)
UNIQUE(enforcement_request_id)
```

Within the atomic boundary it rechecks artifact identity, digest, lifecycle, upstream
state, validity, and enforcement-policy activity before attempting the insert. The
operation is permitted only after commit. An exact retry returns the persisted record
without inserting again. A reused request identifier with changed content and a new
request attempting to reuse the authorization are blocked.

A definite pre-commit persistence failure returns `indeterminate` with
`consumption_persistence_failed`. An unknown transaction outcome returns
`indeterminate` with `consumption_state_unavailable`; it never becomes permission.
The durable record remains authoritative for later reconciliation. Consumption is
terminal and is never reversed if the protected operation later fails.

## Evidence and public boundary

Every result carries frozen, deterministic evidence bound to the authorization
reference and digest, canonical request digest, observed lifecycle, consumption
result, normalized outcome, trusted decision time, policy, enforcement point,
correlation identifier, and prior consumption evidence when applicable. A successful
consumption record fingerprints the exact success evidence.

The public projection allowlists only the schema version, authorization and request
identifiers, deployment, purpose, normalized state and reasons, decision/consumption
times, evidence reference, and correlation identifier. It excludes signatures,
verification keys, readiness fingerprints, internal exceptions, request-binding
internals, database details, and policy mechanics.

## Validation

Run:

```powershell
python -m pytest tests/test_reference_architecture_continued_operation_enforcement.py -q
python -m pytest tests/test_reference_architecture_deployment_readiness.py tests/test_reference_architecture_deployment_readiness_revalidation.py tests/test_reference_architecture_deployment_readiness_authentication.py tests/test_reference_architecture_deployment_continued_operation_authorization.py tests/test_reference_architecture_continued_operation_enforcement.py -q
python scripts/check_repository_boundary.py
python scripts/check_public_export_boundary.py
python scripts/check_private_dependency_boundary.py
python -m pytest -m "not integration" -q
```

Implementation validation: **23 ATL-A.26 tests passed**; **130 focused A.22–A.26
tests passed**; **1,539 non-integration tests passed with 1 integration test
deselected**; repository, public-export, and private-dependency boundary checks passed.
