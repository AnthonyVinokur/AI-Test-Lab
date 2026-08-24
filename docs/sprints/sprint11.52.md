# Sprint 11.52 — Evaluation Run Regression Gate

## Objective

Add a deterministic evaluation-run regression gate that combines per-metric regression gate decisions into one overall run-level decision.

Sprint 11.51 answered:

> Should this individual metric be allowed through the regression quality gate?

Sprint 11.52 answers the next question:

> Did the evaluation run as a whole pass the regression quality gate?

This sprint intentionally performs aggregation only.

It does not yet enforce CI/CD behavior or terminate execution based on the result.

---

## Problem

Sprint 11.51 introduced deterministic per-metric regression gate decisions:

```text
NOT_APPLICABLE
PASS
FAIL
```

An evaluation run may contain several metrics.

For example:

```text
answer_relevancy → PASS
faithfulness     → PASS
toxicity         → FAIL
latency          → PASS
```

Each individual metric can now be evaluated correctly, but AI Test Lab still needs a single answer for the evaluation run:

```text
Did this run pass the regression gate?
```

Sprint 11.52 adds that aggregation layer.

---

## Implementation

Added:

```text
src/evaluation_run_regression_gate.py
```

The module introduces:

```python
EvaluationRunRegressionGateDecision
EvaluationRunRegressionGate
```

and:

```python
evaluate_run_regression_gate()
```

---

## Run-Level Decision Contract

The evaluation-run gate uses:

```python
class EvaluationRunRegressionGateDecision(str, Enum):
    NOT_APPLICABLE = "not_applicable"
    PASS = "pass"
    FAIL = "fail"
```

The run therefore has three possible outcomes.

### `FAIL`

The evaluation run fails when at least one metric gate decision is:

```text
FAIL
```

Example:

```text
PASS
PASS
FAIL
PASS
```

produces:

```text
FAIL
```

A single failed regression metric is enough to fail the overall regression gate.

---

### `PASS`

The evaluation run passes when:

```text
no metric failed
```

and at least one metric produced:

```text
PASS
```

Example:

```text
PASS
NOT_APPLICABLE
PASS
```

produces:

```text
PASS
```

`NOT_APPLICABLE` metrics do not cause the run to fail.

---

### `NOT_APPLICABLE`

The evaluation run is not applicable when no metric produced either a pass or fail decision.

Example:

```text
NOT_APPLICABLE
NOT_APPLICABLE
```

produces:

```text
NOT_APPLICABLE
```

An empty collection of metric decisions also produces:

```text
NOT_APPLICABLE
```

because there is no regression evidence from which to produce a pass or fail decision.

---

## Deterministic Aggregation Rule

Sprint 11.52 uses the following rule:

```text
If any metric decision is FAIL:
    overall decision = FAIL

Else if any metric decision is PASS:
    overall decision = PASS

Else:
    overall decision = NOT_APPLICABLE
```

The precedence is therefore:

```text
FAIL
 ↓
PASS
 ↓
NOT_APPLICABLE
```

This guarantees deterministic run-level behavior.

---

## Result Contract

Each run-level regression gate evaluation records:

```text
decision
total_metrics
passed_metrics
failed_metrics
not_applicable_metrics
```

Example:

```python
EvaluationRunRegressionGate(
    decision=EvaluationRunRegressionGateDecision.FAIL,
    total_metrics=4,
    passed_metrics=2,
    failed_metrics=1,
    not_applicable_metrics=1,
)
```

This preserves both the overall decision and the evidence used to produce it.

---

## Example

Given:

```text
Metric 1 → PASS
Metric 2 → PASS
Metric 3 → FAIL
Metric 4 → NOT_APPLICABLE
```

the aggregation produces:

```text
total_metrics          = 4
passed_metrics         = 2
failed_metrics         = 1
not_applicable_metrics = 1

overall decision       = FAIL
```

The overall result is `FAIL` because at least one applicable metric failed its regression gate.

---

## Immutable Evidence

The result contract uses:

```python
@dataclass(frozen=True)
```

This prevents evaluated regression evidence from being modified after creation.

For example, changing:

```python
result.decision
```

after evaluation raises:

```text
FrozenInstanceError
```

This follows the immutable contract pattern used by the preceding regression layers.

---

## Architectural Layering

Sprint 11.52 does not recalculate:

```text
metric direction
metric movement
regression magnitude
tolerance
tolerance status
severity
per-metric gate decision
```

Instead, it consumes the output produced by Sprint 11.51.

The regression pipeline now forms the following sequence:

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
        ↓
Sprint 11.52
Evaluation Run Regression Gate
```

Each layer retains one narrow responsibility.

---

## Test Coverage

Added:

```text
tests/test_evaluation_run_regression_gate.py
```

The sprint verifies:

```text
all PASS decisions → PASS
any FAIL decision → FAIL
PASS + NOT_APPLICABLE → PASS
all NOT_APPLICABLE → NOT_APPLICABLE
empty decision collection → NOT_APPLICABLE
result contract is immutable
```

Sprint-specific result:

```text
6 passed in 0.07s
```

Full regression suite:

```text
500 passed in 9.81s
```

This confirms the new run-level gate does not break existing AI Test Lab behavior.

---

## Scope Boundary

Sprint 11.52 intentionally does not:

```text
enforce CI/CD behavior
return process exit codes
block GitHub Actions
aggregate assertion failures
introduce configurable run policies
generate reports
perform statistical analysis
recalculate metric regression evidence
```

Those responsibilities belong to later layers.

Sprint 11.52 remains focused on one responsibility:

> Convert a collection of per-metric regression gate decisions into one deterministic evaluation-run regression gate decision.

---

## Result

Before Sprint 11.52, AI Test Lab could determine:

```text
Metric A → PASS
Metric B → PASS
Metric C → FAIL
```

but there was no explicit run-level regression decision.

After Sprint 11.52, AI Test Lab can determine:

```text
Metric A → PASS
Metric B → PASS
Metric C → FAIL
        ↓
Evaluation Run → FAIL
```

This creates the first complete aggregation layer between per-metric regression evidence and future CI/CD quality-gate enforcement.
