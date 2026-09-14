# ATL–A.01.6 — Correlated Round-Trip Orchestration

## Status

Implemented on the `atl-a01` integration branch.

## Purpose

This slice composes the already-frozen ATL–A.01 contracts into one guarded
round trip. AI Test Lab now validates compatibility, calls the injected
provider-neutral integration port, translates the response into the public v1
DTO, and confirms that the response belongs to the originating request.

No Aquagear feature expansion, provider SDK dependency, transport protocol, or
proprietary evaluation logic is introduced.

## Runtime sequence

1. Validate the provider-neutral request identity before any provider call.
2. Translate and verify the Aquagear v1 compatibility handshake.
3. Invoke the injected integration port exactly once.
4. Translate the untrusted raw response into the frozen public response DTO.
5. Correlate contract version, integration ID, correlation ID, and operation.
6. Return the composed result only when the response is correlated.

## Failure behavior

- Malformed correlation identity fails before provider invocation.
- Incompatible reference architecture fails before provider invocation.
- Provider exceptions remain provider exceptions.
- Malformed responses retain the stable response-translation error.
- Valid but mismatched responses fail closed with
  `ReferenceArchitectureUncorrelatedResponseError`.
- Mismatch messages expose only stable public field names.

## Public/private boundary

The final orchestration result is an immutable internal dataclass, not a public
Pydantic contract. Its validated response-translation and correlation DTOs may
be explicitly serialized, while the injected port and orchestration internals
remain private.

## Files

- `src/reference_architecture_round_trip_orchestration.py`
- `tests/test_reference_architecture_round_trip_orchestration.py`
- `docs/sprints/atl-a.01.6.md`

## Acceptance criteria

- A valid response completes all stages and is returned once correlated.
- Invalid preconditions prevent the provider call.
- A mismatched response is never returned as successful.
- Inputs are not mutated.
- The composed result is immutable and is not implicitly public.
- Existing A.01.1–A.01.5 errors remain diagnostically intact.

## Explicit non-goals

- HTTP or queue transport
- retry, timeout, or idempotency policy
- provider error normalization
- persistence or evidence storage
- concurrent request routing
- Aquagear contract changes
