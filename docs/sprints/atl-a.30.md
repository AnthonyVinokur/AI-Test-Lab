# ATL-A.30 — Settled-Outcome Response Authorization and Incident Handoff

## Purpose

ATL-A.30 converts one authoritative abnormal ATL-A.29 settlement into one
immutable, policy-bound response authorization. It admits only a committed and
authentic settlement, resolves exact immutable policy and response-manifest
versions, enforces settlement eligibility and original scope, atomically claims
the response boundary, and signs a narrow authorization that ATL-A.20 can
validate and consume.

The trusted chain is now:

`A.26 consumption → A.27 execution → A.28 verification → A.29 settlement → A.30 response authorization → A.20 remediation`

A.30 does not call an adapter, mutate external state, retry the protected
operation, execute remediation, observe provider state, or close an incident.

## Implemented slices

| Slice | Implementation |
| --- | --- |
| ATL-A.30.1 | Frozen, versioned request, policy, manifest, authoritative-source, outcome, reason, evidence, result, claim, handoff, repository-port, signer-port, and safe public DTO contracts with strict validation and canonical serialization. |
| ATL-A.30.2 | Repository-only committed ATL-A.29 lookup with settlement ID, digest, signature, schema, status, and A.26–A.29 lineage admission. |
| ATL-A.30.3 | Immutable `(id, version)` policy and manifest registries with calculated digests, approved-manifest references, role, status, response-type, scope, constraint, attempt, lifetime, and remediation-capability rules. |
| ATL-A.30.4 | Deterministic failure authorization, suspended fail-closed/manual-review behavior, success ineligibility, rejected-evidence rejection, stable reasons, and no-privilege-expansion checks. |
| ATL-A.30.5 | Thread-safe and SQLite atomic stores with lifecycle, request-ID, and idempotency-key uniqueness, exact replay, changed-reuse conflict, immutable commit, crash recovery, and expired-replay refusal. |
| ATL-A.30.6 | Independently verifiable handoff containing one exact capability, manifest fingerprint, incident and settlement lineage, scope, constraints, attempts, expiry, digest, and signature; translation into the existing ATL-A.20 `RemediationRequest` contract without execution. |
| ATL-A.30.7 | Domain-separated signed evidence, allowlisted public DTO, audit-safe reasons, adversarial and concurrency tests, architecture documentation, and changelog. |

## Decision table

| ATL-A.29 status | A.30 behavior |
| --- | --- |
| `settled_failure` | May authorize only a requested response type and exact manifest permitted by the registered policy. |
| `suspended` | May create only manual-review, investigation, or reverification authority. Failure-assuming remediation remains unauthorized. |
| `settled_success` | Returns `ineligible` and creates no response authorization. |
| `rejected` | Returns a safe rejection and creates no executable authority from inadmissible evidence. |

Every authorized outcome names one immutable response manifest. A caller cannot
submit executable commands or substitute trusted evidence, policy, manifest,
status, incident identity, or lineage.

## Atomicity, idempotency, and expiration

The lifecycle uniqueness boundary is the domain-separated settlement ID plus
response type. Response-request IDs and semantic idempotency keys are also
globally unique. The first valid claim wins. An exact retry returns the original
persisted evidence; changed reuse or a competing claim returns `conflict` and
cannot widen or replace authority.

SQLite uses `BEGIN IMMEDIATE`, primary and unique constraints, write-ahead
logging, compare-before-update commit, and explicit pending-record recovery. A
lost commit acknowledgement returns `deferred` and withholds unconfirmed
authority. An expired persisted authorization is never returned as fresh and
the A.20 handoff validator refuses to consume it.

## Evidence and ATL-A.20 boundary

The authorization binds the A.26 enforcement digest, A.27 execution ID and
digest, A.28 verification ID and digest, A.29 settlement ID and digest, original
authorization reference, deterministic incident ID, response request and
idempotency identities, settlement status, exact response manifest and policy,
capability, scope, constraints, attempt limit, expiry, authorizer, digest, and
signature.

`create_atl_a20_handoff` independently verifies the authorization digest,
identity, signature, outcome, response class, and expiry. Only executable
`authorized` response types can become an A.20 handoff. Manual review evidence
cannot masquerade as executable remediation. Before translation, A.20 compares
every handoff field with the independently verified signed authorization, so a
caller cannot substitute a capability, scope, constraint, attempt limit, or
expiry. The resulting handoff can be translated into A.20's existing
`RemediationRequest`; A.30 never calls A.20's executor.

The public DTO exposes only safe IDs, normalized outcome/type/reason, expiry,
and commit/replay flags. It excludes policy internals, constraints, manifests,
lineage digests, signatures, commands, credentials, raw provider payloads, and
exceptions.

## Validation

```powershell
python -m pytest tests/test_reference_architecture_continued_operation_response.py -q
python -m pytest tests/test_reference_architecture_continued_operation_enforcement.py tests/test_reference_architecture_continued_operation_execution.py tests/test_reference_architecture_continued_operation_reconciliation.py tests/test_reference_architecture_continued_operation_settlement.py tests/test_reference_architecture_continued_operation_response.py -q
python scripts/check_repository_boundary.py
python scripts/check_public_export_boundary.py
python scripts/check_private_dependency_boundary.py
python -m pytest -m "not integration" -q
```

Implementation validation: **15 ATL-A.30 tests passed**; **128 focused A.26–A.30
tests passed**; **1,645 non-integration tests passed, 10 cross-repository tests
skipped, and 1 integration test deselected**; repository, public-export, and
private-dependency boundary checks passed.
