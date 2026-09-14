# ATL-A.02.06 — Evidence Binding Failure Normalization

## Status

**Implemented.**

## Objective

Convert every ordinary A.02.05 evidence-binding rejection into one stable,
provider-neutral, redacted public failure contract.

## Behavior

The normalized boundary preserves a successful verified binding unchanged. A
failure returns a frozen public DTO with only:

- contract name and version;
- stable stage and code;
- safe fixed message;
- retryability;
- response integration and correlation identifiers when safely available.

The raw exception, traceback, artifact bytes, provider response, translated
evidence, and proprietary evaluation meaning are never included.

A.02.05 now attaches a stable internal reason to its existing binding error.
A.02.06 maps that reason to public semantics without parsing exception text.

## Stable stages and codes

| Stage | Codes |
| --- | --- |
| `round_trip_validation` | `invalid_round_trip`, `uncorrelated_response` |
| `response_acceptance` | `response_not_completed` |
| `artifact_validation` | `missing_evidence_artifact`, `invalid_evidence_transport` |
| `document_translation` | `invalid_evidence_document` |
| `integrity` | `evidence_integrity_failed` |
| `compatibility` | `incompatible_evidence` |
| `binding` | `evidence_binding_failed` |

Binding failures are not retryable because retrying the same immutable response
cannot repair its evidence. Process-control exceptions such as
`KeyboardInterrupt` remain outside normalization.

## Acceptance criteria

1. Successful bindings remain successful and unchanged.
2. Every known A.02.05 rejection has a deterministic stage and code.
3. Invalid inputs normalize without leaking caller data.
4. Safe response identifiers are retained when available.
5. Raw exceptions, artifact payloads, and evidence content are excluded.
6. The public failure contract and internal result union are immutable.
7. Exactly one success or failure branch is populated.
8. Control-flow exceptions are not swallowed.

## Verification

```powershell
python -m pytest `
  tests/test_reference_architecture_conformance_evidence_round_trip_binding.py `
  tests/test_reference_architecture_conformance_evidence_binding_failure_normalization.py `
  -q

python -m pytest -q
```

## Repository placement

- `src/reference_architecture_conformance_evidence_round_trip_binding.py`
- `src/reference_architecture_conformance_evidence_binding_failure_normalization.py`
- `tests/test_reference_architecture_conformance_evidence_binding_failure_normalization.py`
- `docs/sprints/atl-a.02.md`
- `docs/sprints/atl-a.02.06.md`

## Suggested commit

```text
feat: normalize conformance evidence binding failures
```
