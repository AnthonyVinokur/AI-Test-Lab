# ATL-A.11 — Evidence Transparency and Equivocation Detection

ATL-A.11 adds a cryptographically verifiable, append-only transparency record over ATL-A.10 lifecycle
events. Canonical entry digests are committed to a Merkle tree. Authorized operators sign checkpoints;
independent verifiers can prove exact inclusion, append-only consistency, or conflicting same-size roots.

## Security boundary

The boundary binds every entry and checkpoint to one log and environment, requires explicit verification
time and exact authority, and fails closed on malformed documents, invalid signatures, altered proofs,
rollback, history rewriting, or cross-context substitution. Public outcomes expose only approved identifiers,
sizes, times, and stable reason categories. Entries contain references and digests, never evidence content.

Signatures prove origin and integrity, not factual correctness, AI safety, fairness, legal compliance, or
production readiness. The in-memory store and proof representation are deterministic reference components;
production deployments still require durable replicated storage, secure key custody, witness/gossip
distribution, trusted time inputs, and availability controls.

## Verification questions

1. Was this exact lifecycle entry included in this signed checkpoint?
2. Does the newer checkpoint preserve the earlier tree unchanged?
3. Did the operator sign conflicting roots for the same log, environment, and size?
