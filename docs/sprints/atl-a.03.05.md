# ATL-A.03.05 — Signer Identity and Key-Reference Binding

## Status

**Implemented.**

## Objective

Require an ATL-A.03 authenticated-provenance signature to verify through an
explicit caller-authorized binding between the declared producer identity, the
declared key reference, the frozen algorithm, and the resolved public key.

## Binding boundary

The immutable `ReferenceArchitectureResolvedSignerKeyBindingV1` contains only:

1. the authorized `producer_id`;
2. the authorized `key_id`;
3. the frozen `ed25519` algorithm; and
4. the resolved raw 32-byte Ed25519 public key.

The A.03.05 verifier first requires exact equality between the provenance and
the binding's producer, key reference, and algorithm. Only then does it invoke
the A.03.04 signature verifier with the binding's public key.

The binding is supplied by the caller. AI Test Lab does not infer trust from a
key name, accept a key merely because it validates a signature, or claim that a
producer owns a key.

## Security properties

- A valid signature is insufficient when the producer is not authorized for
  the resolved binding.
- A valid signature is insufficient under a different key reference.
- A matching identity and key reference are insufficient when the public key
  does not validate the canonical A.03.03 payload.
- The signed payload already includes `producer_id`, `key_id`, and `algorithm`,
  so successful verification cryptographically protects the matched metadata.
- Both provenance and resolved binding remain immutable and unmodified.
- Production code handles public keys only and exposes no signing capability.

## Explicit non-goals

- discovering or resolving a `key_id`;
- deciding which producer or key should be trusted;
- trust-store, certificate, network, provider, or transport integration;
- private-key handling or signature generation;
- key rotation, revocation, expiry, or historical-key policy;
- evidence-digest binding to a completed A.02 outcome;
- freshness, replay, or attestation uniqueness decisions;
- public authenticity outcomes, serialization, or proprietary risk scoring.

## Acceptance criteria

1. A matching authorized binding and valid signature verify.
2. Producer substitution fails even when the same public key is supplied.
3. Key-reference substitution fails even when the same public key is supplied.
4. A different public key fails for otherwise matching metadata.
5. Binding identities, algorithm, and public-key shape are strictly validated.
6. Binding and provenance inputs are immutable and remain unchanged.
7. Invalid API inputs fail closed with explicit errors.
8. No private-key capability exists in the production module.

## Verification

```powershell
python -m pytest `
  tests/test_reference_architecture_authenticated_provenance_contract.py `
  tests/test_reference_architecture_authenticated_provenance_document_translation.py `
  tests/test_reference_architecture_authenticated_provenance_signing_payload.py `
  tests/test_reference_architecture_authenticated_provenance_signature_verification.py `
  tests/test_reference_architecture_authenticated_provenance_signer_key_binding.py `
  -q

python -m pytest -q
```

## Repository placement

- `src/reference_architecture_authenticated_provenance_signer_key_binding.py`
- `tests/test_reference_architecture_authenticated_provenance_signer_key_binding.py`
- `docs/sprints/atl-a.03.05.md`

## Suggested commit

```text
feat: bind authenticated provenance signer identities to keys
```
