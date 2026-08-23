# Sprint 11.46 — Evaluation Run Metric Score Comparison

## Objective

Add deterministic metric-score comparison between baseline and candidate
evaluation runs.

Sprint 11.45 answered:

> Which evaluation cases improved, regressed, or remained unchanged at the
> verdict level?

Sprint 11.46 answers the next question:

> How did individual evaluation metric scores change?

This sprint introduces score-level comparison while deliberately avoiding
regression policy, tolerance, statistical significance, or CI/CD decisions.

---

## Problem

Verdict-level comparison can identify changes such as:

```text
PASS → FAIL
FAIL → PASS
```

However, evaluation systems also produce numeric metric scores.

For example:

```text
answer_relevancy

Baseline:  0.80
Candidate: 0.90
```

AI Test Lab needs a deterministic way to represent this change.

The fundamental calculation is:

```text
delta = candidate_score - baseline_score
```

Therefore:

```text
0.80 → 0.90 = +0.10
0.90 → 0.75 = -0.15
0.85 → 0.85 =  0.00
```

Sprint 11.46 records these facts without deciding whether the change is
acceptable.

---

## Implementation

Added:

```text
src/evaluation_run_metric_comparison.py
```

The module introduces:

```python
EvaluationRunMetricResult
EvaluationRunMetricComparison
EvaluationRunMetricComparisonResult
```

and:

```python
compare_evaluation_run_metrics()
```

---

## Metric Result Contract

Each metric result is identified by:

```text
case_id
metric_name
```

and contains:

```text
score
```

Example:

```python
EvaluationRunMetricResult(
    case_id="case-001",
    metric_name="answer_relevancy",
    score=0.80,
)
```

The combination:

```text
(case_id, metric_name)
```

acts as the deterministic comparison key.

---

## Score Validation

Metric scores must be numeric values within:

```text
0.0 <= score <= 1.0
```

Examples of valid scores:

```text
0.0
0.50
0.87
1.0
```

Examples rejected by the contract:

```text
-0.01
1.01
"0.80"
```

Boolean values are also rejected even though Python represents `bool` as a
subclass of `int`.

---

## Metric Identity Validation

Both:

```text
case_id
metric_name
```

must be non-empty strings.

Empty values such as:

```text
""
"   "
```

are rejected.

This prevents ambiguous metric identities from entering regression analysis.

---

## Metric Set Matching

Baseline and candidate metric sets must be identical.

For example, this is valid:

```text
Baseline:
case-001 / answer_relevancy
case-001 / faithfulness

Candidate:
case-001 / answer_relevancy
case-001 / faithfulness
```

This is rejected:

```text
Baseline:
case-001 / answer_relevancy
case-001 / faithfulness

Candidate:
case-001 / answer_relevancy
```

AI Test Lab does not silently ignore missing metrics.

A missing metric could otherwise hide important evidence or produce an
incomplete comparison.

---

## Duplicate Metric Protection

Duplicate metric identities are rejected.

For example:

```text
case-001 / answer_relevancy
case-001 / answer_relevancy
```

is invalid within one metric result collection.

Without this protection, dictionary indexing could silently overwrite one
result with another.

Sprint 11.46 explicitly rejects that ambiguity.

---

## Deterministic Ordering

Metric comparisons are ordered using:

```text
(case_id, metric_name)
```

Input order therefore does not affect output order.

Example input:

```text
case-002 / faithfulness
case-001 / answer_relevancy
```

produces:

```text
case-001 / answer_relevancy
case-002 / faithfulness
```

This keeps regression evidence reproducible.

---

## Delta Calculation

For every matching metric:

```text
delta = candidate_score - baseline_score
```

Example:

```text
Baseline:  0.80
Candidate: 0.90

Delta: +0.10
```

A negative delta is also preserved:

```text
Baseline:  0.90
Candidate: 0.75

Delta: -0.15
```

Sprint 11.46 treats the delta as evidence only.

It does not assign policy meaning to the sign or magnitude.

---

## Important Semantic Boundary

Sprint 11.46 intentionally does not classify a positive delta as an
improvement or a negative delta as a regression.

Different metrics can have different semantics.

For some measurements:

```text
higher is better
```

For others:

```text
lower is better
```

Examples outside the current contract could include latency, cost, error
rates, or other metrics whose interpretation differs from normalized quality
scores.

Metric direction and acceptable change therefore belong in a later policy
layer.

---

## Empty Comparisons

Two empty metric result sets can be compared deterministically.

The result contains:

```text
metric_comparisons = ()
```

This preserves predictable behavior without inventing metric evidence.

---

## Input Contract Protection

The comparison function requires:

```text
tuple[EvaluationRunMetricResult, ...]
```

for both baseline and candidate inputs.

Non-tuple containers are rejected.

Collections containing objects other than:

```text
EvaluationRunMetricResult
```

are also rejected.

This prevents malformed data from entering the comparison layer.

---

## Scope Boundary

Sprint 11.46 performs deterministic normalized metric-score comparison only.

It does not:

* define regression tolerances;
* classify metric deltas as acceptable or unacceptable;
* define metric directionality policy;
* calculate statistical significance;
* calculate confidence intervals;
* perform repeated-run statistical analysis;
* compare latency or cost semantics;
* define quality gates;
* fail CI/CD pipelines;
* generate historical trends;
* modify public report contracts;
* use an LLM to interpret regression results.

These responsibilities belong to later regression-engineering layers.

---

## Tests

Added:

```text
tests/test_evaluation_run_metric_comparison.py
```

Coverage verifies:

* score increases produce positive deltas;
* score decreases produce negative deltas;
* equal scores produce zero deltas;
* multiple metrics are ordered deterministically;
* missing candidate metrics are rejected;
* missing baseline metrics are rejected;
* duplicate metric identities are rejected;
* empty case IDs are rejected;
* whitespace-only case IDs are rejected;
* empty metric names are rejected;
* whitespace-only metric names are rejected;
* scores below 0.0 are rejected;
* scores above 1.0 are rejected;
* non-numeric scores are rejected;
* empty metric sets compare deterministically;
* baseline input must be a tuple;
* candidate input must be a tuple;
* baseline collections must contain metric-result objects;
* candidate collections must contain metric-result objects.

Focused verification:

```text
19 passed
```

Full regression suite:

```text
417 passed in 9.93s
```

No existing behavior was broken.

---

## Architectural Result

The regression-engineering pipeline now progresses through:

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
Verdict Regression Comparison
        ↓
Metric Score Comparison
```

The responsibilities remain separate:

```text
Regression Eligibility
        ↓
Can these runs legitimately be compared?

Verdict Regression Comparison
        ↓
Which test verdicts changed?

Metric Score Comparison
        ↓
How did individual metric scores change?
```

Sprint 11.46 therefore adds deeper regression evidence without mixing
comparison mechanics with regression policy.

---

## Future Direction

The metric comparison contract creates the foundation for:

```text
Metric Score Comparison
        ↓
Metric Direction Semantics
        ↓
Regression Magnitude
        ↓
Tolerance Policy
        ↓
Statistical Reliability
        ↓
Regression Quality Gate
        ↓
CI/CD Enforcement
        ↓
Historical Regression Analysis
```

Future layers can interpret the evidence produced by Sprint 11.46 without
changing its deterministic comparison contract.

---

## Status

Sprint 11.46 complete.
