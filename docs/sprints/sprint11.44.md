# Sprint 11.44 — Evaluation Run Regression Eligibility

## Objective

Add a regression eligibility layer that determines whether two evaluation runs are valid candidates for regression comparison.

This sprint does not compare evaluation scores.

It only answers:

> Are these two runs sufficiently reproducible to be compared fairly?

## Problem

Sprint 11.43 added deterministic evaluation run reproducibility verification.

That allows AI Test Lab to determine whether two runs were executed under equivalent reproducibility-critical conditions.

Before future regression logic compares scores, metrics, pass rates, or quality results, AI Test Lab needs a separate gate that determines whether such a comparison is valid.

Comparing non-equivalent runs could produce misleading regression results.

Examples include:

* different models;
* different datasets;
* different dataset versions;
* different evaluation profiles;
* different report contracts;
* different report contract fingerprints.

Sprint 11.44 introduces a dedicated regression eligibility contract.

## Implementation

Added:

`src/evaluation_run_regression_eligibility.py`

The module provides:

* `EvaluationRunRegressionEligibility`
* `determine_evaluation_run_regression_eligibility()`

The result contains:

* `eligible`
* `mismatches`

Example eligible result:

```python
EvaluationRunRegressionEligibility(
    eligible=True,
    mismatches=(),
)
```

Example ineligible result:

```python
EvaluationRunRegressionEligibility(
    eligible=False,
    mismatches=("dataset_version",),
)
```

## Architectural Rule

Sprint 11.44 does not duplicate reproducibility comparison logic.

Instead, it delegates to the existing Sprint 11.43 function:

```python
verify_evaluation_run_reproducibility()
```

The regression eligibility result is derived directly from that verification result.

Conceptually:

```text
EvaluationRunProvenance
        ↓
Reproducibility Verification
        ↓
Regression Eligibility
```

This keeps reproducibility rules centralized and prevents duplicate comparison logic from drifting over time.

## Eligibility Rule

If the two evaluation runs are reproducible:

```text
reproducible = True
```

then:

```text
eligible = True
```

If reproducibility verification reports one or more mismatches:

```text
reproducible = False
```

then:

```text
eligible = False
```

The mismatch fields are preserved unchanged.

## Run Identity

Different `run_id` values do not make runs ineligible.

Separate executions should normally have separate run IDs.

Regression eligibility therefore depends on reproducibility conditions rather than execution identity.

## Scope Boundary

Sprint 11.44 determines only whether two runs may be compared.

It does not:

* compare metric scores;
* calculate regression magnitude;
* define regression thresholds;
* determine improvement or degradation;
* modify CLI behavior;
* generate regression reports;
* introduce CI quality gates.

Those capabilities belong to later layers.

## Tests

Added:

`tests/test_evaluation_run_regression_eligibility.py`

Coverage verifies:

* reproducible runs are eligible;
* different run IDs remain eligible;
* model mismatches make runs ineligible;
* dataset version mismatches make runs ineligible;
* multiple mismatches are preserved;
* mismatch ordering remains deterministic;
* invalid baseline inputs are rejected;
* invalid candidate inputs are rejected.

## Verification Results

Focused Sprint 11.44 tests:

```text
6 passed in 0.06s
```

Full regression suite:

```text
385 passed in 10.61s
```

## Architectural Result

AI Test Lab can now distinguish between:

### Reproducibility Verification

> Were two evaluation runs executed under equivalent controlled conditions?

and:

### Regression Eligibility

> Is it valid to compare the results of these two runs for regression analysis?

This creates a safe boundary before actual regression comparison logic is introduced.

The resulting progression is:

```text
Evaluation Run Identity
        ↓
Evaluation Run Provenance
        ↓
Provenance Fingerprint
        ↓
Provenance Verification
        ↓
Reproducibility Verification
        ↓
Regression Eligibility
        ↓
Future Regression Comparison
```

## Status

Sprint 11.44 complete.
