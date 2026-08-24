# Sprint 11.58 — Evaluation Run Regression Result JSON File Persistence

## Goal

Sprint 11.58 adds explicit JSON file persistence for the evaluation-run regression result.

It builds directly on Sprint 11.57, which introduced deterministic JSON encoding for:

```text
EvaluationRunRegressionResult
```

Sprint 11.58 takes that approved JSON representation and provides a dedicated mechanism for writing it to disk.

The architecture now extends from:

```text
EvaluationRunRegressionResult
        ↓
Explicit Serialization
        ↓
Deterministic JSON Encoding
```

to:

```text
EvaluationRunRegressionResult
        ↓
Explicit Serialization
        ↓
Deterministic JSON Encoding
        ↓
JSON File Persistence
```

This creates a durable output boundary for future CLI, CI/CD, reporting, GitHub Actions, API, and dashboard integrations without exposing protected internal regression logic.

---

## New JSON File Writer

A new function was introduced:

```python
write_evaluation_run_regression_result_json(...)
```

The writer accepts:

```text
EvaluationRunRegressionResult
```

and a destination path.

It then delegates JSON generation to the existing:

```python
encode_evaluation_run_regression_result_json(...)
```

function.

The writer itself does not perform serialization or inspect regression internals.

Example persisted ALLOW result:

```json
{"enforcement":"allow","exit_code":0}
```

Example persisted BLOCK result:

```json
{"enforcement":"block","exit_code":1}
```

---

## Implementation

The implementation is located in:

```text
src/evaluation_run_regression_result_writer.py
```

The writer:

1. Converts the supplied path into a `Path`.
2. Creates missing parent directories.
3. Calls the existing deterministic JSON encoder.
4. Writes the encoded result using UTF-8.

The implementation uses:

```python
output_path.parent.mkdir(
    parents=True,
    exist_ok=True,
)
```

This allows destinations such as:

```text
results/regression/result.json
```

to be created even if the parent directories do not already exist.

The JSON content is written using:

```python
output_path.write_text(
    encode_evaluation_run_regression_result_json(result),
    encoding="utf-8",
)
```

---

## Architecture

The evaluation-run regression pipeline is now:

```text
Metric Regression Evaluation
        ↓
Metric Regression Severity
        ↓
Metric Regression Quality Gate
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
        ↓
JSON File Persistence
```

Each layer continues to own one specific responsibility.

---

## Public / Private Boundary

Sprint 11.58 preserves the IP-protection boundary established in the preceding result-contract sprints.

The persistence layer does not serialize internal dataclasses directly.

It does not use mechanisms such as:

```python
result.__dict__
```

or:

```python
dataclasses.asdict(result)
```

for external persistence.

Instead:

```text
Protected Internal Regression Logic
            ↓
EvaluationRunRegressionResult
            ↓
Explicit Serializer
=================================
Approved Public Representation
            ↓
JSON Encoder
            ↓
JSON File Writer
            ↓
External File
```

The file writer therefore receives only information already approved for external representation.

---

## Separation of Responsibilities

The file writer does not:

* calculate metric movement
* determine metric direction
* calculate regression tolerance
* classify regression severity
* make quality-gate decisions
* determine enforcement
* determine process exit codes
* inspect protected enforcement internals
* serialize internal objects
* duplicate JSON formatting logic

Its responsibility is only:

```text
approved JSON representation
        ↓
persistent file
```

---

## Parent Directory Creation

Sprint 11.58 explicitly supports nested output paths.

For example:

```text
tmp/
└── nested/
    └── regression/
        └── result.json
```

If:

```text
nested/regression/
```

does not exist, the writer creates it automatically.

This makes the persistence layer suitable for future automation and CI/CD environments where output directories may not yet exist.

---

## Existing File Behavior

Writing to an existing destination replaces the previous file content.

For example:

First write:

```json
{"enforcement":"allow","exit_code":0}
```

Then write a BLOCK result to the same path:

```json
{"enforcement":"block","exit_code":1}
```

The resulting file contains only the latest representation:

```json
{"enforcement":"block","exit_code":1}
```

This behavior remains deterministic and avoids appending or combining unrelated regression results.

Regression history remains outside this sprint.

---

## Files Added

### Production

```text
src/evaluation_run_regression_result_writer.py
```

Introduces:

```text
write_evaluation_run_regression_result_json
```

### Tests

```text
tests/test_evaluation_run_regression_result_writer.py
```

### Documentation

```text
docs/sprints/sprint11.58.md
```

---

## Test Coverage

Sprint 11.58 verifies five persistence behaviors.

### 1. ALLOW result persistence

Verifies that an ALLOW result is written exactly as:

```json
{"enforcement":"allow","exit_code":0}
```

### 2. BLOCK result persistence

Verifies that a BLOCK result is written exactly as:

```json
{"enforcement":"block","exit_code":1}
```

### 3. Parent directory creation

Verifies that nested parent directories are automatically created when they do not already exist.

### 4. Existing file replacement

Verifies that writing a second result to the same path replaces the previous file contents.

### 5. Valid public JSON

Verifies that the persisted file can be decoded as JSON and contains exactly the approved public fields:

```json
{
  "enforcement": "block",
  "exit_code": 1
}
```

---

## Validation

Focused Sprint 11.58 tests:

```text
5 passed in 0.11s
```

The serializer, JSON encoder, and persistence boundary tests were also executed together successfully.

The complete project test suite was executed successfully with all tests green.

---

## Design Principles

### Single responsibility

The writer only persists an already-approved JSON representation.

### Reuse existing contracts

JSON generation remains owned by:

```text
encode_evaluation_run_regression_result_json
```

The persistence layer does not duplicate serialization behavior.

### Deterministic output

The persisted representation is exactly the deterministic JSON produced by Sprint 11.57.

### Explicit transformation boundary

Internal regression objects are not automatically exposed.

### Safe filesystem behavior

Missing parent directories are created automatically.

### UTF-8 encoding

Persistence explicitly uses:

```text
UTF-8
```

rather than relying on platform-dependent defaults.

### Minimal architecture

No database, history mechanism, CLI integration, API layer, or orchestration mechanism is introduced.

---

## Explicitly Out of Scope

Sprint 11.58 does not add:

* CLI regression output integration
* CLI output path arguments
* GitHub Actions integration
* CI/CD orchestration
* API endpoints
* database persistence
* regression history
* run IDs
* timestamps
* result aggregation
* dashboards
* schema versioning
* report generation
* new regression policies
* new enforcement policies
* new exit-code policies

These capabilities can now consume the persistence contract in later sprints without modifying the underlying regression decision architecture.

---

## Result

Sprint 11.58 adds the first durable persistence layer to the evaluation-run regression result pipeline.

Before Sprint 11.58:

```text
Regression Decision
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

After Sprint 11.58:

```text
Regression Decision
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
        ↓
Persistent JSON File
```

AI Test Lab can now safely move a regression result from internal evaluation logic to a durable external artifact while preserving the public/private contract boundary.

This establishes a clean foundation for subsequent CLI and CI/CD integration.
