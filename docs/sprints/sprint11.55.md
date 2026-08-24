# Sprint 11.55 — Evaluation Run Regression Result

## Goal

Sprint 11.55 introduces a stable immutable result contract for evaluation-run regression enforcement.

The sprint builds on the existing regression pipeline without changing any regression policy, enforcement behavior, or exit-code behavior.

The existing flow before Sprint 11.55 was:

```text
Metric Regression Decisions
        ↓
Evaluation Run Regression Gate
        ↓
Evaluation Run Regression Enforcement
        ↓
Evaluation Run Regression Exit Code
```

Sprint 11.55 adds a final composition layer:

```text
Metric Regression Decisions
        ↓
Evaluation Run Regression Gate
        ↓
Evaluation Run Regression Enforcement
        ↓
Evaluation Run Regression Exit Code
        ↓
Evaluation Run Regression Result
```

## New Contract

A new immutable dataclass was introduced:

```python
@dataclass(frozen=True)
class EvaluationRunRegressionResult:
    enforcement: EvaluationRunRegressionEnforcement
    exit_code: EvaluationRunRegressionExitCode
```

This object provides one stable result containing:

* the enforcement decision
* the corresponding process exit code

## Result Builder

Sprint 11.55 also introduces:

```python
build_evaluation_run_regression_result(...)
```

The builder receives an existing:

```python
EvaluationRunRegressionEnforcement
```

and obtains the exit code through the already-established Sprint 11.54 mapping:

```python
map_evaluation_run_regression_exit_code(enforcement)
```

The builder therefore does not duplicate regression policy or exit-code policy.

## Architectural Boundary

Sprint 11.55 intentionally preserves separation of responsibilities.

### Regression Gate

Answers:

```text
Did the evaluation run pass the regression gate?
```

Possible decisions include:

```text
PASS
FAIL
NOT_APPLICABLE
```

### Regression Enforcement

Answers:

```text
Should execution be allowed or blocked?
```

Possible decisions are:

```text
ALLOW
BLOCK
```

### Regression Exit Code

Answers:

```text
What operating-system process exit code represents the enforcement result?
```

Current behavior:

```text
ALLOW → 0
BLOCK → 1
```

### Regression Result

Answers:

```text
What is the final stable execution result that downstream consumers can inspect?
```

It combines the enforcement result and exit-code result without recalculating either policy.

## Files Added

### Production

```text
src/evaluation_run_regression_result.py
```

Introduces:

```text
EvaluationRunRegressionResult
build_evaluation_run_regression_result
```

### Tests

```text
tests/test_evaluation_run_regression_result.py
```

## Test Coverage

Sprint 11.55 verifies:

1. `ALLOW` produces exit code `0`.
2. `BLOCK` produces exit code `1`.
3. Identical enforcement input produces identical result output.
4. The original enforcement object is preserved.
5. The result contract is immutable.

The immutability test verifies that consumers cannot mutate the resulting execution contract after creation.

## Design Principles

Sprint 11.55 follows several core AI Test Lab architecture principles.

### Deterministic behavior

The same enforcement input produces the same result.

### Immutability

The result object is frozen after creation.

### Single responsibility

The new layer composes existing results rather than introducing new policy.

### No duplicated logic

Exit-code behavior remains owned by:

```text
evaluation_run_regression_exit_code.py
```

### Stable downstream contract

Future consumers can depend on one result object instead of independently reconstructing enforcement and exit-code information.

Potential downstream consumers include:

```text
CLI
CI/CD quality gates
GitHub Actions
reports
public APIs
dashboards
automation
```

Those integrations are outside the scope of Sprint 11.55.

## Explicitly Out of Scope

Sprint 11.55 does not add:

* CLI presentation changes
* JSON serialization
* API endpoints
* GitHub Actions integration
* reporting changes
* persistence
* regression history
* dashboards
* new regression policy
* new enforcement policy
* new exit-code policy

## Result

Sprint 11.55 establishes a small but important composition boundary between internal regression enforcement and future external execution consumers.

The resulting architecture is:

```text
Detection
    ↓
Classification
    ↓
Gate
    ↓
Enforcement
    ↓
Exit Code
    ↓
Stable Execution Result
```

This prepares AI Test Lab for later CI/CD and external integration work while preserving the existing regression architecture and IP boundaries.
