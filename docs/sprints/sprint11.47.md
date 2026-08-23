# Sprint 11.47 — Metric Direction Semantics

## Objective

Add deterministic metric-direction semantics for evaluation metrics.

Sprint 11.46 answered:

> How did individual evaluation metric scores change?

For example:

```text
answer_relevancy

Baseline:  0.80
Candidate: 0.90
Delta:    +0.10
```

However, a numeric delta alone does not explain whether the change represents better or worse performance.

Sprint 11.47 answers the next question:

> For this metric, does a higher or lower value represent better performance?

This sprint introduces explicit metric direction semantics while deliberately avoiding tolerance policy, regression thresholds, statistical analysis, and CI/CD decisions.

---

## Problem

Different metrics can have different optimization directions.

For some metrics:

```text
higher is better
```

For others:

```text
lower is better
```

For example:

```text
answer_relevancy

0.80 → 0.90
```

If higher values represent better performance, this movement is favorable.

However:

```text
synthetic_latency

1.20 → 0.90
```

If lower values represent better performance, the negative delta is also favorable.

Therefore, raw numeric delta alone is insufficient.

AI Test Lab needs an explicit deterministic contract describing how each metric should be interpreted.

---

## Implementation

Added:

```text
src/evaluation_metric_direction.py
```

The module introduces:

```python
MetricDirection
EvaluationMetricDirection
```

and:

```python
metric_direction_catalog()
direction_for_metric()
```

---

## Metric Direction Contract

Metric direction is represented using:

```python
class MetricDirection(str, Enum):
    HIGHER_IS_BETTER = "higher_is_better"
    LOWER_IS_BETTER = "lower_is_better"
```

This prevents direction semantics from being represented using ambiguous free-form strings.

The supported semantic directions are therefore explicit and finite.

---

## Metric Direction Definition

Each direction definition binds:

```text
metric_name
direction
```

Example:

```python
EvaluationMetricDirection(
    metric_name="answer_relevancy",
    direction=MetricDirection.HIGHER_IS_BETTER,
)
```

The contract is immutable using:

```python
@dataclass(frozen=True)
```

This prevents direction definitions from changing unexpectedly after creation.

---

## Default Metric Directions

Sprint 11.47 defines direction semantics for the current normalized quality metrics:

```text
answer_relevancy → HIGHER_IS_BETTER
faithfulness     → HIGHER_IS_BETTER
```

These definitions state only how the metric should be interpreted.

They do not define acceptable regression magnitude.

---

## Higher-Is-Better Semantics

For metrics marked:

```text
HIGHER_IS_BETTER
```

a numerically larger score represents better metric performance.

Example:

```text
Baseline:  0.80
Candidate: 0.90
Delta:    +0.10
```

The direction contract establishes that increasing values are favorable.

Sprint 11.47 does not yet classify the change as an acceptable or unacceptable regression outcome.

---

## Lower-Is-Better Semantics

For metrics marked:

```text
LOWER_IS_BETTER
```

a numerically smaller value represents better metric performance.

Example:

```text
Baseline:  1.20
Candidate: 0.90
Delta:    -0.30
```

The direction contract establishes that decreasing values are favorable.

A controlled synthetic metric is used in testing so that lower-is-better semantics can be verified without prematurely expanding the production metric catalog.

---

## Metric Name Validation

Metric names must be non-empty strings.

Rejected examples include:

```text
""
"   "
123
```

This prevents ambiguous or malformed metric identities from entering the semantic layer.

---

## Direction Type Validation

Direction values must be actual:

```python
MetricDirection
```

members.

For example, this is valid:

```python
MetricDirection.HIGHER_IS_BETTER
```

A free-form value such as:

```text
"higher_is_better"
```

is rejected when supplied directly to the metric definition contract.

This ensures callers use the explicit enum contract.

---

## Deterministic Catalog

The function:

```python
metric_direction_catalog()
```

returns metric direction definitions ordered deterministically by:

```text
metric_name
```

Therefore input order does not affect output order.

Example input:

```text
z_metric
a_metric
```

produces:

```text
a_metric
z_metric
```

This keeps semantic configuration reproducible.

---

## Duplicate Protection

Duplicate metric direction definitions are rejected.

For example:

```text
quality → HIGHER_IS_BETTER
quality → LOWER_IS_BETTER
```

is invalid.

Without this protection, the same metric could have conflicting semantic meaning.

Sprint 11.47 rejects that ambiguity explicitly.

---

## Direction Lookup

The function:

```python
direction_for_metric()
```

resolves the semantic direction for a metric.

Example:

```python
direction_for_metric("answer_relevancy")
```

returns:

```python
MetricDirection.HIGHER_IS_BETTER
```

Unknown metrics are rejected rather than guessed.

Example:

```text
unknown
```

produces an explicit error.

AI Test Lab therefore never silently assumes whether higher or lower values are preferable.

---

## Custom Catalog Support

Direction lookup can operate against an explicitly supplied metric-direction catalog.

Example:

```python
EvaluationMetricDirection(
    metric_name="synthetic_latency",
    direction=MetricDirection.LOWER_IS_BETTER,
)
```

This allows deterministic testing and future extension while keeping the default production catalog narrow.

---

## Empty Catalog Behavior

An empty metric-direction tuple is valid.

Calling:

```python
metric_direction_catalog(())
```

returns:

```text
()
```

This preserves deterministic behavior without inventing metric semantics.

---

## Important Semantic Boundary

Sprint 11.47 defines metric direction only.

It does not determine whether a change should fail regression policy.

For example:

```text
answer_relevancy

0.90 → 0.89
```

The direction layer can establish that this moved in an unfavorable direction because:

```text
HIGHER_IS_BETTER
```

However, Sprint 11.47 does not decide whether a decrease of:

```text
0.01
```

is significant enough to matter.

That requires later layers such as:

```text
regression magnitude
tolerance policy
statistical reliability
quality gates
```

This separation prevents policy decisions from contaminating deterministic metric semantics.

---

## Scope Boundary

Sprint 11.47 performs deterministic metric-direction definition and lookup only.

It does not:

* calculate score deltas;
* classify tolerance;
* define acceptable regression thresholds;
* calculate regression severity;
* calculate statistical significance;
* calculate confidence intervals;
* perform repeated-run statistical analysis;
* define quality gates;
* fail CI/CD pipelines;
* generate historical trends;
* modify public report contracts;
* use an LLM to interpret metric movement.

These responsibilities belong to later regression-engineering layers.

---

## Tests

Added:

```text
tests/test_evaluation_metric_direction.py
```

Coverage verifies:

* higher-is-better direction is supported;
* lower-is-better direction is supported;
* empty metric names are rejected;
* whitespace-only metric names are rejected;
* non-string metric names are rejected;
* invalid direction types are rejected;
* answer relevancy resolves to higher-is-better;
* faithfulness resolves to higher-is-better;
* unknown metrics are rejected;
* empty lookup names are rejected;
* non-string lookup names are rejected;
* catalog ordering is deterministic;
* input order does not affect catalog output;
* duplicate metric direction definitions are rejected;
* catalog input must be a tuple;
* catalog entries must be metric-direction objects;
* custom lower-is-better metrics resolve correctly;
* empty catalogs are valid.

Focused verification:

```text
18 passed in 0.08s
```

Full regression suite:

```text
435 passed in 10.69s
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
        ↓
Metric Direction Semantics
```

The responsibilities remain separate:

```text
Metric Score Comparison
        ↓
What changed numerically?

Metric Direction Semantics
        ↓
Which numerical direction represents better performance?
```

Sprint 11.47 therefore adds interpretation semantics without introducing regression policy.

---

## Future Direction

The regression-engineering sequence can now continue toward:

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

The next layer can use both raw score deltas and metric direction semantics to determine the magnitude and favorability of metric movement without changing either existing contract.

---

## Status

Sprint 11.47 complete.
