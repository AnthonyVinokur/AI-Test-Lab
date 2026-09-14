# ATL-A.02.01 — Conformance Evidence Intake Contract

## Status

**Implemented.**

## Objective

Define the first stable AI Test Lab public contract for the conformance-evidence
export produced by the frozen Aquagear A.43.4 boundary.

This slice answers one narrow question:

> What exact public evidence structure may enter AI Test Lab?

## Accepted contract

The envelope must contain exactly:

- schema `aquagear.reference-architecture-conformance-evidence`;
- export version `1`;
- one evidence object.

The evidence object must contain exactly:

- evidence schema version `1.0`;
- frozen architecture version `v1`;
- an opaque deterministic JSON evaluation object;
- a 64-character lowercase evaluation SHA-256 identity;
- a 64-character lowercase evidence SHA-256 identity.

The DTOs inherit `PublicContractModel`, reject undeclared fields, and are
recursively detached and immutable. The opaque evaluation object is preserved
without interpreting scores, verdicts, requirements, or governance meaning.

## Acceptance criteria

1. The exact Aquagear A.43.4 export shape is accepted.
2. Missing, extra, renamed, or future-version fields fail closed.
3. Digest identities must have the lowercase SHA-256 shape.
4. The evaluation value must be a deterministic JSON object.
5. Input mutation cannot change the accepted contract.
6. Nested accepted state cannot be mutated.
7. Approved public serialization returns a detached JSON-safe representation.
8. AI Test Lab does not import or execute Aquagear.

## Explicit non-goals

- JSON byte decoding or transport;
- recomputing or trusting either digest;
- semantic evaluation or conformance decisions;
- binding evidence to an A.01 round-trip response;
- persistence, signing, authentication, retries, or provider SDKs;
- governance, scoring, compliance, or enforcement logic;
- modification of the frozen Aquagear reference application.

## Verification

```powershell
python -m pytest `
  tests/test_reference_architecture_conformance_evidence_intake_contract.py `
  -q
```

## Repository placement

- `src/reference_architecture_conformance_evidence_intake_contract.py`
- `tests/test_reference_architecture_conformance_evidence_intake_contract.py`
- `docs/sprints/atl-a.02.md`
- `docs/sprints/atl-a.02.01.md`

## Suggested commit

```text
feat: add conformance evidence intake contract
```
