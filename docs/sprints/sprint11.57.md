# Sprint 11.57 — Evaluation Run Regression Result JSON Encoding

## Goal

Sprint 11.57 introduces deterministic JSON encoding for the evaluation-run regression result.

It builds directly on Sprint 11.56, which created the explicit serialization boundary for:

```text
EvaluationRunRegressionResult
```

Sprint 11.57 converts that approved serialized representation into compact JSON suitable for future CLI, CI/CD, reporting, and API consumers.

## Architecture

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
        ↓
Deterministic JSON Encoding
```

The JSON layer intentionally depends on the existing serializer instead of directly inspecting internal regression objects.

This preserves the public/private boundary established in Sprint 11.56.

## New JSON Encoder

A new function was introduced:

```python
encode_evaluation_run_regression_result_json(...)
```

It converts the stable regression result into compact JSON.

Example ALLOW result:

```json
{"enforcement":"allow","exit_code":0}
```

Example BLOCK result:

```json
{"enforcement":"block","exit_code":1}
```

## Implementation

The encoder first calls:

```python
serialize_evaluation_run_regression_result(...)
```

and then converts the resulting public dictionary to JSON using Python's standard JSON encoder.

Compact separators are used:

```python
separators=(",", ":")
```

This avoids unnecessary whitespace and ensures the output format remains predictable.

## Architectural Boundary

Sprint 11.57 does not duplicate or bypass existing regression logic.

The JSON encoder does not:

* calculate regression decisions
* calculate enforcement policy
* calculate exit codes
* inspect internal enforcement fields directly
* automatically serialize internal dataclasses
* mutate the original result

Instead, it consumes only the explicit serialized representation created by Sprint 11.56.

The boundary is:

```text
Protected Internal Regression Objects
        ↓
Evaluation Run Regression Result
        ↓
Explicit Serializer
==============================
Public Representation Boundary
        ↓
JSON Encoder
        ↓
External Consumers
```

Potential future external consumers include:

```text
CLI
CI/CD pipelines
GitHub Actions
reports
public APIs
dashboards
automation
```

Those integrations remain outside the scope of this sprint.

## Files Added

### Production

```text
src/evaluation_run_regression_result_json.py
```

Introduces:

```text
encode_evaluation_run_regression_result_json
```

### Tests

```text
tests/test_evaluation_run_regression_result_json.py
```

## Test Coverage

Sprint 11.57 verifies:

1. ALLOW encodes as:

```json
{"enforcement":"allow","exit_code":0}
```

2. BLOCK encodes as:

```json
{"enforcement":"block","exit_code":1}
```

3. Identical input produces identical JSON output.

4. The encoded result is valid JSON and can be decoded back into the expected public dictionary.

## Validation

Focused JSON tests:

```text
4 passed
```

Serializer and JSON tests:

```text
8 passed
```

Full regression suite:

```text
523 passed in 10.00s
```

## Design Principles

### Explicit transformation

Internal regression objects are never automatically exposed as JSON.

### Deterministic output

The same result produces the same compact JSON representation.

### Single responsibility

The JSON encoder only converts an already-approved serialized representation into JSON.

### No duplicated policy

Regression, enforcement, and exit-code logic remain owned by their existing layers.

### IP boundary preservation

The JSON layer receives only explicitly selected public fields.

## Explicitly Out of Scope

Sprint 11.57 does not add:

* JSON file persistence
* CLI output integration
* API endpoints
* GitHub Actions integration
* regression history
* dashboards
* new regression policy
* new enforcement policy
* new exit-code policy

## Result

Sprint 11.57 extends the regression result pipeline with a safe deterministic JSON representation.

The architecture is now:

```text
Detection
    ↓
Classification
    ↓
Gate
    ↓
Enforcement
    ↓
Exit Code
    ↓
Stable Result
    ↓
Explicit Serialization
    ↓
Deterministic JSON
```

This prepares AI Test Lab for future external integrations while preserving the existing regression architecture and protected internal boundaries.
