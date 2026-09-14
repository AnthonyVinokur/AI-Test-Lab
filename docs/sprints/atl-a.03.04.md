# ATL-A.03.04 — Ed25519 Signature Verification

## Status

**Implemented.**

## Objective

Verify that an ATL-A.03 authenticated-provenance document carries a valid
detached Ed25519 signature over the exact canonical bytes frozen in A.03.03.

## Verification boundary

The verifier accepts two inputs:

1. an already validated, immutable A.03.01 provenance contract; and
2. the resolved raw 32-byte Ed25519 public key.

It reconstructs the A.03.03 canonical payload, decodes the contract's validated
64-byte signature, and delegates cryptographic verification to the pinned
`cryptography` implementation. It returns `True` for a valid signature and
`False` for an authentic cryptographic mismatch.

Malformed API inputs fail closed: a non-contract provenance value or non-byte
key raises `TypeError`, and a key with the wrong length raises `ValueError`.

## Security properties

- Any signed-claim change invalidates the signature.
- Changing `key_id` invalidates the signature because A.03.03 binds it.
- A different public key cannot validate the original signature.
- A modified signature cannot validate the original payload.
- The production module handles public keys only and contains no signing or
  private-key capability.
- Verification does not mutate the immutable public contract.

## Explicit non-goals

- resolving `key_id` to a public key;
- deciding whether a producer, key ID, or supplied key is trusted;
- key storage, rotation, revocation, certificates, or transport;
- evidence-digest binding to A.02 outcomes;
- freshness, expiration, replay prevention, or attestation uniqueness;
- proprietary governance, risk scoring, or trust policy.

## Acceptance criteria

1. A valid Ed25519 signature over the canonical A.03.03 payload verifies.
2. Changed claims, `key_id`, signature bytes, and public key fail verification.
3. The backend is checked against the RFC 8032 empty-message test vector.
4. Only raw 32-byte public keys are accepted.
5. Invalid signature results return `False` without hiding invalid API usage.
6. Verification leaves the input contract unchanged.
7. No private-key operation exists in the production verifier.

## Verification

```powershell
python -m pytest `
  tests/test_reference_architecture_authenticated_provenance_contract.py `
  tests/test_reference_architecture_authenticated_provenance_document_translation.py `
  tests/test_reference_architecture_authenticated_provenance_signing_payload.py `
  tests/test_reference_architecture_authenticated_provenance_signature_verification.py `
  -q

python -m pytest -q
```

## Repository placement

- `src/reference_architecture_authenticated_provenance_signature_verification.py`
- `tests/test_reference_architecture_authenticated_provenance_signature_verification.py`
- `docs/sprints/atl-a.03.04.md`

## Suggested commit

```text
feat: verify authenticated provenance Ed25519 signatures
```
