# ATL–A.01.9 — Public Round-Trip Serialization Boundary

## Status

Implemented on the `atl-a01` development line.

## Goal

Serialize the frozen A.01.8 public outcome into one deterministic JSON-safe
representation without exposing provider data, exceptions, orchestration state,
or proprietary internals.

## Delivered

- Detached JSON-safe dictionary serialization.
- Deterministic compact UTF-8 JSON byte encoding.
- Strict decoding back into the frozen A.01.8 DTO.
- Fail-closed rejection of malformed JSON, non-object roots, extra fields, and
  inconsistent success/failure branches.
- Revalidation before serialization to protect against runtime-altered state.
- Stable sorted JSON keys and rejection of non-standard numeric values.

## Acceptance criteria

1. Success and failure outcomes round-trip without semantic change.
2. Identical outcomes produce identical UTF-8 JSON bytes.
3. Returned mappings cannot mutate the source DTO.
4. Only `ReferenceArchitectureRoundTripOutcomeV1` may enter the serializer.
5. Decoding rejects malformed, non-object, expanded, or inconsistent payloads.
6. No raw provider response, exception, traceback, credential, or internal state
   enters the serialized document.

## Explicit non-goals

- HTTP or provider SDK integration;
- authentication, transport, persistence, retries, or timeouts;
- signing, encryption, or compression;
- evidence evaluation or enforcement policy;
- Aquagear imports or changes to its frozen contracts.

## Verification

```powershell
python -m pytest `
  tests/test_reference_architecture_round_trip_serialization.py `
  -q
```

Then run the A.01 regression slice through A.01.9.

## Repository placement

- `src/reference_architecture_round_trip_serialization.py`
- `tests/test_reference_architecture_round_trip_serialization.py`
- `docs/sprints/atl-a.01.9.md`

## Suggested commit

```text
feat: add public round trip serialization boundary
```
