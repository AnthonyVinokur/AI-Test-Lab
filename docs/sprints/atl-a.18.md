# ATL-A.18 — Trusted Deployment Continuous Integrity Monitoring and Trust Revocation

ATL-A.18 establishes an immutable baseline only from a verified A.16 execution attestation and
a verified A.17 reconciliation. The retained tenant and configuration-digest bindings complete the
baseline, allowing later observations to prove whether the deployed release is still the same
authorized, reconciled release.

Every observation and result has canonical SHA-256 identity and an explicit evaluation time.
Missing evidence becomes `indeterminate`; malformed or tampered evidence becomes `invalid`;
inactive authorization or any artifact, release, tenant, environment, or configuration difference
becomes `untrusted`. Only exact active bindings remain `trusted`. Public reason categories and
remediation signals never disclose raw configuration, provider data, credentials, or policy logic.

## Slices

- `.01` strict frozen DTOs and safe remediation signals
- `.02` verified reconciliation-derived immutable baseline
- `.03` artifact and release binding checks
- `.04` tenant, environment, and configuration binding checks
- `.05` active, expired, revoked, superseded, and unavailable authorization handling
- `.06` deterministic drift classes
- `.07` fail-closed trust derivation
- `.08` safe revocation records
- `.09` canonical serialization and tamper verification
- `.10` unit, regression, negative-path, and architecture coverage
