# ATL-A.07 — Verifiable Evidence Packages and Audit Export

ATL-A.07 turns one verified ATL-A.06 evidence chain into a deterministic, portable,
UTF-8 JSON package. An authorized consumer can verify the package offline using only
its public contents. Verification proves that the declared records are complete,
ordered, admission-bound, run-bound, and unchanged; it does not certify that an AI
answer is correct, safe, compliant, or production-approved.

## Closed flow

`untrusted selection → strict translation → authorization → verified ledger chain → allowlisted projection → canonical manifest → deterministic JSON → offline verification → normalized outcome`

## Public boundary

The public package exposes stable identifiers, evidence and entry digests, chain links,
run and admission references, provenance references, contract versions, and recorded
times already present in the trusted ledger. It never serializes internal ledger,
authorization, policy, scoring, governance, storage, key-material, or orchestration
objects.

Version 1.0 packages one complete chain prefix. In this reference architecture the
public `ledger_id` is the A.06 `chain_id`; this preserves a self-contained proof without
inventing a storage-vendor ledger identifier. Later storage adapters may map the same
public contract to a durable ledger namespace.

## Security properties

- Same request and ledger state produce identical bytes and digests.
- The verifier accepts the public package, not private runtime objects.
- Canonical JSON is UTF-8, sorted, compact, finite, and platform-independent.
- Partial selections that omit a required predecessor fail closed.
- Expected failures return stable reason codes and no exception or secret details.
- Package identity contains no build clock or other volatile value.

## Closure

All ten slices are delivered together by the public contracts, translation boundary,
builder, serialization helpers, verifier, in-memory A.06 adapter integration, tampering
tests, and per-slice documentation. Proprietary evidence intelligence and compliance
interpretation remain protected future capabilities.
