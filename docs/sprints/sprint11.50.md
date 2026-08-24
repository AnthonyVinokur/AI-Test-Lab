# Sprint 11.50 — Metric Regression Severity Classification

## Objective

Add a deterministic severity-classification layer for metric regressions that exceed or fall within configured tolerance.

Sprint 11.49 answered:

> Did the regression exceed its configured tolerance?

Sprint 11.50 answers the next question:

> How severe is the regression relative to that tolerance?

This sprint introduces regression severity classification while deliberately avoiding overall run verdicts, CI/CD enforcement, statistical significance, historical trend analysis, and governance escalation.

---

## Problem

Sprint 11.49 can determine whether a regression is:

```text
NOT_APPLICABLE
WITHIN_TOLERANCE
EXCEEDS_TOLERANCE
```

However, two regressions can both exceed tolerance while having very different practical significance.

Example:

```text
Tolerance: 0.01
Regression A magnitude: 0.015
Regression B magnitude: 0.080
```

Both exceed the configured tolerance, but Regression B is much more serious.

AI Test Lab therefore needs a deterministic severity layer that combines:

```text
regression magnitude
+
configured tolerance
+
tolerance status
```

to produce:

```text
regression severity
```

---

## Implementation

Added:

```text
src/evaluation_metric_regression_severity.py
```

The module introduces:

```python
MetricRegressionSeverity
EvaluationMetricRegressionSeverity
```

and:

```python
classify_metric_regression_severity()
```

---

## Severity Contract

Severity classification uses the explicit enum:

```python
class MetricRegressionSeverity(str, Enum):
    NOT_APPLICABLE = "not_applicable"
    ACCEPTABLE = "acceptable"
    MINOR = "minor"
    MAJOR = "major"
    CRITICAL = "critical"
```

The contract supports five outcomes.

### `NOT_APPLICABLE`

Used when tolerance evaluation itself is not applicable.

This normally means the metric did not regress.

### `ACCEPTABLE`

Used when the metric regressed but remains within configured tolerance.

### `MINOR`

Used when the regression exceeds tolerance but is no more than two times the configured tolerance.

```text
1.0 < ratio <= 2.0
```

### `MAJOR`

Used when the regression exceeds two times tolerance but is no more than five times tolerance.

```text
2.0 < ratio <= 5.0
```

### `CRITICAL`

Used when the regression exceeds five times the configured tolerance.

```text
ratio > 5.0
```

A positive regression against zero tolerance is also classified as `CRITICAL`.

---

## Severity Ratio

For exceeded-tolerance regressions where tolerance is greater than zero:

```text
ratio = regression magnitude / tolerance
```

Example:

```text
Regression magnitude: 0.030
Tolerance:            0.010
```

Therefore:

```text
ratio = 3.0
```

and the severity is:

```text
MAJOR
```

---

## Result Contract

Each severity evaluation records:

```text
magnitude
tolerance
ratio
severity
```

Example:

```python
EvaluationMetricRegressionSeverity(
    magnitude=0.03,
    tolerance=0.01,
    ratio=3.0,
    severity=MetricRegressionSeverity.MAJOR,
)
```

The contract is immutable using:

```python
@dataclass(frozen=True)
```

This preserves the evaluated severity evidence after creation.

---

## Zero-Tolerance Semantics

A configured tolerance of:

```text
0.0
```

means no regression is permitted.

If a positive regression occurs:

```text
magnitude > 0.0
tolerance == 0.0
```

the regression is classified as:

```text
CRITICAL
```

The ratio is stored as:

```text
None
```

because division by zero is undefined.

---

## Layering

Sprint 11.50 consumes the result produced by Sprint 11.49.

It does not recalculate:

```text
metric direction
metric movement
regression magnitude
tolerance status
```

The responsibility chain is:

```text
Sprint 11.47
Metric Direction Semantics
        ↓
Sprint 11.48
Metric Movement and Regression Magnitude
        ↓
Sprint 11.49
Metric Regression Tolerance Policy
        ↓
Sprint 11.50
Metric Regression Severity Classification
```

This preserves a narrow responsibility for each evaluation layer.

---

## Severity Examples

### Acceptable

```text
Magnitude: 0.005
Tolerance: 0.010
Ratio:     0.5
Severity:  ACCEPTABLE
```

### Minor

```text
Magnitude: 0.020
Tolerance: 0.010
Ratio:     2.0
Severity:  MINOR
```

### Major

```text
Magnitude: 0.030
Tolerance: 0.010
Ratio:     3.0
Severity:  MAJOR
```

### Critical

```text
Magnitude: 0.060
Tolerance: 0.010
Ratio:     6.0
Severity:  CRITICAL
```

---

## Tests

Added:

```text
tests/test_evaluation_metric_regression_severity.py
```

The focused test suite verifies:

```text
NOT_APPLICABLE classification
ACCEPTABLE classification
exact tolerance boundary
MINOR boundary
MAJOR classification
MAJOR upper boundary
CRITICAL classification
zero-tolerance regression behavior
invalid input rejection
```

Focused result:

```text
9 passed
```

Full repository regression result:

```text
484 passed in 10.62s
```

---

## Non-Goals

Sprint 11.50 deliberately does not implement:

```text
overall evaluation run verdicts
quality-gate decisions
CI/CD enforcement
statistical significance
historical trend analysis
weighted severity aggregation
governance escalation
compliance policy
```

Those responsibilities belong to later layers.

---

## Result

AI Test Lab can now progress from:

```text
Did the metric regress?
```

to:

```text
How much did it regress?
```

to:

```text
Did it exceed tolerance?
```

to:

```text
How severe is the regression?
```

This creates the deterministic evidence needed for a future regression quality-gate layer.
