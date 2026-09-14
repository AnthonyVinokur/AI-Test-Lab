# ATL-A.03.02 — Untrusted Provenance Document Translation

## Status

**Implemented.**

## Objective

Create the fail-closed boundary that converts one untrusted authenticated-
provenance document into the frozen ATL-A.03.01 contract.

This slice answers one narrow question:

> Can these external bytes be decoded without ambiguity and validated as the
> exact provenance structure AI Test Lab accepts?

## Translation behavior

The translator:

1. accepts only a `bytes` document;
2. decodes strict UTF-8;
3. parses one JSON document;
4. rejects non-standard JSON numbers and duplicate keys at every depth;
5. requires the JSON root to be an object; and
6. validates that object directly into the immutable ATL-A.03.01 contract.

Every decoding, parsing, ambiguity, root-shape, or contract-validation failure
is closed behind one stable public translation error. Parsed state is detached
from the caller and immutable through the A.03.01 DTO.

## Acceptance criteria

1. A valid A.03.01 UTF-8 JSON document translates successfully.
2. Invalid UTF-8, malformed JSON, empty input, and non-object roots fail closed.
3. Duplicate keys at the envelope or nested claims level fail closed.
4. `NaN` and infinity values are rejected as non-standard JSON.
5. Missing, extra, unsupported-version, and malformed contract fields fail
   behind the translation error.
6. Text, byte arrays, memory views, and other non-`bytes` inputs are rejected.
7. Successful output is exactly the frozen A.03.01 contract and remains
   detached and immutable.
8. Translation does not claim producer or key trust, signature validity,
   evidence integrity, freshness, or replay safety.

## Security and IP boundary

The translator exposes only the frozen public A.03.01 DTO and a stable public
failure category. It does not expose private keys, trust stores, allowlist
decisions, governance policy, provider state, raw parser failures, tracebacks,
or proprietary evidence intelligence.

## Explicit non-goals

- defining the canonical bytes covered by the signature;
- verifying the Ed25519 signature or resolving the referenced key;
- trusting `producer_id` or `key_id`;
- binding provenance to a completed A.02 outcome;
- timestamp freshness or replay prevention;
- persistence, transport security, key storage, retries, or provider SDKs;
- proprietary scoring, governance, compliance, evidence-intelligence, or
  enforcement logic;
- importing, executing, or modifying Aquagear.

## Verification

```powershell
python -m pytest `
  tests/test_reference_architecture_authenticated_provenance_contract.py `
  tests/test_reference_architecture_authenticated_provenance_document_translation.py `
  -q

python -m pytest -q
```

## Repository placement

- `src/reference_architecture_authenticated_provenance_document_translation.py`
- `tests/test_reference_architecture_authenticated_provenance_document_translation.py`
- `docs/sprints/atl-a.03.02.md`

## Suggested commit

```text
feat: translate untrusted authenticated provenance documents
```
