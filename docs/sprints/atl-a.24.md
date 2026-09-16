# ATL-A.24 — Trusted Deployment Readiness Authentication and Provenance Verification

## Purpose

ATL-A.24 authenticates the exact fresh readiness result produced by ATL-A.23 before downstream reliance. It signs and verifies provenance; it does not recompute ATL-A.22 readiness composition, execute deployments, authorize continued operation, manage keys, or implement replay consumption.

The trusted-deployment chain is now:

`ATL-A.22 readiness decision → ATL-A.23 current-evidence revalidation → ATL-A.24 authenticity verification → future reliance authorization/enforcement`

## Implemented slices

| Slice | Implementation |
| --- | --- |
| ATL-A.24.01 | Frozen versioned claims, envelope, policy, resolved-key, trusted-reference, outcome, state, normalized error, and public/internal reason contracts. |
| ATL-A.24.02 | Strict adapter accepts only an exact `ReadinessRevalidationResult` with matching fresh attestation/binding, deployment identity, valid A.22 digest, and ordered validity window. A.22 attestations, dictionaries, subclasses, and mismatched bindings are rejected. |
| ATL-A.24.03 | Deterministic SHA-256 fingerprint covers the complete canonical fresh attestation and evidence snapshot, deployment, evidence revision, issuance, expiry, and an A.24 domain separator. |
| ATL-A.24.04 | Canonical signing bytes cover the fingerprint, readiness claims, issuer, key, Ed25519 algorithm, policy reference, contract version, issuance, expiry, and a distinct signing domain. |
| ATL-A.24.05 | Immutable authorization policy and resolved public-key contracts separate authority from cryptographic signature validity and carry independent active/revoked/superseded lifecycles. |
| ATL-A.24.06 | Verification independently checks exact A.23 binding, half-open validity, policy applicability, deployment scope, issuer/key authorization, both lifecycles, and Ed25519 signature without rerunning A.22. |
| ATL-A.24.07 | Only `verified + ready` mints an immutable internal `TrustedReadinessReference`. Known invalidity is rejected; absent policy or key material requires review. All other results fail closed for reliance. |
| ATL-A.24.08 | Explicit public projection exposes only contract version, deployment identifier, readiness state, authentication state, normalized public reason codes, and verification time. |
| ATL-A.24.09 | A.22 and A.23 source contracts, call signatures, statuses, reason codes, public projections, and behavior remain unchanged. |
| ATL-A.24.10 | Tests cover end-to-end verification, all security-relevant mutations, substitution, expiry, lifecycle/authority, missing material, determinism, immutability, serialization, protected-data exclusion, and compatibility. |

## Decision semantics

Authentication and readiness are separate. A correctly signed `blocked` or `review_required` result has authentication state `verified`, but it receives no trusted reference and is ineligible for reliance. The only eligible combination is:

```text
authentication = verified
AND
readiness = ready
AND
trusted_reference is present
```

Known-invalid bindings, claims, signatures, policies, authorities, or keys return `rejected`. Missing policy or resolved-key material returns `review_required`; it never returns `verified`. Binding, authority, and key intervals use half-open time semantics: `active_from <= verification_time < expires_at`.

## Cryptographic and canonicalization boundary

The reference algorithm is Ed25519. The signing function is a caller-supplied callback receiving canonical bytes; no private key enters any A.24 contract or retained state. Verification receives an immutable resolved public-key record separately from policy authorization. A valid signature from a key absent from the supplied policy is still rejected.

Canonical JSON uses UTF-8, sorted keys, compact separators, canonical whole-second UTC timestamps, enum values, and deterministic collection handling. The binding fingerprint and signing payload use different explicit domain separators. Every readiness, evidence, identity, policy, version, and time claim that affects reliance is covered.

## Public and protected boundaries

The public DTO deliberately excludes signatures, issuer/key references, fingerprints, evidence/revisions, binding expiry, policy mechanics, public-key bytes, internal diagnostic comparisons, incident/recovery details, and trusted references. Detailed failures remain internal so the public surface is not a cryptographic diagnostic oracle.

ATL-A.24 provides no key store, private-key persistence, discovery network, automatic evidence collection, background monitoring, one-time-use store, replay prevention, risk scoring, deployment action, or continued-operation authorization. Repeated verification of the same valid envelope at the same evaluation time is deterministic and idempotent.

## Validation

Run:

```powershell
python -m pytest tests/test_reference_architecture_deployment_readiness*.py -q
python scripts/check_repository_boundary.py
python scripts/check_public_export_boundary.py
python scripts/check_private_dependency_boundary.py
python -m pytest -m "not integration" -q
```

Implementation validation (Python 3.12 workspace): **74 focused A.22–A.24 tests passed**;
**1,483 non-integration tests passed, 1 integration test deselected**. Repository,
public-export, and private-dependency boundary checks passed. CI remains responsible
for its configured Python 3.13 environment and pinned dependency set.
