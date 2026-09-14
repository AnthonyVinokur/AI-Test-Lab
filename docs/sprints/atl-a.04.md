# ATL-A.04 — Provenance Trust Policy and Key Lifecycle

## Outcome

ATL-A.04 separates cryptographic authenticity from authorization. An ATL-A.03-authenticated provenance outcome becomes trusted only when an identified, versioned policy authorizes its signer, key, time, purpose, environment, algorithm, and key type.

## Invariants

- Trust evaluation is deterministic and fail closed.
- Evaluation time is explicit and normalized to UTC.
- Policies and their signer/key records are immutable after translation.
- The public outcome is frozen, strict, provider-neutral, and independently serialized.
- Private key material, provider objects, tracebacks, credentials, and proprietary authorization logic never cross the public boundary.
- ATL-A.01 through ATL-A.03 contracts remain unchanged.

## Slices

ATL-A.04.01 through ATL-A.04.10 are implemented together on the dedicated `atl-a04` branch. The focused acceptance suite covers trusted flow, all normalized rejection categories, boundary timestamps, malformed and ambiguous policies, immutability, deterministic serialization, and redaction.

## Non-goals

No CA infrastructure, TLS, key generation/storage/rotation, remote key fetching, persistence, UI, deployment authorization, governance scoring, evaluation-engine changes, or Aquagear changes are introduced.
