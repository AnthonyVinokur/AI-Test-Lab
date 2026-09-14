# ATL-A.02 — Reference Conformance Evidence Intake

## Status

**Closed by ATL-A.02.10.** The public boundary is frozen under the change-control
rules documented in the closure sprint.

## Purpose

Allow AI Test Lab to receive the frozen Aquagear A.43 conformance-evidence
export through an explicit, provider-neutral, fail-closed boundary.

ATL-A.02 consumes only the public artifact already returned by the closed A.01
round trip. It does not import or execute Aquagear and does not expose AI Test
Lab's proprietary scoring, governance, evidence-intelligence, or enforcement
implementation.

## Completed sequence

1. **ATL-A.02.01 — Conformance Evidence Intake Contract:** froze the exact
   public envelope and evidence shape accepted from Aquagear A.43.4.
2. **ATL-A.02.02 — Untrusted Evidence Document Translation:** strictly decodes
   untrusted UTF-8 JSON into the frozen intake contract.
3. **ATL-A.02.03 — Evidence Integrity Verification:** reproduces canonical JSON
   inputs and verifies both published SHA-256 identities.
4. **ATL-A.02.04 — Evidence Compatibility Verification:** enforces exact
   architecture and conformance-contract compatibility.
5. **ATL-A.02.05 — Round-Trip Evidence Binding:** accepts evidence only from a
   completed, correlated A.01 response after all preceding checks.
6. **ATL-A.02.06 — Evidence Binding Failure Normalization:** maps ordinary
   rejections to stable, immutable, redacted public failures.
7. **ATL-A.02.07 — Public Evidence-Binding Outcome:** freezes the minimal public
   success-or-failure envelope.
8. **ATL-A.02.08 — Public Evidence-Binding Serialization Boundary:** emits and
   decodes deterministic compact UTF-8 JSON for the frozen outcome.
9. **ATL-A.02.09 — End-to-End Evidence-Binding Regression Verification:**
   exercises the complete provider-neutral success, rejection, tampering, and
   IP-boundary paths.
10. **ATL-A.02.10 — Integrated Threat Review and A.02 Closure:** closes JSON
    ambiguity, verifies integrated threat controls, records residual risks, and
    freezes A.02 under explicit change control.

## Closure rule

A change to an A.02 public field, literal, version, error mapping, canonical
wire shape, digest input, compatibility rule, binding rule, or dependency
boundary requires a named follow-up architecture sprint, compatibility and
threat analysis, and an explicit versioning decision.

Internal refactoring is permitted only while the A.02 closure suite and the
complete repository suite remain green.
