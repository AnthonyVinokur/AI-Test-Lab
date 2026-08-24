# Sprint 11.49 — Metric Regression Tolerance Policy

## Objective

Add a deterministic tolerance-policy layer for evaluation metric regressions.

Sprint 11.48 answered:

> Did this metric improve, regress, or remain unchanged — and by how much?

Sprint 11.49 answers the next question:

> If the metric regressed, is the regression still within an explicitly allowed tolerance?

This sprint introduces regression tolerance evaluation while deliberately avoiding statistical significance, severity classification, quality-gate decisions, CI/CD enforcement, and historical trend analysis.

---

## Problem

Sprint 11.48 can identify a regression and calculate its magnitude.

Example:

```text
Baseline:  0.900
Candidate: 0.899

Movement:  REGRESSION
Magnitude: 0.001
```

However, that evidence alone does not answer whether the regression is acceptable.

A regression of:

```text
0.001
```

may be acceptable under a configured tolerance of:

```text
0.010
```

while a regression of:

```text
0.050
```

would exceed the same tolerance.

AI Test Lab therefore needs a deterministic layer that combines:

```text
metric movement
+
regression magnitude
+
configured tolerance
```

to produce:

```text
tolerance status
```

---

## Implementation

Added:

```text
src/evaluation_metric_tolerance.py
```

The module introduces:

```python
MetricToleranceStatus
EvaluationMetricTolerance
```

and:

```python
evaluate_metric_tolerance()
```

---

## Tolerance Status Contract

Tolerance evaluation uses the explicit enum:

```python
class MetricToleranceStatus(str, Enum):
    NOT_APPLICABLE = "not_applicable"
    WITHIN_TOLERANCE = "within_tolerance"
    EXCEEDS_TOLERANCE = "exceeds_tolerance"
```

The contract therefore supports exactly three outcomes.

### `NOT_APPLICABLE`

Used when the metric did not regress.

Examples:

```text
IMPROVEMENT
UNCHANGED
```

Tolerance policy is not applied because there is no regression to evaluate.

### `WITHIN_TOLERANCE`

Used when:

```text
regression magnitude <= configured tolerance
```

### `EXCEEDS_TOLERANCE`

Used when:

```text
regression magnitude > configured tolerance
```

---

## Tolerance Result Contract

Each tolerance evaluation records:

```text
magnitude
tolerance
status
```

Example:

```python
EvaluationMetricTolerance(
    magnitude=0.005,
    tolerance=0.010,
    status=MetricToleranceStatus.WITHIN_TOLERANCE,
)
```

The contract is immutable using:

```python
@dataclass(frozen=True)
```

This prevents evaluated tolerance evidence from being changed after creation.

---

## Regression-Only Semantics

Tolerance evaluation applies only when Sprint 11.48 classified the metric movement as:

```text
REGRESSION
```

The flow is:

```text
IMPROVEMENT
    ↓
NOT_APPLICABLE

UNCHANGED
    ↓
NOT_APPLICABLE

REGRESSION
    ↓
compare magnitude with tolerance
```

This separation is intentional.

Sprint 11.49 does not recalculate whether the metric improved or regressed.

That responsibility remains with:

```text
Sprint 11.48 — Metric Movement / Regression Magnitude
```

---

## Within-Tolerance Example

```text
Baseline:   0.900
Candidate:  0.895
Direction:  HIGHER_IS_BETTER

Movement:   REGRESSION
Magnitude:  0.005
Tolerance:  0.010
```

Because:

```text
0.005 <= 0.010
```

the result is:

```text
WITHIN_TOLERANCE
```

---

## Exceeds-Tolerance Example

```text
Baseline:   0.900
Candidate:  0.850
Direction:  HIGHER_IS_BETTER

Movement:   REGRESSION
Magnitude:  0.050
Tolerance:  0.010
```

Because:

```text
0.050 > 0.010
```

the result is:

```text
EXCEEDS_TOLERANCE
```

---

## Exact Boundary Semantics

A regression exactly equal to the configured tolerance is accepted.

Rule:

```text
magnitude == tolerance
    ↓
WITHIN_TOLERANCE
```

Example:

```text
Magnitude: 0.010
Tolerance: 0.010
```

Result:

```text
WITHIN_TOLERANCE
```

The tolerance therefore represents the maximum permitted regression magnitude.

---

## Floating-Point Boundary Handling

During implementation, testing exposed an important numerical issue.

The calculation:

```python
0.90 - 0.89
```

may be represented internally by Python as:

```text
0.010000000000000009
```

instead of exactly:

```text
0.01
```

A direct comparison could therefore incorrectly classify an exact logical boundary as exceeding tolerance.

Sprint 11.49 handles this using:

```python
math.isclose()
```

with an explicit small absolute tolerance:

```python
isclose(
    movement.magnitude,
    tolerance,
    rel_tol=0.0,
    abs_tol=1e-12,
)
```

This preserves deterministic boundary semantics while protecting the policy from binary floating-point representation artifacts.

---

## Lower-Is-Better Metrics

Sprint 11.49 does not need metric-direction logic.

Sprint 11.48 already resolves metric direction into movement.

Example:

```text
Latency metric

Baseline:   0.40
Candidate:  0.45
Direction:  LOWER_IS_BETTER
```

Sprint 11.48 produces:

```text
Movement:   REGRESSION
Magnitude:  0.05
```

Sprint 11.49 then evaluates:

```text
Tolerance: 0.02
```

Because:

```text
0.05 > 0.02
```

the result is:

```text
EXCEEDS_TOLERANCE
```

This keeps direction semantics and tolerance policy cleanly separated.

---

## Zero-Tolerance Semantics

A tolerance of:

```text
0.0
```

is valid.

It means:

```text
no regression is permitted
```

Therefore:

```text
Regression magnitude: 0.01
Tolerance:            0.00
```

produces:

```text
EXCEEDS_TOLERANCE
```

For non-regression movement:

```text
UNCHANGED
```

the tolerance remains:

```text
NOT_APPLICABLE
```

because no regression exists.

---

## Maximum Tolerance

The maximum valid tolerance is:

```text
1.0
```

Because evaluation metric scores are normalized to:

```text
0.0 <= score <= 1.0
```

a tolerance of:

```text
1.0
```

can accommodate the maximum possible regression magnitude.

---

## Tolerance Validation

Tolerance must be numeric and fall within:

```text
0.0 <= tolerance <= 1.0
```

Valid examples:

```text
0.0
0.01
0.10
0.50
1.0
```

Invalid examples:

```text
-0.01
1.01
"0.1"
None
[]
{}
True
False
```

Boolean values are explicitly rejected even though Python represents `bool` as a subclass of `int`.

---

## Movement Contract Validation

The `movement` argument must be an actual:

```python
EvaluationMetricMovement
```

instance.

Valid:

```python
EvaluationMetricMovement(...)
```

Invalid:

```text
"regression"
"improvement"
0.05
None
```

This ensures Sprint 11.49 consumes the trusted Sprint 11.48 movement contract instead of accepting ambiguous free-form data.

---

## Important Semantic Boundary

Sprint 11.49 determines:

```text
Did a regression remain within the configured tolerance?
```

It does not determine:

```text
Should the evaluation run fail?
```

For example:

```text
Movement:   REGRESSION
Magnitude:  0.05
Tolerance:  0.02

Status:     EXCEEDS_TOLERANCE
```

Sprint 11.49 stops there.

It does not automatically produce:

```text
FAIL
```

or:

```text
BLOCK DEPLOYMENT
```

Those decisions belong to later quality-gate and CI/CD enforcement layers.

---

## Scope Boundary

Sprint 11.49 performs deterministic metric-regression tolerance evaluation only.

It does not:

* calculate statistical significance;
* calculate confidence intervals;
* perform repeated-run statistical analysis;
* classify regression severity;
* define warning levels;
* define overall evaluation-run verdicts;
* define pass/fail quality gates;
* fail CI/CD pipelines;
* block deployments;
* perform historical trend analysis;
* modify public report contracts;
* use an LLM to interpret tolerance results.

These responsibilities belong to later regression-engineering layers.

---

## Tests

Added:

```text
tests/test_evaluation_metric_tolerance.py
```

Coverage verifies:

* regression below tolerance is within tolerance;
* regression exactly at tolerance is within tolerance;
* regression above tolerance exceeds tolerance;
* improvement is not applicable;
* unchanged movement is not applicable;
* lower-is-better regression consumes existing movement semantics;
* zero tolerance rejects any actual regression;
* zero tolerance is valid;
* tolerance `1.0` is valid;
* negative tolerance is rejected;
* tolerance above `1.0` is rejected;
* non-numeric tolerance is rejected;
* boolean tolerance is rejected;
* invalid movement types are rejected;
* result records regression magnitude;
* result records configured tolerance;
* result contract is immutable;
* repeated evaluation is deterministic;
* the correct result contract type is returned;
* floating-point equality boundaries are handled correctly.

Focused verification:

```text
22 passed in 0.08s
```

Full regression suite:

```text
475 passed in 10.84s
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
        ↓
Metric Regression Tolerance Policy
```

The responsibilities remain separated:

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

Metric Regression Tolerance Policy
        ↓
If it regressed, is the regression still acceptable under the configured tolerance?
```

Sprint 11.49 therefore introduces policy evaluation without yet introducing statistical reliability or enforcement.

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
Metric Regression Tolerance Policy
        ↓
Statistical Reliability
        ↓
Regression Quality Gate
        ↓
CI/CD Enforcement
        ↓
Historical Regression Analysis
```

The next layer can determine how confidently AI Test Lab should interpret observed score movement when evaluation metrics may vary across repeated runs.

This becomes especially important for probabilistic AI evaluation, where a small score difference may result from normal measurement variation rather than a meaningful product regression.

---

## Status

Sprint 11.49 complete.
