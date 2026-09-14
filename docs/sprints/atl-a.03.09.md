# ATL-A.03.09 — End-to-End Authenticated-Provenance Regression Verification

## Status

**Implemented.**

## Objective

Prove the integrated A.03 chain from untrusted provenance bytes through strict
translation, canonical-payload verification, signer/key binding, normalized
failure, public projection, and canonical public serialization.

## Regression coverage

- A valid Ed25519-signed document authenticates and round-trips publicly.
- Mutation of authenticated evidence claims fails closed.
- A wrong authorized public key fails closed.
- Malformed input remains a safe public failure.
- Neither success nor failure wire documents reveal signatures or public keys.

This sprint verifies existing components; it does not add key discovery,
revocation, replay storage, freshness policy, evidence-digest lookup, or
commercial governance logic.

## Verification

`tests/test_reference_architecture_authenticated_provenance_end_to_end.py`
