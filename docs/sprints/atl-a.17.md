# ATL-A.17 — Trusted Deployment Outcome Verification and Reconciliation

ATL-A.17 converts a verified ATL-A.16 execution attestation into an immutable answer about the
actual deployed state. The expected artifact, release, provider, environment, and healthy-state
requirement are derived solely from verified evidence and policy; callers cannot replace them.
An explicitly registered observer is observation-only and returns a sanitized provider-neutral fact.

Only a fresh observation with exact identity and required health is `verified`. Contradictions are
`mismatch`, incomplete or unavailable observations are `indeterminate`, and invalid evidence or
bindings are `invalid`. The capability never executes, retries, remediates, or rolls back a deployment.

## Slices

- `.01` verified execution-attestation intake
- `.02` canonical expected-state projection
- `.03` observer-only provider-neutral port
- `.04` allowlisted observer resolution
- `.05` explicit evidence-time and freshness policy
- `.06` normalized safe observation model
- `.07` deterministic reconciliation
- `.08` atomic claim and idempotent replay
- `.09` immutable verification attestation
- `.10` safe public projection and compatibility
