# Sprint 11.45 — Evaluation Run Regression Comparison

## Objective

Add deterministic regression comparison between two evaluation runs that have already passed regression eligibility verification.

Sprint 11.44 answered:

> Are these two evaluation runs valid candidates for regression comparison?

Sprint 11.45 answers the next question:

> What changed between the baseline run and the candidate run?

This sprint introduces verdict-level regression comparison for individual evaluation cases.

---

## Problem

AI Test Lab can now determine whether two evaluation runs were executed under equivalent reproducibility-critical conditions.

However, eligibility alone does not tell us whether the newer run became better, worse, or stayed the same.

For example:

```text
Baseline: PASS
Candidate: FAIL
```

This is a regression.

Similarly:

```text
Baseline: FAIL
Candidate: PASS
```

This is an improvement.

AI Test Lab needs a deterministic comparison layer that can classify these changes consistently across evaluation runs.

Sprint 11.45 introduces that capability.

---

## Implementation

Added:

```text
src/evaluation_run_regression_comparison.py
```

The module provides the following core types:

```python
EvaluationRunRegressionChange
EvaluationRunCaseResult
EvaluationRunCaseComparison
EvaluationRunRegressionComparison
```

and the comparison function:

```python
compare_evaluation_runs_for_regression()
```

---

## Regression Change Classification

Each evaluation case is classified into one of three states:

```text
UNCHANGED
IMPROVED
REGRESSED
```

The classification rules are:

| Baseline | Candidate | Result    |
| -------- | --------- | --------- |
| PASS     | PASS      | UNCHANGED |
| FAIL     | FAIL      | UNCHANGED |
| FAIL     | PASS      | IMPROVED  |
| PASS     | FAIL      | REGRESSED |

The important regression rule is:

```text
PASS → FAIL = REGRESSED
```

An improvement is:

```text
FAIL → PASS = IMPROVED
```

Equivalent verdicts remain:

```text
UNCHANGED
```

---

## Regression Eligibility Requirement

Sprint 11.45 does not independently decide whether two runs are comparable.

Before comparing case results, it delegates to the existing Sprint 11.44 function:

```python
determine_evaluation_run_regression_eligibility()
```

Conceptually:

```text
Evaluation Run Provenance
        ↓
Reproducibility Verification
        ↓
Regression Eligibility
        ↓
Regression Comparison
```

If the baseline and candidate runs are not regression-eligible, comparison is rejected.

Example:

```text
baseline dataset_version = v1
candidate dataset_version = v2
```

produces an error rather than a potentially misleading regression result.

This preserves the architectural rule that regression analysis should only occur between sufficiently equivalent evaluation runs.

---

## Evaluation Case Contract

Sprint 11.45 introduces a small comparison-specific result contract:

```python
EvaluationRunCaseResult(
    case_id="case-001",
    passed=True,
)
```

Each case contains:

```text
case_id
passed
```

The comparison layer intentionally uses only the information required for verdict-level regression analysis.

It does not depend directly on internal evaluation engine implementations or reporter models.

This keeps the regression comparison layer isolated from unrelated evaluation internals.

---

## Deterministic Case Matching

Baseline and candidate results are matched using:

```text
case_id
```

The case sets must be identical.

For example, this is valid:

```text
Baseline:
case-001
case-002
case-003

Candidate:
case-001
case-002
case-003
```

This is rejected:

```text
Baseline:
case-001
case-002

Candidate:
case-001
```

AI Test Lab does not silently ignore missing evaluation cases.

A missing case could otherwise hide a regression or create an invalid comparison.

---

## Duplicate Case Protection

Duplicate case IDs are rejected.

For example:

```text
case-001
case-001
```

is invalid.

Each evaluation case must have a unique identity within a run.

This prevents ambiguous comparisons.

---

## Deterministic Ordering

Regression comparison output is ordered deterministically by:

```text
case_id
```

Input order does not affect the final comparison order.

For example, these input sequences:

```text
case-003
case-001
case-002
```

and:

```text
case-002
case-003
case-001
```

still produce comparison output ordered as:

```text
case-001
case-002
case-003
```

This makes regression results stable and reproducible.

---

## Aggregate Regression Result

The comparison result includes aggregate counts:

```text
compared_count
unchanged_count
improved_count
regressed_count
```

It also exposes:

```python
has_regressions
```

Example:

```text
Compared:   10
Unchanged:   7
Improved:    1
Regressed:   2
```

produces:

```python
has_regressions == True
```

If no cases regress:

```python
has_regressions == False
```

---

## Example

Baseline:

```text
case-001 PASS
case-002 FAIL
case-003 PASS
case-004 FAIL
```

Candidate:

```text
case-001 FAIL
case-002 PASS
case-003 PASS
case-004 FAIL
```

Comparison:

```text
case-001 → REGRESSED
case-002 → IMPROVED
case-003 → UNCHANGED
case-004 → UNCHANGED
```

Aggregate result:

```text
Compared:   4
Unchanged:  2
Improved:   1
Regressed:  1
```

---

## Scope Boundary

Sprint 11.45 performs verdict-level regression comparison only.

It does not:

* compare numeric metric scores;
* calculate score deltas;
* calculate regression magnitude;
* define acceptable tolerance ranges;
* calculate statistical significance;
* determine confidence intervals;
* compare latency or cost;
* create historical regression trends;
* fail CI/CD pipelines;
* define quality-gate policy;
* generate regression dashboards;
* modify public report contracts.

Those capabilities belong to later regression and quality-gate layers.

---

## Why Numeric Score Comparison Is Deferred

A result such as:

```text
0.91 → 0.83
```

may look worse, but Sprint 11.45 intentionally does not decide whether that difference constitutes a meaningful regression.

That requires additional policy such as:

```text
thresholds
tolerances
metric semantics
statistical reliability
minimum meaningful delta
quality-gate rules
```

Those concerns should be implemented explicitly rather than mixed into the basic verdict comparison contract.

Sprint 11.45 therefore establishes the simpler and more deterministic foundation first.

---

## Tests

Added:

```text
tests/test_evaluation_run_regression_comparison.py
```

Coverage verifies:

* `PASS → FAIL` is classified as `REGRESSED`;
* `FAIL → PASS` is classified as `IMPROVED`;
* `PASS → PASS` is classified as `UNCHANGED`;
* `FAIL → FAIL` is classified as `UNCHANGED`;
* multiple evaluation cases are aggregated correctly;
* regression counts are calculated correctly;
* improvement counts are calculated correctly;
* unchanged counts are calculated correctly;
* `has_regressions` reflects the aggregate result;
* case comparison ordering is deterministic;
* regression-ineligible runs are rejected;
* missing candidate cases are rejected;
* missing baseline cases are rejected;
* duplicate case IDs are rejected;
* invalid case IDs are rejected;
* invalid verdict values are rejected;
* empty eligible runs can be compared deterministically.

---

## Verification Results

Full regression suite:

```text
398 passed in 10.07s
```

No existing behavior was broken.

---

## Architectural Result

AI Test Lab can now move from determining whether regression comparison is valid to actually identifying verdict-level changes.

The progression is now:

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
Regression Comparison
```

The responsibilities remain clearly separated:

```text
Reproducibility Verification
        ↓
Were the runs executed under equivalent conditions?

Regression Eligibility
        ↓
Is it valid to compare these runs?

Regression Comparison
        ↓
Which evaluation cases improved, regressed, or remained unchanged?
```

This separation keeps the architecture deterministic, testable, and extensible.

---

## Future Direction

Sprint 11.45 establishes the foundation for deeper regression engineering.

Future layers can build on this contract to support capabilities such as:

```text
Metric Score Comparison
        ↓
Regression Magnitude
        ↓
Tolerance Policies
        ↓
Statistical Reliability
        ↓
Regression Quality Gates
        ↓
CI/CD Enforcement
        ↓
Historical Regression Analysis
```

These future capabilities can reuse the comparison foundation introduced here without changing the basic meaning of verdict-level regression.

---

## Status

Sprint 11.45 complete.
