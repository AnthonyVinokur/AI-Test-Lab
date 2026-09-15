# ATL-A.08.08 — Deterministic Consumption Decision Engine

Implements fixed fail-closed precedence: validate request, resolve requester and policy,
validate policy time, resolve and verify ledger evidence, enforce complete selection and
scope, authorize purpose/environment/type, apply lifecycle and holds, then retention.
Unexpected errors can never authorize construction.
