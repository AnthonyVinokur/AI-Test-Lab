# ATL-A.01.4 — Provider-Neutral Response Translation

## Status

**Implemented.**

## Objective

Translate the raw provider response intentionally preserved by ATL-A.01.3 into
an immutable, approved AI Test Lab public response contract matching the frozen
Aquagear A.40 `v1` response shape.

## Behavior

`src/reference_architecture_response_translation.py` accepts one untrusted
mapping and validates the complete response boundary:

- exact `v1` contract identity;
- integration and correlation identity;
- canonical `submit`, `enforce`, or `return` operation;
- canonical `accepted`, `completed`, `rejected`, or `failed` status;
- optional opaque artifact;
- ordered, unique string metadata entries.

Missing fields, undeclared fields, invalid types, unsupported enum values,
duplicate metadata keys, and invalid artifacts raise the single stable
`ReferenceArchitectureResponseTranslationError` boundary.

## Explicit transformation

The frozen Aquagear response carries opaque artifact bytes. The public AI Test
Lab DTO does not serialize internal byte objects directly. The translator
copies those bytes and exposes them as deterministic Base64 in
`payload_base64`. It does not decode, inspect, score, trust, or enforce the
artifact contents.

## Protection boundaries

- No Aquagear import or modification.
- No HTTP, SDK, provider, model, credential, timeout, or retry dependency.
- No raw response object is declared to be a public contract.
- No private score, governance rule, evidence intelligence, enforcement rule,
  provider exception, or implementation detail crosses the boundary.
- Public DTOs remain immutable and forbid undeclared fields.

## Validation

Focused tests cover complete translation, approved serialization, all canonical
enums, optional artifacts, malformed and incompatible shapes, extra-field
rejection, byte-payload validation, duplicate metadata, immutability, stable
errors, and input non-mutation.

Recommended verification:

```powershell
python -m pytest `
  tests/test_reference_architecture_compatibility_contract.py `
  tests/test_reference_architecture_request_translation.py `
  tests/test_reference_architecture_integration_adapter.py `
  tests/test_reference_architecture_response_translation.py `
  -q
```

## Explicit non-goals

- wiring response translation into the A.01.3 adapter;
- request/response identity correlation;
- provider-error normalization;
- artifact interpretation or evidence validation;
- compatibility enforcement;
- Aquagear feature expansion;
- cross-version compatibility.

Those responsibilities remain separate future slices.
