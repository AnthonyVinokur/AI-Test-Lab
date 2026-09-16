# ATL-A.29 — Protected-Operation Outcome Settlement and Lifecycle Finalization

## Purpose

ATL-A.29 converts one authoritative, committed ATL-A.28 reconciliation into the
single durable lifecycle conclusion for that protected operation. It revalidates
the A.26 consumption, A.27 execution, and A.28 verification lineage; applies an
explicit versioned settlement policy; and atomically records immutable signed
settlement evidence.

The trusted chain is now:

`A.25 authorization → A.26 consumption → A.27 execution → A.28 independent verification → A.29 authoritative settlement`

A.29 does not invoke or retry the operation, observe provider state, repair a
mismatch, roll back, compensate, restore consumed authorization, or resolve an
incident.

## Implemented slices

| Slice | Implementation |
| --- | --- |
| ATL-A.29.1 | Frozen versioned request, policy, authoritative-source, status, reason, result, evidence, claim, signer, repository-port, and safe public DTO contracts with strict validation. |
| ATL-A.29.2 | Repository-only A.28 admission with attestation digest verification, freshness, verification-policy allowlisting, exact lifecycle binding, and complete A.26/A.27 lineage verification. |
| ATL-A.29.3 | Deterministic `verified → settled_success`, `mismatch → settled_failure`, `indeterminate → suspended`, and `invalid → rejected` mapping. Policy may suspend a nonterminal mismatch but cannot promote mismatch, indeterminate, stale, or invalid evidence to success. |
| ATL-A.29.4 | Thread-safe and SQLite repositories with one unique lifecycle winner, globally unique request identity, exact replay, conflicting-request rejection, immutable commit, and recoverable pending/committed states. |
| ATL-A.29.5 | Domain-separated canonical evidence identity, SHA-256 digest, injected signer port, reference HMAC signer, immutable timestamp, and allowlisted public projection. |
| ATL-A.29.6 | Mapping, lineage, tamper, staleness, policy, retry, concurrency, durable recovery, interrupted write, unknown commit, injection, redaction, and immutability tests. |
| ATL-A.29.7 | Architecture boundary, decision table, threat model, recovery guarantees, validation commands, and changelog. |

## Settlement decision table

| Admitted A.28 outcome | Default settlement | Meaning |
| --- | --- | --- |
| `verified` | `settled_success` | The independently observed state satisfies the required postcondition. |
| `mismatch` | `settled_failure` | Authoritative observation contradicts the required postcondition. |
| `indeterminate` | `suspended` | The lifecycle cannot safely be finalized as success or failure. |
| `invalid` | `rejected` | A valid A.28 attestation records that verification was inadmissible. |

An invalidly signed, altered, substituted, or incorrectly bound A.28 record is
rejected before settlement and produces no committed settlement evidence. A
cryptographically valid A.28 attestation whose recorded outcome is `invalid`
produces a durable `rejected` settlement. This preserves the distinction between
an authoritative rejection and an untrusted settlement request.

## Atomicity and recovery

The uniqueness key is the domain-separated digest of deployment, operation,
execution, and verification identifiers. The request identifier is also globally
unique. The first valid claim wins. The same request and canonical digest replays
the committed record; any changed request or competing request for the same
lifecycle returns `CONFLICTING_SETTLEMENT` and cannot overwrite it.

SQLite uses `BEGIN IMMEDIATE`, primary-key and unique constraints, write-ahead
logging, and a compare-before-update commit. A durable row with no result is an
interrupted/uncommitted settlement and recovers as `in_progress`, never as
success. A lost commit acknowledgement returns `suspended` with
`SETTLEMENT_COMMIT_INDETERMINATE` and withholds the unconfirmed evidence. The
durable record—not the transient API response—is authoritative.

## Evidence and public boundary

Settlement evidence binds the exact A.26 enforcement digest, A.27 execution
attestation digest, A.28 reconciliation ID and digest, lifecycle identifiers,
policy ID/version, status, reason, and settlement time. Its canonical digest is
domain-separated and signed through an injected signer port. The included HMAC
adapter is a deterministic reference; production deployments should supply a
managed-key signer.

The public DTO exposes only settlement and lifecycle identifiers, status, stable
reason, settlement time, and commit/replay flags. It excludes authorization
artifacts, enforcement/execution/verification digests, signatures, credentials,
provider output, observations, internal exceptions, and policy internals.

## Threat model and guarantees

- A caller cannot supply an A.28 object, status, A.27 attestation, or A.26 artifact;
  all authority is resolved from trusted repositories.
- A.27 `succeeded` never selects settlement success; only an admitted A.28
  `verified` result can do so.
- Digest, identity, deployment, operation, execution, correlation, policy, or
  lineage substitution fails closed.
- Stale verification is durably suspended, never silently promoted.
- Policy cannot convert mismatch, indeterminate, invalid, or stale evidence to
  success and cannot bypass mandatory evidence needed to construct settlement.
- Concurrent writers cannot create two authoritative settlements.
- A.29 has no provider adapter or observer and cannot mutate external state.

## Validation

```powershell
python -m pytest tests/test_reference_architecture_continued_operation_settlement.py -q
python -m pytest tests/test_reference_architecture_continued_operation_enforcement.py tests/test_reference_architecture_continued_operation_execution.py tests/test_reference_architecture_continued_operation_reconciliation.py tests/test_reference_architecture_continued_operation_settlement.py -q
python scripts/check_repository_boundary.py
python scripts/check_public_export_boundary.py
python scripts/check_private_dependency_boundary.py
python -m pytest -m "not integration" -q
```

Implementation validation: **15 ATL-A.29 tests passed**; **146 focused
A.25–A.29 tests passed**; **1,630 non-integration tests passed, 10
environment-dependent tests skipped, and 1 integration test deselected**;
repository, public-export, and private-dependency boundary checks passed.
