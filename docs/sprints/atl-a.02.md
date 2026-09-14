# ATL-A.02 — Reference Conformance Evidence Intake

## Purpose

Allow AI Test Lab to receive the frozen Aquagear A.43 conformance-evidence
export through an explicit, provider-neutral, fail-closed boundary.

ATL-A.02 consumes only the public artifact already returned by the closed A.01
round trip. It does not import or execute Aquagear and does not expose AI Test
Lab's proprietary scoring, governance, evidence-intelligence, or enforcement
implementation.

## Planned sequence

1. **ATL-A.02.01 — Conformance Evidence Intake Contract:** freeze the exact
   public envelope and evidence shape accepted from Aquagear A.43.4.
2. **ATL-A.02.02 — Untrusted Evidence Document Translation:** decode and
   fail-closed validate untrusted evidence bytes into the A.02.01 contract.
3. **ATL-A.02.03 — Evidence Integrity Verification:** recompute and verify the
   published evaluation and evidence SHA-256 identities.
4. **ATL-A.02.04 — Evidence Compatibility Verification:** verify that the
   evidence targets the supported frozen architecture and conformance contract.
5. **ATL-A.02.05 — Round-Trip Evidence Binding:** bind accepted evidence to the
   successful A.01 response carrying it without weakening correlation rules.
6. **ATL-A.02.06+ — Normalization, public outcome, serialization, and closure:**
   define stable failures and a minimal public result before freezing A.02.

Every later slice requires its own narrow contract and tests. The planned
sequence does not pre-approve new public fields or proprietary behavior.

