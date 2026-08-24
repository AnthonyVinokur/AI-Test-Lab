# Sprint 11.53 — Evaluation Run Regression Gate Enforcement Policy

## Objective

Add a deterministic enforcement-policy layer that converts an evaluation-run regression gate decision into an explicit execution-policy decision.

Sprint 11.52 answered:

> Did the evaluation run pass the regression quality gate?

Sprint 11.53 answers the next question:

> Should that run be allowed to continue or should it be blocked?

This sprint introduces policy only.

It intentionally does not yet terminate a process, return CI/CD exit codes, or modify GitHub Actions behavior.

---

## Problem

Sprint 11.52 introduced run-level regression decisions:

```text
NOT_APPLICABLE
PASS
FAIL
```

This allows AI Test Lab to determine whether the evaluation run as a whole passed its regression gate.

For example:

```text
Metric A → PASS
Metric B → PASS
Metric C → FAIL
        ↓
Evaluation Run → FAIL
```

However, a run-level `FAIL` is still only an evaluation result.

AI Test Lab also needs an explicit policy decision answering:

```text
Should execution be allowed to proceed?
```

Sprint 11.53 introduces that policy boundary.

---

## Implementation

Added:

```text
src/evaluation_run_regression_enforcement.py
```

The module introduces:

```python
EvaluationRunRegressionEnforcementDecision
EvaluationRunRegressionEnforcement
```

and:

```python
enforce_evaluation_run_regression_gate()
```

---

## Enforcement Decision Contract

The enforcement layer defines two possible decisions:

```python
class EvaluationRunRegressionEnforcementDecision(str, Enum):
    ALLOW = "allow"
    BLOCK = "block"
```

These values intentionally differ from the run regression gate states.

The run gate describes evaluation evidence:

```text
PASS
FAIL
NOT_APPLICABLE
```

The enforcement layer describes what policy should do with that evidence:

```text
ALLOW
BLOCK
```

This keeps evaluation semantics separate from execution policy.

---

## Enforcement Policy

Sprint 11.53 uses the following deterministic mapping:

```text
PASS            → ALLOW
FAIL            → BLOCK
NOT_APPLICABLE  → ALLOW
```

In policy form:

```text
If run regression gate == FAIL:
    enforcement decision = BLOCK

Otherwise:
    enforcement decision = ALLOW
```

---

## PASS → ALLOW

When Sprint 11.52 produces:

```text
PASS
```

Sprint 11.53 produces:

```text
ALLOW
```

Example:

```text
Evaluation Run Regression Gate
            PASS
              ↓
      Enforcement Policy
            ALLOW
```

The regression evidence contains no blocking regression.

---

## FAIL → BLOCK

When Sprint 11.52 produces:

```text
FAIL
```

Sprint 11.53 produces:

```text
BLOCK
```

Example:

```text
Evaluation Run Regression Gate
            FAIL
              ↓
      Enforcement Policy
            BLOCK
```

This establishes the first explicit blocking decision in the regression pipeline.

Importantly, `BLOCK` is currently a policy result only.

Sprint 11.53 does not yet:

```text
raise SystemExit
return a non-zero process code
fail GitHub Actions
terminate the CLI
stop deployment
```

Those are execution-layer responsibilities for later integration.

---

## NOT_APPLICABLE → ALLOW

When Sprint 11.52 produces:

```text
NOT_APPLICABLE
```

Sprint 11.53 produces:

```text
ALLOW
```

This means absence of applicable regression evidence does not automatically block execution.

Example:

```text
Evaluation Run Regression Gate
       NOT_APPLICABLE
              ↓
      Enforcement Policy
            ALLOW
```

This preserves the distinction between:

```text
confirmed regression
```

and:

```text
no applicable regression decision
```

Only a confirmed run-level `FAIL` blocks.

---

## Result Contract

The enforcement result is represented by:

```python
@dataclass(frozen=True)
class EvaluationRunRegressionEnforcement:
    decision: EvaluationRunRegressionEnforcementDecision
```

Example:

```python
EvaluationRunRegressionEnforcement(
    decision=EvaluationRunRegressionEnforcementDecision.BLOCK,
)
```

The enforcement result contains only the policy decision required by this layer.

It does not duplicate the metric counts or regression evidence already preserved by Sprint 11.52.

---

## Immutable Policy Evidence

The enforcement result uses:

```python
@dataclass(frozen=True)
```

This ensures the enforcement decision cannot be modified after evaluation.

For example, attempting to change:

```python
result.decision
```

after creation raises:

```text
FrozenInstanceError
```

This continues the immutable-contract pattern used throughout the regression pipeline.

---

## Determinism

The enforcement function is pure and deterministic.

For the same run regression gate:

```text
FAIL
```

every evaluation produces:

```text
BLOCK
```

Likewise:

```text
PASS → ALLOW
NOT_APPLICABLE → ALLOW
```

No randomness, external state, environment configuration, clock value, model output, or network dependency affects the decision.

This is important for future CI/CD integration because identical regression evidence must always produce identical enforcement behavior.

---

## Architectural Separation

Sprint 11.53 deliberately separates three concepts.

### Evidence

Earlier regression layers determine what happened:

```text
metric changed
metric regressed
regression exceeded tolerance
regression severity
```

### Gate Decision

Sprint 11.51 and Sprint 11.52 determine whether that evidence passes the regression quality gate:

```text
PASS
FAIL
NOT_APPLICABLE
```

### Enforcement Policy

Sprint 11.53 determines what the system should do with the run-level gate decision:

```text
ALLOW
BLOCK
```

The architecture therefore becomes:

```text
Regression Evidence
        ↓
Metric Regression Gate
        ↓
Evaluation Run Regression Gate
        ↓
Regression Enforcement Policy
        ↓
ALLOW / BLOCK
```

This separation prevents process-control concerns from leaking into evaluation semantics.

---

## Regression Pipeline

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
        ↓
Sprint 11.53
Evaluation Run Regression Gate Enforcement Policy
```

Each layer retains one narrow responsibility.

---

## Test Coverage

Added:

```text
tests/test_evaluation_run_regression_enforcement.py
```

Sprint-specific tests verify:

```text
PASS → ALLOW
FAIL → BLOCK
NOT_APPLICABLE → ALLOW
same input produces same output
result contract is immutable
```

Sprint-specific result:

```text
5 passed in 0.06s
```

The related regression-gate test chain also passed successfully.

Full repository regression suite:

```text
505 passed in 10.44s
```

This confirms Sprint 11.53 introduces the enforcement-policy contract without breaking existing AI Test Lab behavior.

---

## Scope Boundary

Sprint 11.53 intentionally does not:

```text
terminate Python execution
return process exit codes
modify CLI exit behavior
fail GitHub Actions
block deployment
add environment-specific policies
add configurable enforcement profiles
generate reports
recalculate metric regression evidence
recalculate run-level regression decisions
```

Those responsibilities belong to later integration layers.

Sprint 11.53 remains focused on one responsibility:

> Convert a deterministic evaluation-run regression gate decision into a deterministic ALLOW or BLOCK enforcement-policy decision.

---

## Why This Separation Matters

Without a separate policy layer, the run regression gate would need to know about:

```text
CLI behavior
CI/CD systems
GitHub Actions
deployment rules
process exit codes
```

That would mix evaluation logic with operational execution.

Sprint 11.53 prevents that coupling.

The core regression engine can now say:

```text
BLOCK
```

without caring whether a future consumer translates that into:

```text
exit code 1
GitHub Actions failure
deployment rejection
API response
dashboard status
manual review requirement
```

This creates a clean extension point for future integrations.

---

## Result

Before Sprint 11.53, AI Test Lab could determine:

```text
Evaluation Run → FAIL
```

but it did not have a dedicated execution-policy interpretation.

After Sprint 11.53:

```text
Evaluation Run → FAIL
        ↓
Enforcement Policy
        ↓
      BLOCK
```

while:

```text
Evaluation Run → PASS
        ↓
      ALLOW
```

and:

```text
Evaluation Run → NOT_APPLICABLE
        ↓
      ALLOW
```

AI Test Lab now has a deterministic boundary between regression evaluation and future CI/CD enforcement.

The next layer can consume `ALLOW` or `BLOCK` without needing to understand how metric regression evidence was calculated.
