# Sprint 11.51 — Metric Regression Quality-Gate Decision

## Objective

Add a deterministic per-metric quality-gate decision layer on top of metric regression severity.

Sprint 11.50 answered:

> How severe is the metric regression?

Sprint 11.51 answers the next question:

> Should this metric be allowed through the regression quality gate?

This sprint intentionally evaluates one metric at a time. It does not yet calculate an overall evaluation-run verdict or enforce CI/CD behavior.

---

## Problem

Sprint 11.50 introduced deterministic regression severity values:

```text
NOT_APPLICABLE
ACCEPTABLE
MINOR
MAJOR
CRITICAL
```

Severity tells AI Test Lab how serious a regression is, but severity by itself does not answer whether that regression is acceptable under a particular quality policy.

For example:

```text
Metric regression severity: MINOR
```

One policy may allow it:

```text
maximum allowed severity: MINOR
decision: PASS
```

A stricter policy may reject it:

```text
maximum allowed severity: ACCEPTABLE
decision: FAIL
```

AI Test Lab therefore needs a separate policy layer that converts severity evidence into a gate decision.

---

## Implementation

Added:

```text
src/evaluation_metric_regression_gate.py
```

The module introduces:

```python
MetricRegressionGateDecision
EvaluationMetricRegressionGate
```

and:

```python
evaluate_metric_regression_gate()
```

---

## Gate Decision Contract

The gate decision uses the explicit enum:

```python
class MetricRegressionGateDecision(str, Enum):
    NOT_APPLICABLE = "not_applicable"
    PASS = "pass"
    FAIL = "fail"
```

The contract supports three outcomes.

### `NOT_APPLICABLE`

Used when the severity evaluation itself is not applicable.

Example:

```text
severity: NOT_APPLICABLE
decision: NOT_APPLICABLE
```

### `PASS`

Used when the metric severity is equal to or less severe than the configured maximum allowed severity.

Example:

```text
severity: MINOR
maximum allowed severity: MINOR
decision: PASS
```

### `FAIL`

Used when the metric severity is more severe than the configured maximum allowed severity.

Example:

```text
severity: MAJOR
maximum allowed severity: MINOR
decision: FAIL
```

---

## Severity Ordering

Sprint 11.51 defines deterministic severity ordering:

```text
ACCEPTABLE < MINOR < MAJOR < CRITICAL
```

Internally:

```python
_SEVERITY_RANK = {
    MetricRegressionSeverity.ACCEPTABLE: 0,
    MetricRegressionSeverity.MINOR: 1,
    MetricRegressionSeverity.MAJOR: 2,
    MetricRegressionSeverity.CRITICAL: 3,
}
```

This allows gate evaluation to compare:

```text
actual severity
```

against:

```text
maximum allowed severity
```

without recalculating regression evidence.

---

## Gate Rule

The core rule is:

```text
actual severity <= maximum allowed severity
```

then:

```text
PASS
```

Otherwise:

```text
FAIL
```

Example:

```text
Actual severity:        MAJOR
Maximum allowed:        MINOR

MAJOR > MINOR

Decision: FAIL
```

Another example:

```text
Actual severity:        MINOR
Maximum allowed:        MAJOR

MINOR < MAJOR

Decision: PASS
```

---

## Result Contract

Each gate evaluation records:

```text
severity
maximum allowed severity
decision
```

Example:

```python
EvaluationMetricRegressionGate(
    severity=MetricRegressionSeverity.MINOR,
    max_allowed_severity=MetricRegressionSeverity.MINOR,
    decision=MetricRegressionGateDecision.PASS,
)
```

The result contract is immutable using:

```python
@dataclass(frozen=True)
```

This preserves the gate evidence after evaluation.

---

## Invalid Policy

`NOT_APPLICABLE` cannot be used as the configured maximum allowed severity.

This is rejected:

```python
max_allowed_severity=MetricRegressionSeverity.NOT_APPLICABLE
```

because `NOT_APPLICABLE` represents the absence of a severity evaluation, not an acceptable policy threshold.

The evaluator raises:

```text
ValueError
```

with:

```text
max_allowed_severity cannot be NOT_APPLICABLE
```

---

## Layering

Sprint 11.51 consumes the severity result produced by Sprint 11.50.

It does not recalculate:

```text
metric direction
metric movement
regression magnitude
tolerance
tolerance status
severity ratio
severity
```

The responsibility chain is now:

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
        ↓
Sprint 11.51
Metric Regression Quality-Gate Decision
```

Each layer has one narrow responsibility.

---

## Examples

### Not Applicable

```text
Severity:             NOT_APPLICABLE
Maximum allowed:      MINOR
Decision:             NOT_APPLICABLE
```

### Acceptable Pass

```text
Severity:             ACCEPTABLE
Maximum allowed:      ACCEPTABLE
Decision:             PASS
```

### Minor Pass

```text
Severity:             MINOR
Maximum allowed:      MINOR
Decision:             PASS
```

### Minor Fail Under Strict Policy

```text
Severity:             MINOR
Maximum allowed:      ACCEPTABLE
Decision:             FAIL
```

### Major Pass Under Permissive Policy

```text
Severity:             MAJOR
Maximum allowed:      MAJOR
Decision:             PASS
```

### Major Fail

```text
Severity:             MAJOR
Maximum allowed:      MINOR
Decision:             FAIL
```

### Critical Fail

```text
Severity:             CRITICAL
Maximum allowed:      MAJOR
Decision:             FAIL
```

---

## Tests

Added:

```text
tests/test_evaluation_metric_regression_gate.py
```

The focused test suite verifies:

```text
NOT_APPLICABLE behavior
ACCEPTABLE pass behavior
MINOR pass behavior
MAJOR fail behavior
CRITICAL fail behavior
strict ACCEPTABLE policy
permissive MAJOR policy
CRITICAL rejection under MAJOR policy
invalid NOT_APPLICABLE policy rejection
immutable result contract
```

Focused result:

```text
10 passed in 0.07s
```

Full repository regression result:

```text
494 passed in 11.42s
```

---

## Non-Goals

Sprint 11.51 deliberately does not implement:

```text
overall evaluation-run verdict
multiple-metric aggregation
weighted severity aggregation
profile configuration wiring
CI/CD enforcement
pipeline blocking
statistical significance
historical trend analysis
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

to:

```text
Should this metric pass the regression quality gate?
```

Sprint 11.51 establishes the deterministic per-metric policy decision needed before AI Test Lab can safely aggregate multiple metric decisions into an overall evaluation-run quality gate.
