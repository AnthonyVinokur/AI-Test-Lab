# ATL-A.03.06 — Authenticated Provenance Failure Normalization

## Status

**Implemented.**

## Objective

Convert ordinary authenticated-provenance intake and verification failures into
one frozen, deterministic, redacted public contract while preserving successful
authenticated provenance internally.

## Normalization boundary

`authenticate_reference_architecture_provenance_with_normalized_failure`
performs the existing A.03 steps through one fail-closed boundary:

1. translate untrusted UTF-8 JSON with A.03.02;
2. require an A.03.05 caller-authorized signer-key binding;
3. verify producer identity, key reference, algorithm, and signature; and
4. return exactly one success or failure branch.

The frozen public failure DTO exposes only a stable stage, code, safe message,
non-retryable classification, and identifiers copied from an already validated
A.03.01 contract. It never exposes the input document, signature, public key,
canonical signing payload, exception text, traceback, or cryptographic details.

## Stable failure taxonomy

| Stage | Code | Meaning |
| --- | --- | --- |
| `document_translation` | `invalid_provenance_document` | Untrusted bytes could not enter A.03.01. |
| `binding_validation` | `invalid_signer_key_binding` | The caller did not supply the required A.03.05 binding type. |
| `authentication` | `authentication_failed` | Producer, key reference, algorithm, public key, or signature did not authenticate. |
| `authentication` | `provenance_verification_failed` | An unexpected ordinary verifier failure was safely redacted. |

All expected authentication mismatches intentionally share one public code and
message. A caller cannot use the failure response to distinguish whether the
producer, key ID, public key, or detached signature was wrong.

## Security properties

- Malformed and ambiguous provenance documents fail closed.
- Invalid caller API inputs become stable boundary failures.
- Identity, key-reference, key, and signature mismatches are indistinguishable.
- Unexpected ordinary exceptions cannot leak provider or cryptographic detail.
- Only identifiers from a structurally validated provenance contract may be
  reflected in a failure.
- Every normalized failure is non-retryable; retry policy remains outside this
  contract.
- `KeyboardInterrupt`, `SystemExit`, and other control-flow `BaseException`
  values are not swallowed.
- Public failures and internal success/failure results are immutable.

## Explicit non-goals

- key discovery, trust-store lookup, authorization, rotation, or revocation;
- changing A.03.02 translation or A.03.04/A.03.05 verification semantics;
- revealing which authentication comparison failed;
- evidence-digest binding to an A.02 outcome;
- freshness, expiry, replay, or attestation uniqueness decisions;
- persistence, transport, serialization orchestration, or proprietary scoring;
- deciding whether an operational failure should be retried.

## Acceptance criteria

1. A valid document and authorized signer-key binding return authenticated
   provenance without mutation.
2. Invalid document bytes return the frozen document-translation failure.
3. An invalid binding input returns the frozen binding-validation failure.
4. Producer, key-reference, public-key, and signature mismatches return the same
   safe authentication failure.
5. Unexpected verifier exceptions return a redacted verification failure.
6. Failure contracts contain no document, signature, public-key, payload, or
   exception detail.
7. The internal result requires exactly one of provenance or failure.
8. Control-flow exceptions remain outside ordinary failure normalization.

## Verification

```powershell
python -m pytest `
  tests/test_reference_architecture_authenticated_provenance_contract.py `
  tests/test_reference_architecture_authenticated_provenance_document_translation.py `
  tests/test_reference_architecture_authenticated_provenance_signing_payload.py `
  tests/test_reference_architecture_authenticated_provenance_signature_verification.py `
  tests/test_reference_architecture_authenticated_provenance_signer_key_binding.py `
  tests/test_reference_architecture_authenticated_provenance_failure_normalization.py `
  -q

python -m pytest -q
```

## Repository placement

- `src/reference_architecture_authenticated_provenance_failure_normalization.py`
- `tests/test_reference_architecture_authenticated_provenance_failure_normalization.py`
- `docs/sprints/atl-a.03.06.md`

## Suggested commit

```text
feat: normalize authenticated provenance failures
```
