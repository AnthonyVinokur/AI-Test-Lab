# ATL-A.03.07 — Public Provenance Verification Outcome

## Status

**Implemented.**

## Objective

Project the internal A.03.06 authentication result into one immutable public
success-or-failure contract without exposing signatures, public keys, canonical
payloads, bindings, exceptions, or verifier implementation details.

## Boundary

Success exposes only the authenticated attestation ID, producer ID, evidence
SHA-256 digest, issue time, key reference, and algorithm. Failure reuses the
redacted A.03.06 failure contract. Exactly one branch must exist and `succeeded`
must agree with it.

## Security and IP properties

- Public DTOs are explicit frozen models, not serialized internal objects.
- Authentication proof material and caller-resolved key bindings stay internal.
- Failed authentication never produces a success DTO.
- Failure projection is detached and deterministic.
- Trust discovery, authorization policy, replay prevention, scoring, and
  governance remain outside this public contract.

## Verification

`tests/test_reference_architecture_authenticated_provenance_outcome.py`

## Repository placement

- `src/reference_architecture_authenticated_provenance_outcome.py`
- `tests/test_reference_architecture_authenticated_provenance_outcome.py`
