# ATL-A.03.03 — Canonical Provenance Signing Payload

## Status

**Implemented.**

## Objective

Define the one deterministic byte sequence covered by an ATL-A.03 provenance
signature. Equivalent A.03.01 contracts now produce identical signing bytes on
every conforming producer or verifier.

## Canonical payload

The payload is a compact, key-sorted UTF-8 JSON object containing:

1. the frozen provenance `contract_name` and `contract_version`;
2. every public claim: `attestation_id`, `producer_id`, `evidence_sha256`, and
   `issued_at`; and
3. the proof's frozen `algorithm` and public `key_id`.

`signature_base64` is excluded because it is the detached signature produced
*from* these bytes. Its exclusion also lets a verifier reconstruct the exact
payload without circular input.

Unicode is encoded directly as UTF-8, object keys are sorted, insignificant
whitespace is removed, and non-standard numeric values are forbidden. The
function returns immutable `bytes` rather than text or a mutable object.

## Security properties

The payload binds the producer claim, evidence digest, timestamp, attestation
identity, algorithm, key reference, and contract identity together. A change to
any of these fields creates different bytes and therefore cannot reuse a valid
signature over the original payload.

The implementation accepts only the already validated, immutable A.03.01
contract. It does not accept arbitrary dictionaries and does not expose or use
private keys, trust stores, provider runtimes, or proprietary policy.

## Acceptance criteria

1. Equivalent A.03.01 contracts produce byte-for-byte identical payloads.
2. The exact compact, sorted, UTF-8 JSON representation is frozen by a test.
3. Every variable claim and `key_id` changes the payload independently.
4. Contract identity, version, algorithm, and key reference are included.
5. `signature_base64` is excluded and changing it does not change the payload.
6. Unicode public identities use deterministic UTF-8 rather than JSON escapes.
7. Payload construction does not mutate the provenance contract.
8. Non-A.03.01 inputs fail closed with `TypeError`.

## Explicit non-goals

- generating or verifying an Ed25519 signature;
- resolving or trusting `producer_id` or `key_id`;
- binding provenance to a completed A.02 outcome;
- enforcing timestamp freshness or replay prevention;
- key storage, rotation, revocation, transport security, or persistence;
- exposing governance, trust-scoring, evidence-intelligence, or other
  proprietary internals.

## Verification

```powershell
python -m pytest `
  tests/test_reference_architecture_authenticated_provenance_contract.py `
  tests/test_reference_architecture_authenticated_provenance_document_translation.py `
  tests/test_reference_architecture_authenticated_provenance_signing_payload.py `
  -q

python -m pytest -q
```

## Repository placement

- `src/reference_architecture_authenticated_provenance_signing_payload.py`
- `tests/test_reference_architecture_authenticated_provenance_signing_payload.py`
- `docs/sprints/atl-a.03.03.md`

## Suggested commit

```text
feat: define canonical provenance signing payload
```
