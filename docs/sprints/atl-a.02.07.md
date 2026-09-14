# ATL-A.02.07 — Public Evidence-Binding Outcome

## Status

**Implemented.**

## Objective

Expose one stable, provider-neutral public result for an A.02 evidence-binding
attempt without exposing the internal binding object, the complete A.01
response, artifact transport state, exceptions, or verification internals.

## Behavior

The public entry point runs the A.02.06 normalized binding boundary and projects
its result into one frozen public outcome.

A successful outcome contains only:

- the response integration identifier;
- the response correlation identifier;
- the verified A.02.01 public evidence contract.

A failed outcome contains only the redacted A.02.06 public failure contract.
Exactly one `binding` or `failure` branch must be populated, and `succeeded`
must agree with that branch.

## Public envelope

| Field | Meaning |
| --- | --- |
| `contract_name` | Stable evidence-binding outcome identity |
| `outcome_contract_version` | Frozen public schema version (`1.0`) |
| `succeeded` | True exactly when `binding` is populated |
| `binding` | Minimal verified binding, or `null` |
| `failure` | Redacted A.02.06 failure, or `null` |

The success binding contains `integration_id`, `correlation_id`, and
`evidence`. The evidence is reconstructed through its public serialized
contract at the projection boundary, providing validation and deep detachment.

## IP protection boundary

A.02.07 is an explicit public projection. It does not serialize the internal
A.02.05 binding result. It excludes the full provider-neutral response,
transport artifact and base64 payload, response metadata, provider state,
translation details, digest-comparison mechanics, compatibility decision
internals, source exceptions, tracebacks, and proprietary evaluation or
governance processing.

The opaque evaluation carried by the already-approved A.02.01 evidence contract
is preserved; A.02.07 does not interpret or expand it.

## Acceptance criteria

1. Successful verified evidence produces a binding-only public envelope.
2. Rejected evidence produces a failure-only public envelope.
3. Both or neither branches are rejected.
4. `succeeded` cannot disagree with the populated branch.
5. Success retains only safe response identifiers and the approved evidence DTO.
6. Failure reuses only the redacted A.02.06 failure DTO.
7. Extra public fields and inconsistent envelopes fail closed.
8. Projected evidence is validated, detached, and immutable.
9. Process-control exceptions such as `KeyboardInterrupt` still propagate.

## Verification

```powershell
python -m pytest `
  tests/test_reference_architecture_conformance_evidence_binding_failure_normalization.py `
  tests/test_reference_architecture_conformance_evidence_binding_outcome.py `
  -q

python -m pytest -q
```

## Repository placement

- `src/reference_architecture_conformance_evidence_binding_outcome.py`
- `tests/test_reference_architecture_conformance_evidence_binding_outcome.py`
- `docs/sprints/atl-a.02.md`
- `docs/sprints/atl-a.02.07.md`

## Suggested commit

```text
feat: add public evidence binding outcome
```
