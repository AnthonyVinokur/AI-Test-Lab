# Sprint 11.79 — Regression CLI Diagnostic Contract

## Status

**Completed**

Sprint 11.79 strengthens the AI Test Lab command-line regression interface by turning CLI diagnostics into an explicit, centralized, and independently testable contract.

Previous Sprint 11 work had already established deterministic regression execution, exit-code handling, result artifact generation, artifact failure handling, and execution failure handling.

Sprint 11.79 focuses on a narrower but important boundary:

> The CLI should not only return stable process exit codes. It should also produce stable, predictable diagnostics for the caller.

This sprint centralizes regression-related diagnostic formatting and verifies that error messages continue to be written to `stderr` without changing existing runtime semantics.

---

## Objective

Establish a durable CLI diagnostic boundary for regression-related failures.

The CLI must preserve a clear relationship between failure category, diagnostic output, and process exit code.

```text
Invalid input or configuration
        ↓
Input error: ...
        ↓
stderr
        ↓
exit code 2
```

```text
Regression execution failure
        ↓
Regression execution error: ...
        ↓
stderr
        ↓
exit code 3
```

```text
Regression artifact failure
        ↓
Regression artifact error: ...
        ↓
stderr
        ↓
exit code 3
```

The objective is intentionally small:

> Make existing CLI diagnostics stable, centralized, and directly testable without introducing a larger logging or observability system.

---

## Background

Sprint 11 progressively transformed regression support from internal evaluation logic into a dependable CI/CD-facing quality-gate interface.

Recent work established the following layers:

```text
Regression CLI input contract
        ↓
Regression CLI execution wiring
        ↓
Regression exit-code enforcement
        ↓
Regression result-output contract
        ↓
Regression artifact failure handling
        ↓
Regression execution failure handling
```

By Sprint 11.78, AI Test Lab could already distinguish:

```text
Candidate failed quality gate
```

from:

```text
Regression infrastructure failed
```

through deterministic process exit codes.

However, several public CLI diagnostics were still formatted directly inside:

```text
src/cli/app.py
```

The behavior was correct, but the textual process contract remained distributed across orchestration code.

Sprint 11.79 closes that gap.

---

## Problem

Before this sprint, `src/cli/app.py` directly formatted several error messages.

Conceptually:

```python
print(
    f"Input error: {error}",
    file=sys.stderr,
)

print(
    f"Regression execution error: {error}",
    file=sys.stderr,
)

print(
    f"Regression artifact error: {error}",
    file=sys.stderr,
)
```

This created unnecessary coupling between:

```text
CLI orchestration
```

and:

```text
CLI diagnostic representation
```

Although small, that coupling matters because CLI diagnostics are part of the observable process contract.

A future refactor could accidentally change:

- message prefixes,
- output stream,
- formatting consistency,
- error-classification semantics.

Without dedicated tests, such changes could reach CI/CD users unnoticed.

---

## Design Principle

Sprint 11.79 separates two responsibilities.

### Application orchestration

The CLI application decides:

- whether an error occurred,
- what type of failure it represents,
- whether processing must stop,
- which exit code should be returned.

### Diagnostic representation

The diagnostics layer decides:

- the stable prefix used for each failure category,
- how the underlying error message is rendered,
- that diagnostic output is written to `stderr`.

The resulting separation is:

```text
Application detects failure
        ↓
Application classifies failure
        ↓
Diagnostic helper formats message
        ↓
stderr
        ↓
Application returns exit code
```

This keeps `app.py` focused on orchestration rather than message formatting.

---

## Implementation

### New File

```text
src/cli/diagnostics.py
```

A small dedicated module now owns stable CLI diagnostic formatting.

The implementation intentionally remains simple.

```python
from __future__ import annotations

import sys


def print_input_error(error: object) -> None:
    print(
        f"Input error: {error}",
        file=sys.stderr,
    )


def print_regression_execution_error(error: object) -> None:
    print(
        f"Regression execution error: {error}",
        file=sys.stderr,
    )


def print_regression_artifact_error(error: object) -> None:
    print(
        f"Regression artifact error: {error}",
        file=sys.stderr,
    )
```

The module does not implement:

- logging configuration,
- error classification,
- exception translation,
- telemetry,
- structured reporting,
- process exit behavior.

Its responsibility is deliberately narrow:

> Convert an already-classified CLI failure into its stable human-readable diagnostic representation.

---

## CLI Integration

### Modified File

```text
src/cli/app.py
```

The CLI now imports the diagnostic helpers:

```python
from src.cli.diagnostics import (
    print_input_error,
    print_regression_artifact_error,
    print_regression_execution_error,
)
```

---

## Input Failure Handling

Before:

```python
except INPUT_EXCEPTIONS as error:
    print(
        f"Input error: {error}",
        file=sys.stderr,
    )
    return 2
```

After:

```python
except INPUT_EXCEPTIONS as error:
    print_input_error(error)
    return 2
```

The runtime behavior is unchanged.

The CLI still owns the decision that this is an input failure and still returns:

```text
exit code 2
```

Only diagnostic formatting has moved behind the dedicated boundary.

---

## Regression Execution Failure Handling

Before:

```python
except Exception as error:
    print(
        f"Regression execution error: {error}",
        file=sys.stderr,
    )
    return 3
```

After:

```python
except Exception as error:
    print_regression_execution_error(error)
    return 3
```

Again, process semantics remain unchanged.

A regression runtime or infrastructure failure continues to mean:

```text
Regression could not reliably complete.
```

and therefore returns:

```text
exit code 3
```

---

## Regression Artifact Failure Handling

Before:

```python
except EvaluationRunRegressionResultWriteError as error:
    print(
        f"Regression artifact error: {error}",
        file=sys.stderr,
    )
    return 3
```

After:

```python
except EvaluationRunRegressionResultWriteError as error:
    print_regression_artifact_error(error)
    return 3
```

An artifact write failure is still treated as an infrastructure-level regression failure.

The sprint changes representation ownership, not runtime classification.

---

## Diagnostic Contract

Sprint 11.79 establishes the following stable diagnostic categories.

### Input Failure

```text
Input error: <details>
```

Example:

```text
Input error: invalid dataset
```

Output stream:

```text
stderr
```

Associated exit code:

```text
2
```

---

### Regression Execution Failure

```text
Regression execution error: <details>
```

Example:

```text
Regression execution error: baseline execution failed
```

Output stream:

```text
stderr
```

Associated exit code:

```text
3
```

---

### Regression Artifact Failure

```text
Regression artifact error: <details>
```

Example:

```text
Regression artifact error: cannot write result
```

Output stream:

```text
stderr
```

Associated exit code:

```text
3
```

---

## Why `stderr` Matters

CLI diagnostics are intentionally written to:

```text
stderr
```

rather than:

```text
stdout
```

This distinction is important for command-line and CI/CD automation.

`stdout` should remain available for ordinary command output and machine-consumed result information.

`stderr` represents diagnostics concerning failed execution or invalid invocation.

Conceptually:

```text
stdout
    → normal command output

stderr
    → diagnostics and operational failures
```

Keeping these channels separate allows callers to capture them independently.

For example:

```powershell
ai-test-lab ... 1>results.txt 2>errors.txt
```

A CI system can therefore preserve normal output separately from operational diagnostics.

---

## Tests

### New File

```text
tests/cli/test_diagnostics.py
```

Three focused tests establish the diagnostic contract.

---

### Input Diagnostic Test

The first test verifies that:

```text
print_input_error(...)
```

produces exactly:

```text
Input error: invalid dataset
```

on:

```text
stderr
```

and produces no output on:

```text
stdout
```

---

### Regression Execution Diagnostic Test

The second test verifies that:

```text
print_regression_execution_error(...)
```

produces:

```text
Regression execution error: baseline execution failed
```

on `stderr`.

No normal output is emitted.

---

### Regression Artifact Diagnostic Test

The third test verifies that:

```text
print_regression_artifact_error(...)
```

produces:

```text
Regression artifact error: cannot write result
```

on `stderr`.

Again, `stdout` remains empty.

---

## Test-First Development

Sprint 11.79 was implemented using a small red-green-refactor cycle.

### Step 1 — Define the contract

The tests were added before the production module existed.

Running:

```powershell
pytest .\tests\cli\test_diagnostics.py -v
```

initially failed during collection with:

```text
ModuleNotFoundError: No module named 'src.cli.diagnostics'
```

This established that the new diagnostic boundary did not yet exist.

---

### Step 2 — Implement the smallest diagnostic boundary

The new:

```text
src/cli/diagnostics.py
```

module was introduced with only the three required helper functions.

The focused test result became:

```text
3 passed
```

---

### Step 3 — Integrate with the existing CLI

`src/cli/app.py` was then refactored to use the new helpers without changing process behavior.

Focused diagnostic and regression CLI tests passed:

```text
13 passed in 0.63s
```

---

## Full Verification

The complete AI Test Lab test suite was executed after the refactor.

Result:

```text
633 passed in 12.55s
```

The previous Sprint 11.78 baseline was:

```text
630 passed
```

Sprint 11.79 introduced three new diagnostic contract tests.

No regressions were introduced elsewhere in the system.

---

## Exit-Code Contract

Sprint 11.79 does **not** change the established CLI exit-code contract.

| Exit Code | Meaning |
|---:|---|
| `0` | Evaluation and regression completed successfully and the candidate is acceptable |
| `1` | Evaluation or regression produced a valid quality failure |
| `2` | CLI invocation, input, dataset, or configuration requirements are invalid |
| `3` | Regression execution, infrastructure, or artifact processing failed |

The important distinction remains:

```text
exit 1
```

means:

> AI Test Lab completed its work and produced a negative quality decision.

While:

```text
exit 3
```

means:

> AI Test Lab could not reliably produce the regression decision.

Sprint 11.79 strengthens the textual diagnostic side of that process contract.

---

## Runtime Behavior

### Valid Regression Success

```text
Candidate evaluation
        ↓
Regression execution
        ↓
Regression result
        ↓
Artifact written
        ↓
exit 0
```

---

### Valid Regression Failure

```text
Candidate evaluation
        ↓
Regression execution
        ↓
Regression policy blocks candidate
        ↓
exit 1
```

---

### Invalid Input

```text
CLI invocation
        ↓
Input requirement fails
        ↓
print_input_error(...)
        ↓
stderr
        ↓
exit 2
```

---

### Regression Execution Failure

```text
Candidate evaluation
        ↓
Regression execution
        ↓
Infrastructure/runtime exception
        ↓
print_regression_execution_error(...)
        ↓
stderr
        ↓
exit 3
```

---

### Regression Artifact Failure

```text
Regression execution completes
        ↓
Regression result created
        ↓
Artifact write fails
        ↓
print_regression_artifact_error(...)
        ↓
stderr
        ↓
exit 3
```

---

## Architectural Significance

Sprint 11.79 is intentionally small, but it improves the durability of the public CLI boundary.

AI Test Lab is increasingly expected to behave as:

```text
evaluation engine
        +
regression system
        +
CI/CD quality gate
```

A CI/CD-facing interface should have stable behavior across several dimensions:

```text
input contract
exit-code contract
artifact contract
failure contract
diagnostic contract
```

Sprint 11.79 completes another part of that interface.

The CLI no longer treats its error text as incidental formatting scattered through application logic.

Instead:

```text
failure classification
```

and:

```text
failure representation
```

are separate responsibilities.

---

## Maintainability Benefit

Future developers now have one obvious place to modify CLI diagnostic representation:

```text
src/cli/diagnostics.py
```

rather than searching through orchestration code for individual:

```python
print(..., file=sys.stderr)
```

statements.

This reduces the likelihood of diagnostic drift.

For example, without centralization, future code could accidentally introduce inconsistent prefixes:

```text
Regression error:
Regression execution failed:
Regression failure:
Regression runtime error:
```

After Sprint 11.79, the intended public diagnostic remains:

```text
Regression execution error:
```

and its exact form is protected by tests.

---

## Scope Control

Sprint 11.79 intentionally avoids introducing broader infrastructure.

The sprint does **not** add:

- Python logging configuration;
- structured JSON diagnostics;
- log levels;
- telemetry;
- tracing;
- observability backends;
- GitHub Actions integration;
- CI-provider-specific formatting;
- REST API error schemas;
- additional exit codes;
- generalized application exception hierarchies.

Those capabilities may become useful later, but they are not required to solve the current problem.

This sprint follows the principle:

> Introduce the smallest stable boundary needed by the current architecture.

---

## IP and Architecture Boundary

The diagnostic module is part of the public execution boundary rather than proprietary evaluation logic.

It exposes only generic process-level information:

```text
input failure
execution failure
artifact failure
```

It does not expose:

- regression scoring algorithms;
- evaluation policy internals;
- proprietary governance rules;
- evidence-intelligence logic;
- internal orchestration details.

This preserves the separation between public operational contracts and protected core implementation.

---

## Files Changed

```text
src/cli/app.py
src/cli/diagnostics.py
tests/cli/test_diagnostics.py
docs/sprints/sprint11.79.md
```

---

## Acceptance Criteria

- [x] Input exception diagnostics are centralized.
- [x] Regression execution diagnostics are centralized.
- [x] Regression artifact diagnostics are centralized.
- [x] Diagnostic prefixes remain stable.
- [x] Diagnostic output is written to `stderr`.
- [x] Diagnostic helpers do not write to `stdout`.
- [x] Diagnostic formatting is independently unit tested.
- [x] Existing CLI exit-code semantics remain unchanged.
- [x] Existing regression execution behavior remains unchanged.
- [x] Existing regression artifact behavior remains unchanged.
- [x] Focused diagnostic and regression CLI tests pass.
- [x] Full AI Test Lab test suite passes.
- [x] No unrelated logging or observability infrastructure is introduced.

---

## Final Result

Before Sprint 11.79:

```text
CLI orchestration
        ↓
inline diagnostic formatting
        ↓
stderr
```

After Sprint 11.79:

```text
CLI orchestration
        ↓
failure classification
        ↓
dedicated diagnostic contract
        ↓
stable stderr representation
```

Sprint 11.79 turns CLI error text from scattered implementation detail into a small, explicit process contract.

The regression CLI now has stable behavior across:

```text
inputs
execution
exit codes
result artifacts
failure handling
diagnostics
```

That makes the AI Test Lab regression interface cleaner, easier to maintain, and better prepared for future CI/CD quality-gate integration.