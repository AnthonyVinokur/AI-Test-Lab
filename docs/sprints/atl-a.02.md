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
2. **ATL-A.02.02 — Untrusted Evidence Document Translation:** implemented;
   strict UTF-8 JSON decoding rejects ambiguous input and fail-closed validates
   untrusted evidence bytes into the A.02.01 contract.
3. **ATL-A.02.03 — Evidence Integrity Verification:** implemented; reproduces
   Aquagear's canonical JSON inputs and requires both published evaluation and
   evidence SHA-256 identities to match.
4. **ATL-A.02.04 — Evidence Compatibility Verification:** implemented; applies
   the A.01 exact-version policy to the evidence targets and fails closed for
   every undeclared architecture or conformance-contract version.
5. **ATL-A.02.05 — Round-Trip Evidence Binding:** implemented; extracts the
   evidence artifact only from a completed, correlated A.01 result and accepts
   it only after frozen transport, document, integrity, and exact-compatibility
   verification.
6. **ATL-A.02.06 — Evidence Binding Failure Normalization:** implemented;
   converts every ordinary A.02.05 rejection into an immutable, redacted public
   failure with a stable stage, code, message, retryability, and safe response
   identifiers.
7. **ATL-A.02.07 — Public Evidence-Binding Outcome:** implemented; projects the
   normalized result into a frozen success-or-failure public envelope. Success
   exposes only safe response identifiers and the verified A.02.01 evidence;
   failure exposes only the redacted A.02.06 DTO.
8. **ATL-A.02.08 — Public Evidence-Binding Serialization Boundary:**
   implemented; revalidates the A.02.07 DTO, emits deterministic compact UTF-8
   JSON, and fail-closed decodes only the frozen public schema.
9. **ATL-A.02.09 — End-to-End Evidence-Binding Regression Verification:**
   implemented; exercises the complete provider-neutral round trip through
   evidence binding, failure normalization, public projection, and canonical
   wire decoding across success, rejection, tampering, and IP-boundary cases.
10. **ATL-A.02.10+ — Threat review and closure:** review the integrated boundary
    and freeze A.02.

Every later slice requires its own narrow contract and tests. The planned
sequence does not pre-approve new public fields or proprietary behavior.
