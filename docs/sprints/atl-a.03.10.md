# ATL-A.03.10 — Integrated Threat Review and A.03 Closure

## Status

**Implemented. A.03 closed.**

## Threat review

| Threat | Control | Residual boundary |
| --- | --- | --- |
| Malformed or ambiguous JSON | Strict UTF-8 translation, duplicate-key rejection, frozen schemas | Input-size/rate limits belong to transport. |
| Claim or digest tampering | Canonical payload plus Ed25519 verification | Compromised signing keys require operational revocation. |
| Signer/key substitution | Caller-authorized producer and key-reference binding | Key discovery and authorization policy remain external. |
| Verification oracle | Authentication mismatches share a redacted failure | Timing hardening belongs to deployment infrastructure. |
| Secret/internal leakage | Explicit public projection and strict A.03.08 schema | Logs must follow the same redaction policy. |
| Schema confusion | Literal contract names/versions and forbidden extras | Future versions require new explicit contracts. |
| Replay or stale attestation | Canonical `attestation_id` and `issued_at` are authenticated | Replay store and freshness policy are deliberately deferred. |
| Evidence substitution | `evidence_sha256` is authenticated | Resolving and comparing the referenced A.02 evidence is a later boundary. |

## Closure decision

A.03 now provides a complete, deterministic authenticated-provenance boundary:
contract, untrusted translation, canonical signing payload, Ed25519 verification,
signer/key-reference binding, safe failure normalization, public outcome,
canonical serialization, and integrated adversarial regression coverage.

The closure test mutates producer identity, evidence digest, and key reference,
and confirms every attack fails closed without revealing signatures, keys,
canonical payloads, or tracebacks.

## Explicitly deferred

- trust-store discovery, certificate chains, key rotation and revocation;
- replay detection, uniqueness persistence, expiry and clock policy;
- fetching and binding the authenticated digest to stored A.02 evidence;
- transport authentication, rate limits, audit storage, governance scoring;
- proprietary evidence intelligence and commercial orchestration.

## Verification

`tests/test_reference_architecture_authenticated_provenance_threat_closure.py`
