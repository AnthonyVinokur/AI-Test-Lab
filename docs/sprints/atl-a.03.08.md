# ATL-A.03.08 — Public Outcome Serialization Boundary

## Status

**Implemented.**

## Objective

Provide the only approved A.03 public wire boundary: detached mappings and
deterministic compact UTF-8 JSON for A.03.07 outcomes.

## Guarantees

- Only the exact A.03.07 public outcome type is accepted.
- Encoding is sorted, compact, UTF-8, and rejects non-standard numbers.
- Decoding rejects invalid UTF-8, non-object roots, duplicate keys, extra
  fields, malformed branches, and unsupported contract identities.
- Decoded values are frozen public contracts.
- Mapping output is detached from the source model.
- Signature bytes, key material, binding objects, payloads, tracebacks, and
  proprietary internal state cannot cross this schema.

## Verification

`tests/test_reference_architecture_authenticated_provenance_serialization.py`

## Repository placement

- `src/reference_architecture_authenticated_provenance_serialization.py`
- `tests/test_reference_architecture_authenticated_provenance_serialization.py`
