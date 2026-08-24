# Sprint 11.56 — Evaluation Run Regression Result Serialization

## Goal

Sprint 11.56 introduces an explicit serialization boundary for the stable evaluation-run regression result created in Sprint 11.55.

The sprint converts the internal:

```text
EvaluationRunRegressionResult
```

into a deterministic external representation suitable for future CLI, CI/CD, reporting, and API consumers.

## New Serializer

A new serializer was introduced:

```python
serialize_evaluation_run_regression_result(...)
```

It converts:

```python
EvaluationRunRegressionResult
```

into:

```python
{
    "enforcement": "allow",
    "exit_code": 0,
}
```

or:

```python
{
    "enforcement": "block",
    "exit_code": 1,
}
```

## Architectural Boundary

Sprint 11.56 intentionally avoids automatically exposing internal dataclasses.

The flow is now:

```text
Metric Regression Decisions
        ↓
Evaluation Run Regression Gate
        ↓
Evaluation Run Regression Enforcement
        ↓
Evaluation Run Regression Exit Code
        ↓
Evaluation Run Regression Result
        ↓
Explicit Serialization
```

The serializer does not:

- recalculate enforcement policy
- recalculate exit-code policy
- mutate the original result
- serialize internal objects automatically
- introduce CLI or API integration

## Files Added

### Production

```text
src/evaluation_run_regression_result_serializer.py
```

Introduces:

```text
serialize_evaluation_run_regression_result
```

### Tests

```text
tests/test_evaluation_run_regression_result_serializer.py
```

## Test Coverage

Sprint 11.56 verifies:

1. `ALLOW` serializes to `"allow"`.
2. `BLOCK` serializes to `"block"`.
3. Exit code `0` remains integer `0`.
4. Exit code `1` remains integer `1`.
5. Serialization is deterministic.
6. Serialization does not mutate the original result.

## Design Principles

### Explicit public transformation

External representations are deliberately constructed instead of relying on automatic dataclass serialization.

### Deterministic behavior

The same internal result produces the same serialized representation.

### Single responsibility

The serializer only transforms an already-computed result.

### IP boundary preservation

Only explicitly selected fields are exposed to downstream consumers.

## Validation

Focused tests:

```text
4 passed
```

Full regression suite:

```text
519 passed in 10.02s
```

## Explicitly Out of Scope

Sprint 11.56 does not add:

- CLI output changes
- JSON file writing
- API endpoints
- GitHub Actions integration
- persistence
- regression history
- dashboards
- new regression policy
- new enforcement policy
- new exit-code policy

## Result

Sprint 11.56 establishes a safe and deterministic serialization boundary between the internal regression execution result and future external integrations.
