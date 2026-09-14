# ATL-A.02.08 — Public Evidence-Binding Serialization Boundary

## Status

**Implemented.**

## Objective

Define one deterministic wire format for the frozen A.02.07 public
evidence-binding outcome without allowing internal binding, transport,
verification, provider, or exception state to cross the boundary.

## Behavior

A.02.08 accepts only a
`ReferenceArchitectureConformanceEvidenceBindingOutcomeV1`. Before
serialization, it revalidates the public model and produces a deeply detached
JSON-safe mapping.

The encoder emits deterministic, compact UTF-8 JSON bytes with:

- lexicographically sorted object keys;
- no optional whitespace;
- Unicode preserved as UTF-8;
- non-finite numbers rejected.

The decoder accepts exact `bytes`, requires a top-level JSON object, and
validates the complete document against the frozen A.02.07 public contract.
Malformed UTF-8, malformed JSON, missing fields, extra fields, or inconsistent
success/failure branches fail closed behind one stable serialization error.

## Wire identity

| Constant | Value |
| --- | --- |
| `REFERENCE_ARCHITECTURE_CONFORMANCE_EVIDENCE_BINDING_SERIALIZATION_FORMAT` | `json` |
| `REFERENCE_ARCHITECTURE_CONFORMANCE_EVIDENCE_BINDING_SERIALIZATION_VERSION` | `1.0` |

The format version identifies this canonical encoding boundary. The serialized
document retains the A.02.07 `contract_name` and
`outcome_contract_version`; it does not add another wrapper.

## IP protection boundary

The serializer consumes only the explicit A.02.07 public DTO. It never accepts
the internal A.02.05 binding object or the A.02.06 internal normalized union.
It cannot export the full response, artifact transport or base64 payload,
metadata, provider state, verification mechanics, source exceptions,
tracebacks, or proprietary scoring and governance logic.

Successful documents contain only the safe identifiers and already-approved
A.02.01 evidence. Failed documents contain only the redacted A.02.06 failure.

## Acceptance criteria

1. Success and failure outcomes round-trip through UTF-8 JSON.
2. Re-encoding the same outcome produces identical bytes.
3. Encoded JSON is compact and key-sorted.
4. Mapping output is deeply detached from the source model.
5. Only the A.02.07 public outcome is accepted for serialization.
6. Decode accepts exact bytes and requires a top-level object.
7. Malformed, incomplete, inconsistent, and extended documents fail closed.
8. Success output excludes transport, response, provider, and internal state.
9. Failure output exposes only the normalized redacted failure contract.

## Verification

```powershell
python -m pytest `
  tests/test_reference_architecture_conformance_evidence_binding_outcome.py `
  tests/test_reference_architecture_conformance_evidence_binding_serialization.py `
  -q

python -m pytest -q
```

## Repository placement

- `src/reference_architecture_conformance_evidence_binding_serialization.py`
- `tests/test_reference_architecture_conformance_evidence_binding_serialization.py`
- `docs/sprints/atl-a.02.md`
- `docs/sprints/atl-a.02.08.md`

## Suggested commit

```text
feat: serialize public evidence binding outcomes
```
