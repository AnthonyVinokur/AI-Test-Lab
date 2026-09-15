# ATL-A.06 — Trusted Evidence Ledger and Chain of Custody

ATL-A.06 converts a successful ATL-A.05 admission into durable, provider-neutral,
tamper-evident history. An internal admission authorization binds the admitted evidence
to its digest, producer, provenance, run, policy, and contract versions. The ledger then
assigns deterministic logical identity and append-only order, links superseding entries,
and returns an explicitly projected public outcome.

The reference storage adapter is intentionally in-memory. Its behavioral contract—not
its storage mechanism—is architectural: accepted entries cannot be overwritten, retries
are idempotent, competing histories fail closed, and every chain can be verified.

## Public versus internal boundary

Public contracts contain only status, stable reason code, ledger/chain identity,
sequence, evidence digest, run identity, recorded time, and verification state. Admission
authorizations, canonicalization, chain construction, indexes, policy objects, signer
details, and storage state remain internal.

## Closed flow

`admission authorization → strict translation → exact binding → deterministic identity → conflict checks → append → verification → public projection`

The next boundary is ATL-A.07: policy-controlled consumption and lifecycle rules for
ledger evidence. Quality scoring, compliance interpretation, and proprietary evidence
intelligence remain outside this public architecture.
