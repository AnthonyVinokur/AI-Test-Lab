# ATL-A.02.02 — Untrusted Evidence Document Translation

## Status

**Implemented.**

## Objective

Create the fail-closed boundary that converts an untrusted Aquagear evidence
document into the frozen ATL-A.02.01 intake contract.

This slice answers one narrow question:

> Can these external bytes be decoded without ambiguity and validated as the
> exact evidence structure AI Test Lab accepts?

## Translation behavior

The translator:

1. accepts only a `bytes` document;
2. decodes strict UTF-8;
3. parses one JSON document;
4. rejects non-standard JSON numbers and duplicate keys at every depth;
5. requires the JSON root to be an object; and
6. validates that object directly into the immutable ATL-A.02.01 contract.

Every decoding, parsing, ambiguity, root-shape, or contract-validation failure
is closed behind one stable public translation error. Parsed state is detached
from the caller and recursively immutable through the A.02.01 DTO.

## Acceptance criteria

1. A valid Aquagear A.43.4 UTF-8 JSON document translates successfully.
2. Invalid UTF-8, malformed JSON, empty input, and non-object roots fail closed.
3. Duplicate keys at the envelope or nested evaluation level fail closed.
4. `NaN` and infinity values are rejected as non-standard JSON.
5. Missing, extra, unsupported-version, and malformed contract fields fail
   behind the translation error.
6. Text, byte arrays, memory views, and other non-`bytes` inputs are rejected.
7. Successful output is exactly the frozen A.02.01 contract and remains
   recursively immutable.
8. Translation does not claim that either published digest is correct.

## Explicit non-goals

- recomputing or comparing digest identities (ATL-A.02.03);
- semantic interpretation of evaluation contents;
- compatibility decisions beyond the frozen A.02.01 structure;
- A.01 round-trip correlation or evidence binding;
- persistence, transport, authentication, signing, retries, or provider SDKs;
- proprietary scoring, governance, compliance, evidence-intelligence, or
  enforcement logic;
- importing, executing, or modifying Aquagear.

## Verification

```powershell
python -m pytest `
  tests/test_reference_architecture_conformance_evidence_intake_contract.py `
  tests/test_reference_architecture_conformance_evidence_document_translation.py `
  -q
```

## Repository placement

- `src/reference_architecture_conformance_evidence_document_translation.py`
- `tests/test_reference_architecture_conformance_evidence_document_translation.py`
- `docs/sprints/atl-a.02.md`
- `docs/sprints/atl-a.02.02.md`

## Suggested commit

```text
feat: translate untrusted conformance evidence documents
```
