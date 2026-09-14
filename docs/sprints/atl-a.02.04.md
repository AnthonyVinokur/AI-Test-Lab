# ATL-A.02.04 — Evidence Compatibility Verification

## Status

**Implemented.**

## Objective

Verify that accepted Aquagear conformance evidence declares the exact frozen
architecture and conformance contract supported by AI Test Lab.

This slice answers one narrow question:

> Does this evidence target the public contract that AI Test Lab deliberately
> supports?

## Verification behavior

The verifier compares the evidence target fields with the authoritative A.01
compatibility contract:

| Evidence field | Required value | Meaning |
|---|---|---|
| `architecture_version` | `v1` | Frozen Aquagear reference architecture |
| `schema_version` | `1.0` | Reference-architecture conformance contract |

An exact match returns `ReferenceArchitectureCompatibility.EXACT`. Any
unsupported or unrecognized target returns `INCOMPATIBLE`.

The current policy declares no cross-version compatibility, so the verifier
never infers compatibility from matching major versions, adjacent versions, or
similar strings. `COMPATIBLE` is reserved for a future explicitly approved
relationship.

## Acceptance criteria

1. Evidence targeting architecture `v1` and conformance contract `1.0` is
   classified as `EXACT`.
2. A different architecture version is `INCOMPATIBLE`.
3. A different conformance-contract version is `INCOMPATIBLE`.
4. Multiple mismatches remain `INCOMPATIBLE`.
5. No undeclared cross-version relationship produces `COMPATIBLE`.
6. A malformed nested evidence object fails closed.
7. Values outside the frozen A.02.01 intake type are rejected.
8. Compatibility does not reinterpret or replace A.02.03 integrity results.

## Separation from integrity

Integrity and compatibility answer different questions:

- **A.02.03 integrity:** do the published SHA-256 identities match the content?
- **A.02.04 compatibility:** does the content name the supported frozen target?

Neither decision implies the other. A later orchestration slice must require
both gates before evidence is accepted.

## Explicit non-goals

- recomputing evidence digests;
- reevaluating whether Aquagear actually conforms;
- inspecting proprietary evaluation or scoring logic;
- inferring compatibility for unpublished contract versions;
- binding evidence to an A.01 round-trip response (ATL-A.02.05);
- importing, executing, or modifying Aquagear.

## Verification

```powershell
python -m pytest `
  tests/test_reference_architecture_conformance_evidence_intake_contract.py `
  tests/test_reference_architecture_conformance_evidence_document_translation.py `
  tests/test_reference_architecture_conformance_evidence_integrity_verification.py `
  tests/test_reference_architecture_conformance_evidence_compatibility_verification.py `
  -q
```

## Repository placement

- `src/reference_architecture_conformance_evidence_compatibility_verification.py`
- `tests/test_reference_architecture_conformance_evidence_compatibility_verification.py`
- `docs/sprints/atl-a.02.md`
- `docs/sprints/atl-a.02.04.md`

## Suggested commit

```text
feat: verify conformance evidence compatibility
```
