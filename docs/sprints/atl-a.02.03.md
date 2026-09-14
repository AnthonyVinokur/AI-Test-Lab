# ATL-A.02.03 — Evidence Integrity Verification

## Status

**Implemented.**

## Objective

Recompute and verify the two SHA-256 identities published inside an accepted
Aquagear A.43 conformance-evidence artifact.

This slice answers one narrow question:

> Does the accepted evidence still contain exactly the evaluation and evidence
> content that produced its published SHA-256 identities?

## Verification behavior

The verifier reproduces Aquagear A.43.3 canonicalization exactly:

1. serialize JSON with sorted keys and compact separators;
2. preserve Unicode and encode the canonical text as UTF-8;
3. recompute `evaluation_sha256` from `evaluation` alone;
4. recompute `evidence_sha256` from `schema_version`,
   `architecture_version`, `evaluation`, and the published
   `evaluation_sha256`;
5. compare both identities with `hmac.compare_digest()`; and
6. return `True` only when both identities match.

The outer A.43.4 transport envelope and `evidence_sha256` itself are not part of
the producer's evidence-digest input. Verification reads the immutable A.02.01
contract and does not alter it.

## Acceptance criteria

1. Untouched A.43.3 evidence verifies successfully.
2. Nested objects, sequences, numbers, booleans, nulls, and Unicode reproduce
   the producer's digest identities.
3. JSON object key order does not affect verification.
4. A changed evaluation fails verification.
5. A changed evaluation identity fails even if an attacker recalculates only
   the outer evidence identity.
6. A changed evidence identity fails verification.
7. Both identities must match; partial integrity never passes.
8. Verification does not mutate or reinterpret the intake contract.
9. Values outside the frozen A.02.01 intake type are rejected.

## Explicit non-goals

- semantic interpretation or reevaluation of conformance;
- architecture or contract compatibility decisions (ATL-A.02.04);
- A.01 correlation or round-trip evidence binding;
- signing, authentication, authorization, transport security, or persistence;
- accepting alternate hash algorithms or canonicalization formats;
- exposing proprietary scoring, governance, compliance, evidence-intelligence,
  or enforcement logic;
- importing, executing, or modifying Aquagear.

## Verification

```powershell
python -m pytest `
  tests/test_reference_architecture_conformance_evidence_intake_contract.py `
  tests/test_reference_architecture_conformance_evidence_document_translation.py `
  tests/test_reference_architecture_conformance_evidence_integrity_verification.py `
  -q
```

## Repository placement

- `src/reference_architecture_conformance_evidence_integrity_verification.py`
- `tests/test_reference_architecture_conformance_evidence_integrity_verification.py`
- `docs/sprints/atl-a.02.md`
- `docs/sprints/atl-a.02.03.md`

## Suggested commit

```text
feat: verify conformance evidence integrity
```
