# ATL-A.25 — Trusted Deployment Continued-Operation Authorization

## Purpose

ATL-A.25 converts an authenticated, fresh, `ready` ATL-A.24 result into a narrowly
scoped and time-bounded authorization for one exact deployment, consumer, purpose,
request, policy, and validity interval. It authorizes intent only. It does not change
traffic, execute infrastructure operations, mutate deployment state, or consume an
authorization.

The trusted-deployment chain is now:

`ATL-A.22 readiness → ATL-A.23 revalidation → ATL-A.24 authentication → ATL-A.25 authorization → future ATL-A.26 enforcement`

## Implemented slices

| Slice | Implementation |
| --- | --- |
| ATL-A.25.01 | Frozen, versioned request, grant, policy, authority, resolved-key, signed-artifact, outcome, verification, lifecycle, reason, normalized-error, and public DTO contracts. |
| ATL-A.25.02 | Strict A.24 consumption boundary invokes `verify_readiness_authentication` over an exact A.23 result. Caller-created A.24 outcomes, DTOs, or trusted references cannot enter as authority. |
| ATL-A.25.03 | Exact proposition binds request, deployment, consumer, purpose, request/evaluation/expiry times, policy reference, authenticated readiness, and authorization signer. |
| ATL-A.25.04 | Canonical UTF-8 JSON, whole-second UTC timestamps, sorted keys, compact separators, SHA-256, and separate proposition, identifier, and signing domains provide deterministic identity. |
| ATL-A.25.05 | Immutable policy controls deployments, consumers, purposes, A.24 versions and issuers/keys, maximum duration, policy lifecycle, and authorization signer/key scope. |
| ATL-A.25.06 | Exact checks bind the request to A.24 digest/fingerprint, deployment, readiness authority, policy, signer, and the shortest applicable validity window. |
| ATL-A.25.07 | Deterministic `authorized`, `denied`, and `review_required` outcomes. Only `authorized` carries an artifact; known invalidity is never softened into review. |
| ATL-A.25.08 | Immutable Ed25519 signed authorization, caller-supplied signing callback, canonical serialization, strict translation, and an independent A.26-ready verifier. Private keys never enter retained state. |
| ATL-A.25.09 | Explicit allowlisted public projection exposes only schema version, deployment, purpose, state, normalized public reasons, decision time, and authorized expiry. |
| ATL-A.25.10 | Security, mutation, substitution, lifecycle, expiry, determinism, serialization, protected-data, boundary, and A.22–A.24 compatibility coverage. |

## Authorization semantics

Authorization requires all of the following:

```text
A.24 authentication = verified
AND readiness = ready
AND trusted readiness reference is internally minted and current
AND request/readiness/policy/signer bindings are exact
AND policy, signer, and resolved signing key are active
AND deployment, consumer, purpose, version, and authorities are permitted
AND requested duration is within policy maximum
AND requested expiry does not exceed any upstream validity boundary
```

The effective upper bound is the earliest of the authenticated readiness expiry,
policy expiry, authorization-signing authority expiry, and resolved signing-key
expiry. A request that exceeds a boundary is denied rather than silently shortened.
All validity intervals are half-open: an authorization is active at `not_before` and
inactive at `expires_at`.

Known-invalid authentication, blocked or review-required readiness, mismatched
bindings, unsupported versions, disallowed scope, expired inputs, revoked or
superseded authority, and invalid signatures return `denied`. Missing authorization
policy or independently resolved signing-key material returns `review_required`.

## Cryptographic and enforcement boundary

The proposition digest covers every claim that can change authorization meaning. The
authorization identifier is deterministically derived from that proposition digest.
The Ed25519 signature covers the identifier, full proposition, proposition digest,
algorithm, and an independent signing-domain separator.

The signer is a callback that receives canonical bytes. ATL-A.25 stores no private
key and verifies the returned signature against independently resolved public-key
material before returning `authorized`. The independent verifier checks integrity,
signature, lifecycle time, and optional deployment/consumer/purpose applicability.

ATL-A.25 does not deploy, stop, restart, promote, roll back, change traffic, refresh
readiness evidence, manage keys, store replay state, or atomically consume an
authorization. Those operational enforcement concerns remain outside this boundary
and atomic consumption belongs to ATL-A.26.

## Public and protected boundaries

The public DTO excludes signatures, digests, binding fingerprints, readiness and
authorization issuer/key identities, policy mechanics, grants, trusted references,
evidence revisions, lifecycle comparisons, public-key bytes, internal reasons, and
consumer credentials. Detailed failures remain internal so the public API is not a
policy or cryptographic diagnostic oracle.

## Validation

Run:

```powershell
python -m pytest tests/test_reference_architecture_deployment_continued_operation_authorization.py -q
python -m pytest tests/test_reference_architecture_deployment_readiness*.py tests/test_reference_architecture_deployment_continued_operation_authorization.py -q
python scripts/check_repository_boundary.py
python scripts/check_public_export_boundary.py
python scripts/check_private_dependency_boundary.py
python -m pytest -m "not integration" -q
```

Implementation validation (Python 3.12 workspace): **33 ATL-A.25 tests passed**;
**107 focused A.22–A.25 tests passed**; **1,516 non-integration tests passed with
1 integration test deselected**; repository, public-export, and private-dependency
boundary checks passed.
