# Sprint 11.48 — Evaluation Metric Movement / Regression Magnitude

## Objective

Add deterministic metric movement classification and regression magnitude calculation for evaluation metrics.

Sprint 11.46 answered:

> How did individual evaluation metric scores change?

Sprint 11.47 answered:

> For this metric, does a higher or lower value represent better performance?

Sprint 11.48 answers the next question:

> Did this metric improve, regress, or remain unchanged — and by how much?

This sprint combines raw score deltas with explicit metric direction semantics while deliberately avoiding tolerance policy, statistical significance, quality-gate decisions, and CI/CD enforcement.

---

## Problem

A raw numeric delta is not enough to determine whether a metric changed favorably.

For example:

```text
answer_relevancy

Baseline:  0.80
Candidate: 0.90
Delta:    +0.10
```

If the metric is:

```text
HIGHER_IS_BETTER
```

the movement is an improvement.

However:

```text
synthetic_latency

Baseline:  0.80
Candidate: 0.60
Delta:    -0.20
```

If the metric is:

```text
LOWER_IS_BETTER
```

the negative delta is also an improvement.

AI Test Lab therefore needs a deterministic layer that combines:

```text
score delta
+
metric direction
```

to produce:

```text
movement classification
+
movement magnitude
```

---

## Implementation

Added:

```text
src/evaluation_metric_movement.py
```

The module introduces:

```python
MetricMovement
EvaluationMetricMovement
```

and:

```python
classify_metric_movement()
```

---

## Metric Movement Contract

Movement is represented using:

```python
class MetricMovement(str, Enum):
    IMPROVEMENT = "improvement"
    REGRESSION = "regression"
    UNCHANGED = "unchanged"
```

This prevents metric movement from being represented using ambiguous free-form strings.

The supported movement outcomes are explicit and finite.

---

## Movement Result Contract

Each movement result records:

```text
baseline_score
candidate_score
delta
magnitude
direction
movement
```

Example:

```python
EvaluationMetricMovement(
    baseline_score=0.80,
    candidate_score=0.90,
    delta=0.10,
    magnitude=0.10,
    direction=MetricDirection.HIGHER_IS_BETTER,
    movement=MetricMovement.IMPROVEMENT,
)
```

The contract is immutable using:

```python
@dataclass(frozen=True)
```

This prevents calculated movement evidence from being changed unexpectedly after creation.

---

## Delta Calculation

The raw metric delta remains:

```text
delta = candidate_score - baseline_score
```

Examples:

```text
0.80 → 0.90 = +0.10
0.90 → 0.80 = -0.10
0.85 → 0.85 =  0.00
```

The sign is preserved because it remains useful evidence about the numerical direction of change.

---

## Magnitude Calculation

Movement magnitude is calculated using:

```text
magnitude = abs(delta)
```

Therefore magnitude is always non-negative.

Examples:

```text
Delta: +0.10 → Magnitude: 0.10
Delta: -0.10 → Magnitude: 0.10
Delta:  0.00 → Magnitude: 0.00
```

Magnitude describes only the size of the movement.

It does not determine whether that movement is acceptable.

---

## Higher-Is-Better Semantics

For metrics with:

```text
HIGHER_IS_BETTER
```

the rules are:

```text
candidate > baseline → IMPROVEMENT
candidate < baseline → REGRESSION
candidate = baseline → UNCHANGED
```

Example:

```text
Baseline:  0.80
Candidate: 0.90
Direction: HIGHER_IS_BETTER

Delta:     +0.10
Magnitude:  0.10
Movement:   IMPROVEMENT
```

A decrease reverses the outcome:

```text
Baseline:  0.90
Candidate: 0.80
Direction: HIGHER_IS_BETTER

Delta:     -0.10
Magnitude:  0.10
Movement:   REGRESSION
```

---

## Lower-Is-Better Semantics

For metrics with:

```text
LOWER_IS_BETTER
```

the rules are:

```text
candidate < baseline → IMPROVEMENT
candidate > baseline → REGRESSION
candidate = baseline → UNCHANGED
```

Example:

```text
Baseline:  0.80
Candidate: 0.60
Direction: LOWER_IS_BETTER

Delta:     -0.20
Magnitude:  0.20
Movement:   IMPROVEMENT
```

An increase reverses the outcome:

```text
Baseline:  0.60
Candidate: 0.80
Direction: LOWER_IS_BETTER

Delta:     +0.20
Magnitude:  0.20
Movement:   REGRESSION
```

---

## Unchanged Semantics

If:

```text
candidate_score == baseline_score
```

the movement is:

```text
UNCHANGED
```

regardless of metric direction.

Example:

```text
Baseline:  0.70
Candidate: 0.70

Delta:      0.00
Magnitude:  0.00
Movement:   UNCHANGED
```

---

## Score Validation

Scores must be numeric values within:

```text
0.0 <= score <= 1.0
```

Examples of valid values:

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
"0.50"
None
```

Boolean values are also rejected even though Python represents `bool` as a subclass of `int`.

---

## Direction Validation

The direction argument must be an actual:

```python
MetricDirection
```

member.

Valid:

```python
MetricDirection.HIGHER_IS_BETTER
MetricDirection.LOWER_IS_BETTER
```

Invalid:

```text
"higher_is_better"
"lower_is_better"
```

This ensures movement classification uses the explicit Sprint 11.47 metric-direction contract rather than free-form strings.

---

## Boundary Scores

The contract supports the full normalized score range.

Example:

```text
Baseline:  0.0
Candidate: 1.0
Direction: HIGHER_IS_BETTER

Delta:      1.0
Magnitude:  1.0
Movement:   IMPROVEMENT
```

This verifies deterministic behavior at the score boundaries.

---

## Important Semantic Boundary

Sprint 11.48 determines:

```text
Did the metric improve, regress, or remain unchanged?

How large was the movement?
```

It does not determine:

```text
Is the regression acceptable?
```

For example:

```text
Baseline:  0.900
Candidate: 0.899
Direction: HIGHER_IS_BETTER
```

Sprint 11.48 reports:

```text
Movement:  REGRESSION
Magnitude: 0.001
```

It does not decide whether a regression of:

```text
0.001
```

should cause a warning or failure.

That decision belongs to a later tolerance-policy layer.

---

## Scope Boundary

Sprint 11.48 performs deterministic metric movement classification and magnitude calculation only.

It does not:

* define regression tolerances;
* define acceptable regression limits;
* define warning thresholds;
* define severity levels;
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
tests/test_evaluation_metric_movement.py
```

Coverage verifies:

* higher-is-better increase is classified as improvement;
* higher-is-better decrease is classified as regression;
* higher-is-better equality is classified as unchanged;
* lower-is-better decrease is classified as improvement;
* lower-is-better increase is classified as regression;
* lower-is-better equality is classified as unchanged;
* improvement magnitude is positive;
* regression magnitude is positive;
* unchanged magnitude is zero;
* raw delta preserves its sign;
* scores below `0.0` are rejected;
* scores above `1.0` are rejected;
* non-numeric baseline scores are rejected;
* non-numeric candidate scores are rejected;
* boolean scores are rejected;
* invalid direction values are rejected;
* boundary scores are supported;
* movement behavior is deterministic.

Focused verification:

```text
18 passed in 0.10s
```

Full regression suite:

```text
453 passed in 9.88s
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
        ↓
Metric Movement / Regression Magnitude
```

The responsibilities remain separate:

```text
Metric Score Comparison
        ↓
What changed numerically?

Metric Direction Semantics
        ↓
Which numerical direction represents better performance?

Metric Movement / Regression Magnitude
        ↓
Did the metric improve or regress, and by how much?
```

Sprint 11.48 therefore adds semantic interpretation and magnitude without introducing regression policy.

---

## Future Direction

The regression-engineering sequence can now continue toward:

```text
Metric Score Comparison
        ↓
Metric Direction Semantics
        ↓
Metric Movement / Regression Magnitude
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

The next layer can use movement classification and magnitude to determine whether a regression exceeds an explicitly defined acceptable tolerance without changing the existing comparison or semantic contracts.

---

## Status

Sprint 11.48 complete.
