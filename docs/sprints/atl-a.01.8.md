# ATL–A.01.8 — Public Round-Trip Outcome Projection

## Status

Implemented on the `atl-a01` development line.

## Goal

Expose the completed A.01 round trip through one stable, provider-neutral public
outcome contract. A caller receives either a validated correlated response or a
normalized failure without gaining access to raw provider state, injected ports,
translation internals, correlation diagnostics, exceptions, or orchestration
objects.

## Delivered

- Frozen public `ReferenceArchitectureRoundTripOutcomeV1` DTO.
- Exactly-one success/failure branch invariant.
- A success flag that must agree with the populated branch.
- Success projection containing only the validated public response DTO.
- Failure projection containing only the safe A.01.7 failure DTO.
- Class and functional entry points for the complete public round trip.
- Deep copies at the projection boundary.
- Fail-closed rejection of malformed or expanded public envelopes.
- Continued propagation of process-control exceptions such as
  `KeyboardInterrupt`.

## Public envelope

| Field | Meaning |
|---|---|
| `contract_name` | Stable outcome contract identity |
| `outcome_contract_version` | Frozen public schema version (`1.0`) |
| `succeeded` | True exactly when `response` is populated |
| `response` | Correlated provider-neutral v1 response, or `null` |
| `failure` | Normalized provider-neutral A.01.7 failure, or `null` |

## IP protection boundary

The new public DTO is an explicit projection, not a serialization of the
internal round-trip result. It excludes the integration adapter, provider port,
raw provider response, compatibility result, translation wrapper, correlation
decision internals, source exception, traceback, credentials, and proprietary
orchestration state.

## Acceptance criteria

1. A successful correlated round trip produces a response-only public envelope.
2. Every ordinary A.01.7 failure produces a failure-only public envelope.
3. Both or neither branches are rejected.
4. `succeeded` cannot disagree with the populated branch.
5. Extra public fields are rejected by the frozen public-contract base.
6. Raw exception text and internal orchestration state cannot enter the output.
7. Input mappings remain unchanged.
8. Process-control exceptions still propagate.

## Verification

Run in PowerShell:

```powershell
python -m pytest `
  tests/test_reference_architecture_round_trip_outcome_projection.py `
  -q
```

Then run the A.01 regression slice:

```powershell
python -m pytest `
  tests/test_reference_architecture_compatibility_contract.py `
  tests/test_reference_architecture_request_translation.py `
  tests/test_reference_architecture_integration_adapter.py `
  tests/test_reference_architecture_response_translation.py `
  tests/test_reference_architecture_request_response_correlation.py `
  tests/test_reference_architecture_round_trip_orchestration.py `
  tests/test_reference_architecture_round_trip_failure_normalization.py `
  tests/test_reference_architecture_round_trip_outcome_projection.py `
  -q
```

## Repository placement

- `src/reference_architecture_round_trip_outcome_projection.py`
- `tests/test_reference_architecture_round_trip_outcome_projection.py`
- `docs/sprints/atl-a.01.8.md`

## Suggested commit

```text
feat: add public reference architecture round trip outcome
```
