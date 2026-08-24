# Sprint 11.54 — Evaluation Run Regression Exit Code Mapping

## Objective

Add a deterministic process-exit-code mapping layer that converts an evaluation-run regression enforcement decision into a process-level numeric result.

Sprint 11.53 answered:

> Should the evaluation run be allowed to continue or should it be blocked?

Sprint 11.54 answers the next question:

> What process exit code represents that enforcement decision?

This sprint introduces exit-code mapping only.

It intentionally does not yet terminate Python execution, modify CLI behavior, or fail GitHub Actions.

---

## Problem

Sprint 11.53 introduced deterministic regression enforcement decisions:

```text
ALLOW
BLOCK
```

This established the policy boundary between regression evaluation and execution behavior.

For example:

```text
Evaluation Run Regression Gate
            FAIL
              ↓
      Enforcement Policy
            BLOCK
```

However, `BLOCK` is still a domain-level policy decision.

Operating systems, command-line interfaces, and CI/CD systems normally communicate execution success or failure using numeric process exit codes.

AI Test Lab therefore needs a deterministic translation from:

```text
ALLOW / BLOCK
```

into:

```text
0 / 1
```

Sprint 11.54 introduces that translation layer.

---

## Implementation

Added:

```text
src/evaluation_run_regression_exit_code.py
```

The module introduces:

```python
EvaluationRunRegressionExitCode
```

and:

```python
map_evaluation_run_regression_exit_code()
```

---

## Exit Code Contract

The result contract is represented by:

```python
@dataclass(frozen=True)
class EvaluationRunRegressionExitCode:
    code: int
```

The mapping policy is:

```text
ALLOW → 0
BLOCK → 1
```

This follows the conventional process-exit model in which:

```text
0     → successful execution
non-0 → unsuccessful execution
```

Sprint 11.54 deliberately uses `1` as the blocking result.

---

## ALLOW → 0

When Sprint 11.53 produces:

```text
ALLOW
```

Sprint 11.54 produces:

```text
0
```

Example:

```text
Evaluation Run Regression Gate
            PASS
              ↓
      Enforcement Policy
            ALLOW
              ↓
       Exit Code Mapping
              0
```

This indicates that regression enforcement does not require the execution environment to treat the run as failed.

The same applies when the run regression gate is `NOT_APPLICABLE`, because Sprint 11.53 maps that gate state to `ALLOW`.

---

## BLOCK → 1

When Sprint 11.53 produces:

```text
BLOCK
```

Sprint 11.54 produces:

```text
1
```

Example:

```text
Evaluation Run Regression Gate
            FAIL
              ↓
      Enforcement Policy
            BLOCK
              ↓
       Exit Code Mapping
              1
```

This creates a process-compatible representation of the blocking decision.

Importantly, Sprint 11.54 does not actually terminate the process.

It produces:

```python
EvaluationRunRegressionExitCode(code=1)
```

but does not execute:

```python
sys.exit(1)
```

or:

```python
raise SystemExit(1)
```

Process termination remains the responsibility of a later integration layer.

---

## Mapping Function

The mapping is performed by:

```python
map_evaluation_run_regression_exit_code()
```

Conceptually:

```python
if enforcement.decision == BLOCK:
    code = 1
else:
    code = 0
```

The function receives the immutable enforcement result produced by Sprint 11.53 and returns a new immutable exit-code result.

It does not recalculate:

```text
metric movement
regression magnitude
tolerance
severity
metric gate decisions
run gate decisions
enforcement decisions
```

Each earlier layer remains responsible for its own contract.

---

## Immutable Exit-Code Evidence

The result uses:

```python
@dataclass(frozen=True)
```

This means the exit-code mapping cannot be modified after creation.

For example, changing:

```python
result.code
```

after construction raises:

```text
FrozenInstanceError
```

This continues the immutable-contract pattern used throughout the AI Test Lab regression pipeline.

---

## Determinism

The mapping is pure and deterministic.

For identical enforcement input:

```text
ALLOW
```

the result is always:

```text
0
```

For identical enforcement input:

```text
BLOCK
```

the result is always:

```text
1
```

The mapping does not depend on:

```text
time
randomness
network state
environment variables
model output
external services
filesystem state
CI provider
operating system
```

This property is important because future CLI and CI/CD integrations must receive identical process-level outcomes for identical regression enforcement evidence.

---

## Architectural Separation

Sprint 11.54 deliberately keeps several responsibilities separate.

### Regression Evidence

Earlier layers determine what happened to individual metrics.

```text
metric direction
metric movement
regression magnitude
tolerance
severity
```

### Quality-Gate Decision

The metric and evaluation-run regression gates determine:

```text
PASS
FAIL
NOT_APPLICABLE
```

### Enforcement Policy

Sprint 11.53 converts the run-level gate result into:

```text
ALLOW
BLOCK
```

### Process Representation

Sprint 11.54 converts the enforcement decision into:

```text
0
1
```

The resulting architecture is:

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
        ↓
Exit Code Mapping
        ↓
0 / 1
```

This keeps operating-system representation separate from evaluation and policy semantics.

---

## Why the Mapping Layer Does Not Exit

It would be possible to write:

```python
if enforcement.decision == BLOCK:
    raise SystemExit(1)
```

inside the enforcement layer.

Sprint 11.54 intentionally avoids that design.

Doing so would couple core regression logic to process control.

AI Test Lab may eventually be consumed by:

```text
CLI applications
Python libraries
web APIs
CI/CD pipelines
GitHub Actions
dashboards
background workers
enterprise orchestration systems
```

Not every consumer should terminate its Python process when a regression is detected.

Instead, the core produces:

```text
BLOCK
    ↓
1
```

and leaves the final execution behavior to the consuming integration.

This creates a safer and more reusable architecture.

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
        ↓
Sprint 11.54
Evaluation Run Regression Exit Code Mapping
```

Each layer retains one narrow responsibility.

---

## Test Coverage

Added:

```text
tests/test_evaluation_run_regression_exit_code.py
```

Sprint-specific tests verify:

```text
ALLOW maps to 0
BLOCK maps to 1
identical enforcement produces identical exit code
result contract is immutable
mapping does not raise SystemExit
```

Sprint-specific result:

```text
5 passed in 0.06s
```

Full repository regression suite:

```text
510 passed in 10.47s
```

This confirms that Sprint 11.54 introduces the process-exit-code mapping contract without breaking existing AI Test Lab behavior.

---

## Scope Boundary

Sprint 11.54 intentionally does not:

```text
call sys.exit()
raise SystemExit
terminate Python execution
modify CLI exit behavior
modify main.py
modify GitHub Actions
modify workflow YAML
stop deployment
introduce configurable exit codes
change regression calculations
change regression tolerance
change regression severity
change quality-gate behavior
change enforcement policy
generate reports
```

Those responsibilities belong to later integration layers.

Sprint 11.54 remains focused on one responsibility:

> Convert a deterministic evaluation-run regression enforcement decision into a deterministic process exit-code representation.

---

## Result

Before Sprint 11.54, AI Test Lab could determine:

```text
Evaluation Run → FAIL
        ↓
Enforcement Policy
        ↓
      BLOCK
```

but there was no process-level representation of that blocking decision.

After Sprint 11.54:

```text
Evaluation Run → FAIL
        ↓
      BLOCK
        ↓
Exit Code Mapping
        ↓
        1
```

while:

```text
Evaluation Run → PASS
        ↓
      ALLOW
        ↓
        0
```

AI Test Lab now has a deterministic bridge between its regression-enforcement domain contract and the process-level convention required by future CLI and CI/CD integration.

The next integration layer can consume the numeric exit-code result without needing to understand how regression evidence, gate decisions, or enforcement decisions were calculated.
