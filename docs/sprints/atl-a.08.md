# ATL-A.08 — Evidence Consumption Policy and Lifecycle Enforcement

ATL-A.08 places a fail-closed disclosure guard in front of the ATL-A.07 evidence
package builder. A package can be constructed only after an immutable request has
passed requester, policy, ledger, scope, purpose, environment, lifecycle, retention,
and hold checks at one explicitly supplied trusted evaluation time.

## Closed flow

`untrusted request → strict translation → requester resolution → policy resolution → verified ledger selection → scope and lifecycle evaluation → exact A.07 authorization → normalized outcome`

## Boundary guarantees

- ATL-A.06 history is read and verified, never deleted, rewritten, or reordered.
- A.07 cryptographic records are never redacted to manufacture an incomplete proof.
- Authentication remains external; the evaluator consumes a trusted requester identity.
- Expected denials expose stable reason codes, policy references, and safe evidence IDs only.
- Credentials, role mappings, policy trees, hold explanations, storage details, stack traces,
  governance logic, and proprietary scoring never enter the public outcome.
- Expiration governs future exports and cannot erase packages already disclosed.
- Holds preserve eligible evidence for allowed investigations but do not imply approval.

## Closure

All ten slices are delivered together through immutable contracts, strict translation,
replaceable in-memory ports, deterministic evaluation, A.07 callback integration,
attack-oriented tests, and per-slice documentation. Compliance, safety, fairness, and
release-approval interpretation remain outside this reference boundary.
