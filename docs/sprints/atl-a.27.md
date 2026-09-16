# ATL-A.27 — Trusted Continued-Operation Execution and Outcome Attestation

## Purpose

ATL-A.27 converts one committed ATL-A.26 permission into at most one
framework-controlled protected-operation invocation. It distinguishes permission,
attempt, and outcome; a consumed authorization is never treated as proof that an
operation ran or succeeded.

The trusted-deployment chain is now:

`ATL-A.22 readiness → ATL-A.23 revalidation → ATL-A.24 authentication → ATL-A.25 authorization → ATL-A.26 enforcement → ATL-A.27 execution`

ATL-A.27 attests what its execution boundary observed. Independent observation of
the resulting runtime state and later reconciliation remain outside this sprint.

## Implemented slices

| Slice | Implementation |
| --- | --- |
| ATL-A.27.01 | Frozen, versioned request, trusted-permit, operation-manifest, execution-policy, command, claim, adapter-result, attestation, result, reason-code, storage-port, adapter-port, and public DTO contracts. |
| ATL-A.27.02 | Strict untrusted JSON/mapping translation, duplicate-key rejection, exact field sets, canonical wire form, whole-second UTC timestamps, size bounds, and raw-command, parameter, credential, provider-response, and trust-flag rejection. |
| ATL-A.27.03 | Authoritative ATL-A.26 consumption-record lookup by evidence reference; missing, unavailable, forged, or mismatched state fails closed and only a committed record produces an internal trusted permit. |
| ATL-A.27.04 | Exact authorization, enforcement, request-binding, deployment, consumer, enforcement-point, purpose, operation, and correlation checks plus domain-separated deterministic command identity. |
| ATL-A.27.05 | Immutable manifest resolution and digest verification; deployment restrictions, execution-policy identity, adapter allowlists, contract-version checks, capabilities, at-most-once classification, and maximum permit-to-execution delay. |
| ATL-A.27.06 | Storage-neutral claim contract, thread-safe reference implementation, and durable SQLite implementation with unique authorization, enforcement-request, attempt, and idempotency keys. |
| ATL-A.27.07 | Single-winner concurrency, exact retry recovery, changed-request conflicts, consumed-permission replay blocking, committed pre-invocation state, and no automatic reinvocation after invocation may have begun. |
| ATL-A.27.08 | Provider-neutral adapter invocation and explicit success, failure, rejection, timeout, malformed-response, exception, persistence-failure, and unknown-outcome normalization. |
| ATL-A.27.09 | Immutable deterministic outcome attestations, independent digest verification, prior execution-state references, sanitized provider-response fingerprints, and durable result recovery. |
| ATL-A.27.10 | Minimal allowlisted public projection, threat and protected-data tests, A.22–A.26 compatibility tests, repository-boundary checks, documentation, and sprint closure. |

## Trust and binding model

Callers submit duplicate upstream values only as exact-match assertions. The service
resolves the ATL-A.26 record from its trusted repository and does not accept an
enforcement result or caller-created permit as evidence. The record must match every
authorization, enforcement, deployment, consumer, enforcement-point, purpose,
operation, request-binding, evidence, and correlation value.

The operation registry supplies the immutable executable definition. The untrusted
request has no command, unrestricted arguments, provider credentials, or provider
payload. A command identity is calculated from a domain-separated canonical document
that binds the verified A.26 permit, manifest input fingerprint, adapter, policy,
attempt, and idempotency key.

## Atomic and recovery semantics

The state store commits a claim before adapter invocation and enforces:

```text
UNIQUE(authorization_id)
UNIQUE(enforcement_request_id)
UNIQUE(execution_attempt_id)
UNIQUE(idempotency_key)
```

An exact retry returns the durable result, or a safe current-state projection if no
final result exists. A new attempt cannot reuse the consumed permission. Conflicting
attempt or idempotency content is blocked. Concurrent callers produce one claim
winner and the adapter is never invoked by a loser.

Provider exceptions and malformed responses become `outcome_unknown` because
invocation may have occurred. An adapter-authoritative timeout remains `timed_out`;
it is not rewritten as failure or success. Failure to persist a result after possible
invocation also returns `outcome_unknown`. None of these paths restores ATL-A.26
consumption or automatically invokes the operation again.

## Evidence and public boundary

Every completed or possibly completed invocation produces a digest-verifiable
attestation bound to the A.26 evidence, command, manifest, exact protected-operation
identity, adapter, policy, normalized outcome, timestamps, sanitized provider
fingerprint, previous execution state, and correlation identifier.

The public result exposes only the version, safe identities, operation, normalized
outcome and reason, times, attestation reference, correlation identifier, and
idempotent indicator. It excludes signatures, upstream/internal digests, manifest
contents, commands, parameters, credentials, raw provider data, exceptions, adapter
configuration, policy mechanics, and database details.

## Validation

Run:

```powershell
python -m pytest tests/test_reference_architecture_continued_operation_execution.py -q
python -m pytest tests/test_reference_architecture_deployment_readiness.py tests/test_reference_architecture_deployment_readiness_revalidation.py tests/test_reference_architecture_deployment_readiness_authentication.py tests/test_reference_architecture_deployment_continued_operation_authorization.py tests/test_reference_architecture_continued_operation_enforcement.py tests/test_reference_architecture_continued_operation_execution.py -q
python scripts/check_repository_boundary.py
python scripts/check_public_export_boundary.py
python scripts/check_private_dependency_boundary.py
python -m pytest -m "not integration" -q
```

Implementation validation: **43 ATL-A.27 tests passed**; **173 focused A.22–A.27
tests passed**; **1,583 non-integration tests passed, 10 environment-dependent tests
skipped, and 1 integration test deselected**; repository, public-export, and
private-dependency boundary checks passed.
