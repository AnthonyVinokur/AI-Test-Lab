# ATL–A.01.7 — Round-Trip Failure Normalization

## Status

Implemented on the `atl-a01` development line.

## Goal

Give callers one stable, provider-neutral failure contract for the complete
A.01.6 correlated round trip. Internal exceptions must not leak provider
details, private payloads, tracebacks, credentials, or orchestration state.

## Delivered

- A frozen public `ReferenceArchitectureRoundTripFailureV1` DTO.
- Stable failure stages: request validation, compatibility, provider
  invocation, response translation, and correlation.
- Stable machine-readable failure codes.
- Deterministic safe messages independent of raw exception text.
- Retryability is true only for unknown provider-invocation failures.
- Safe propagation of validated-looking integration and correlation IDs.
- An immutable internal success/failure union with exactly one branch.
- A class and functional entry point wrapping the A.01.6 orchestrator.
- Fail-closed handling while allowing process-control exceptions such as
  `KeyboardInterrupt` to propagate.

## Normalization table

| Source failure | Stage | Code | Retryable |
|---|---|---|---|
| Invalid request identity | `request_validation` | `invalid_request_identity` | No |
| Malformed compatibility request | `compatibility` | `invalid_compatibility_request` | No |
| Valid but incompatible architecture | `compatibility` | `incompatible_reference_architecture` | No |
| Provider/integration exception | `provider_invocation` | `provider_invocation_failed` | Yes |
| Malformed provider response | `response_translation` | `invalid_provider_response` | No |
| Response/request mismatch | `correlation` | `uncorrelated_provider_response` | No |

## IP protection boundary

The public failure DTO contains only contract identity, stage, code, a fixed
safe message, retryability, and two request identifiers. It never serializes
the source exception, raw provider response, compatibility mismatch internals,
port implementation, traceback, or proprietary orchestration details.

## Verification

The focused tests cover successful pass-through, every failure family,
provider-call counts, retryability, redaction, schema shape, contract identity,
immutable union invariants, and control-flow exception propagation.

Run in PowerShell:

```powershell
python -m pytest `
  tests/test_reference_architecture_round_trip_failure_normalization.py `
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
  -q
```

## Repository placement

- `src/reference_architecture_round_trip_failure_normalization.py`
- `tests/test_reference_architecture_round_trip_failure_normalization.py`
- `docs/sprints/atl-a.01.7.md`

## Suggested commit

```text
feat: normalize reference architecture round trip failures
```
