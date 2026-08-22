# Sprint 11.43 — Evaluation Run Reproducibility Verification

## Objective

Add deterministic verification that determines whether two evaluation runs were executed under equivalent reproducibility-critical conditions.

The verification must distinguish evaluation run identity from evaluation run reproducibility.

Two separate runs may have different run IDs while still being reproducible.

## Problem

AI Test Lab already provides:

- evaluation run identity;
- evaluation run provenance;
- provenance fingerprint generation;
- provenance fingerprint verification.

However, a provenance fingerprint includes the evaluation run ID.

Because every legitimate rerun should have its own run ID, directly comparing provenance fingerprints would incorrectly classify otherwise equivalent runs as non-reproducible.

Sprint 11.43 introduces a separate reproducibility comparison contract.

## Reproducibility Fields

The following provenance fields are considered reproducibility-critical:

- `model`
- `evaluation_profile`
- `dataset`
- `dataset_version`
- `report_contract`
- `report_contract_fingerprint`

The following field is intentionally excluded:

- `run_id`

A different `run_id` identifies a different execution but does not by itself mean the execution conditions changed.

## Implementation

Added:

`src/evaluation_run_reproducibility.py`

The module provides:

- `EvaluationRunReproducibilityVerification`
- `verify_evaluation_run_reproducibility()`

The verification result contains:

- `reproducible`
- `mismatches`

Example successful result:

```python
EvaluationRunReproducibilityVerification(
    reproducible=True,
    mismatches=(),
)
```

Example mismatch:

```python
EvaluationRunReproducibilityVerification(
    reproducible=False,
    mismatches=("dataset_version",),
)
```

## Deterministic Comparison

Reproducibility fields are evaluated in a fixed order.

This guarantees deterministic mismatch reporting across runs and environments.

The comparison order is:

1. model
2. evaluation_profile
3. dataset
4. dataset_version
5. report_contract
6. report_contract_fingerprint

## Validation

The verifier requires both inputs to be `EvaluationRunProvenance` instances.

Invalid baseline or candidate values raise `TypeError`.

## Tests

Added:

`tests/test_evaluation_run_reproducibility.py`

Coverage verifies:

- identical reproducibility conditions pass;
- different run IDs do not break reproducibility;
- model changes are detected;
- dataset version changes are detected;
- multiple mismatches are reported;
- mismatch ordering is deterministic;
- invalid baseline values are rejected;
- invalid candidate values are rejected.

## Verification Results

Focused Sprint 11.43 tests:

```text
7 passed in 0.06s
```

Provenance and reproducibility verification tests:

```text
31 passed in 0.14s
```

Full regression suite:

```text
379 passed in 11.19s
```

## Architectural Result

AI Test Lab can now distinguish between:

### Provenance Integrity

> Has this specific provenance record changed?

and:

### Evaluation Reproducibility

> Were two separate evaluation runs executed under equivalent controlled conditions?

This distinction is required before reliable evaluation regression comparison can be introduced.

EvaluationRunReproducibilityVerification(
    reproducible=False,
    mismatches=("dataset_version",),
)

## Status

Sprint 11.43 complete.
