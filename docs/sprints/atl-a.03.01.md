# ATL-A.03.01 — Provenance Contract

## Status

**Implemented.**

## Goal

Freeze the minimum public data required to authenticate which producer claims
to have created one A.02 conformance-evidence artifact. A.02 proved that bytes
were unchanged; this contract creates the explicit input for later A.03
authenticity verification.

## Public contract

`ReferenceArchitectureAuthenticatedProvenanceV1` is an immutable, strict
`PublicContractModel` with three sections:

1. frozen AI Test Lab contract identity and version;
2. public claims containing `attestation_id`, `producer_id`, the exact A.02
   `evidence_sha256`, and a canonical UTC `issued_at` timestamp;
3. a public proof containing the frozen `ed25519` algorithm, a `key_id`, and a
   canonical base64-encoded 64-byte signature.

Unknown, missing, malformed, non-canonical, and private fields fail closed.
Only the approved public serializer can export the model.

## Security and IP boundary

The contract carries a public producer claim, public key reference, and public
signature. It never carries:

- a private key, seed, credential, or secret;
- a trust score, allowlist decision, governance policy, or key-store state;
- provider runtime objects, transport details, tracebacks, or internal errors;
- prompts, model responses, metrics, or proprietary evidence intelligence.

The module is provider-neutral and has no Aquagear runtime, cryptographic
library, provider SDK, or HTTP-client dependency.

## Deliberate non-goals

ATL-A.03.01 does not:

- define the canonical bytes covered by the signature;
- verify the Ed25519 signature;
- resolve or trust `producer_id` or `key_id`;
- bind the provenance to a completed A.02 outcome;
- enforce timestamp freshness or replay prevention;
- parse untrusted JSON, persist keys, or provide transport security.

Those behaviors require separate, reviewable A.03 slices. A structurally valid
contract is therefore an unverified claim, not proof that a producer is trusted.

## Verification

```powershell
python -m pytest `
  .\tests\test_reference_architecture_authenticated_provenance_contract.py `
  -q

python -m pytest -q
```

## Repository placement

- `src/reference_architecture_authenticated_provenance_contract.py`
- `tests/test_reference_architecture_authenticated_provenance_contract.py`
- `docs/sprints/atl-a.03.01.md`

## Suggested commit

```text
feat: define authenticated provenance contract
```
