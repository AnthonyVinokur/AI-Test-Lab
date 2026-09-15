# ATL-A.13 — Authorized Deployment Approval and Release Attestation

ATL-A.13 converts one valid, satisfied ATL-A.12 attestation into narrowly scoped deployment authorization. It binds approval to the exact artifact and configuration, target tenant/environment/region/purpose, release identity, policy category, authorized approvers, conditions, and validity window.

The deterministic boundary enforces approver scope, risk and duration limits, separation of duties, unique-identity quorum, and required roles. Signed approval attestations and hash-linked lifecycle events detect substitution, condition removal, replay, revocation, supersession, rollback, and history fabrication. The safe public interface reveals only what an enforcement point needs.
