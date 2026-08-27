# Sprint 11.78 — Regression CLI Execution-Failure Handling

## Status

**Completed**

Sprint 11.78 strengthens the AI Test Lab regression CLI by adding a stable process-level failure boundary around regression execution.

The CLI now converts unexpected regression runtime or infrastructure exceptions into a deterministic command-line result instead of allowing raw Python exceptions and tracebacks to escape.

---

## Objective

Ensure that failures occurring while executing regression analysis are handled as controlled CLI failures.

The sprint establishes the following contract:

> A regression runtime failure is an infrastructure failure, not a regression verdict.

When regression execution cannot complete, the CLI must:

1. report the failure clearly,
2. stop further regression-result processing,
3. avoid creating misleading regression artifacts,
4. return a deterministic infrastructure exit code.

---

## Background

Earlier Sprint 11 regression work progressively established the regression execution stack:

```text
Baseline result acquisition
        ↓
Candidate result adaptation
        ↓
Regression comparison
        ↓
Case-level regression gate
        ↓
Regression enforcement
        ↓
Evaluation-run regression orchestration
        ↓
Runtime assembly
        ↓
Regression entry point
        ↓
CLI execution wiring
        ↓
CLI exit-code enforcement
        ↓
Regression result artifact
        ↓
Artifact failure handling
```

By Sprint 11.77, the CLI already handled failures that occurred while writing the regression-result artifact.

However, one important process boundary remained incomplete.

The call to:

```python
execute_evaluation_run_regression(...)
```

could still raise an exception that propagated through `main()`.

In a local terminal, this could expose a traceback.

In CI/CD, this was more problematic because the caller could not reliably distinguish:

```text
Candidate failed regression
```

from:

```text
Regression infrastructure failed to execute
```

Sprint 11.78 closes that gap.

---

## Problem

Before this sprint, regression execution effectively followed this path:

```text
CLI
 ↓
execute_evaluation_run_regression(...)
 ↓
exception
 ↓
uncaught Python error
 ↓
traceback / uncontrolled process termination
```

The CLI therefore did not fully own its process contract.

A command-line application intended for automated quality gates should translate expected application-layer failures into deterministic process outcomes.

Raw implementation exceptions should not become the public CI/CD interface.

---

## Implementation

### Modified File

```text
src/cli/app.py
```

Regression execution is now protected by a CLI-level exception boundary.

The regression call is wrapped so that an execution failure is converted into a controlled CLI response:

```python
try:
    regression_execution = execute_evaluation_run_regression(
        candidate_results=results,
        baseline_report_path=args.regression_baseline_report,
        baseline_provenance_path=args.regression_baseline_provenance,
        candidate_identity=candidate_identity,
        candidate_dataset_version=str(args.dataset_version),
        report_schema_version="1.0",
    )
except Exception as error:
    print(
        f"Regression execution error: {error}",
        file=sys.stderr,
    )
    return 3
```

---

## Runtime Behavior

### Successful Regression Execution

```text
Candidate evaluation results
        ↓
Execute regression
        ↓
Build regression result
        ↓
Write regression artifact
        ↓
Return regression decision exit code
```

### Failed Regression Execution

```text
Candidate evaluation results
        ↓
Execute regression
        ↓
Runtime/infrastructure exception
        ↓
Print controlled stderr diagnostic
        ↓
Skip regression-result construction
        ↓
Skip regression artifact writing
        ↓
Return exit code 3
```

Example diagnostic:

```text
Regression execution error: baseline regression execution failed
```

---

## Why the Failure Stops Processing

A regression result represents the outcome of a completed comparison.

If regression execution itself fails, there is no trustworthy regression decision to serialize.

Therefore AI Test Lab must not continue with:

```python
build_evaluation_run_regression_result(...)
```

or:

```python
write_cli_regression_result(...)
```

Doing so could create an artifact that appears authoritative even though regression analysis never completed.

Sprint 11.78 explicitly prevents that behavior.

---

## Exit-Code Contract

The regression CLI now has a clearer process-level contract.

| Exit Code | Meaning |
|---:|---|
| `0` | Evaluation/regression completed successfully and the regression gate allows the candidate |
| `1` | Evaluation or regression quality failure |
| `2` | Invalid CLI arguments, input, configuration, or dataset requirements |
| `3` | Regression infrastructure, execution, or artifact failure |

This distinction is especially important for CI/CD automation.

For example:

```text
exit 1
```

means:

> The system worked and found a quality problem.

While:

```text
exit 3
```

means:

> The regression system could not reliably produce a decision.

Those conditions should normally trigger different pipeline responses.

---

## Exception Boundary

Sprint 11.78 catches:

```python
Exception
```

at the CLI process boundary.

This is intentional.

Regression execution can depend on several fallible operations, including:

- baseline report acquisition,
- baseline provenance loading,
- regression runtime assembly,
- stored artifact parsing,
- filesystem access,
- provenance processing,
- candidate/baseline compatibility evaluation,
- regression orchestration.

The CLI does not need to expose every internal exception type as part of its public process contract.

Instead, those implementation failures are translated into the regression infrastructure failure category.

The boundary does **not** catch Python process-control exceptions such as:

```text
KeyboardInterrupt
SystemExit
```

because those do not inherit from `Exception`.

Normal process interruption semantics therefore remain intact.

---

## Tests

### Modified File

```text
tests/cli/test_regression_execution.py
```

Two regression CLI tests were added.

### 1. Regression Execution Failure Contract

The first test verifies that when regression execution raises a runtime exception:

- the CLI returns exit code `3`,
- a controlled diagnostic is written to `stderr`,
- regression-result construction does not occur,
- regression-artifact writing does not occur.

Conceptually:

```text
execute regression
      ↓
RuntimeError
      ↓
stderr diagnostic
      ↓
exit 3
```

and:

```text
build result      → NOT CALLED
write artifact    → NOT CALLED
```

---

### 2. Failure Precedence

The second test verifies that a regression execution failure takes precedence over ordinary evaluation failures.

For example:

```text
evaluation contains failures
        +
regression infrastructure fails
        ↓
exit 3
```

The CLI must not reduce this situation to:

```text
exit 1
```

because the regression system itself failed to complete.

This preserves the distinction between a valid negative quality decision and an invalid/incomplete regression execution.

---

## Verification

### Focused Regression CLI Tests

```text
10 passed in 0.54s
```

All regression CLI behavior passed, including:

- regression disabled when not requested,
- managed-dataset requirements,
- single-model requirements,
- regression execution,
- regression block exit codes,
- regression exit-code precedence,
- regression artifact failures,
- artifact-failure precedence,
- regression execution failures,
- execution-failure precedence.

### Full Test Suite

```text
630 passed in 21.07s
```

No regressions were introduced elsewhere in AI Test Lab.

---

## Files Changed

```text
src/cli/app.py
tests/cli/test_regression_execution.py
```

Sprint documentation is maintained separately in:

```text
docs/sprints/sprint11.78.md
```

---

## Architectural Significance

Sprint 11.78 is small in code size but important at the system boundary.

AI Test Lab is increasingly operating as a quality-gate platform rather than only a Python evaluation library.

That requires its public execution interfaces to behave deterministically.

The CLI must communicate not only:

```text
Did the candidate pass?
```

but also:

```text
Was AI Test Lab itself able to produce a trustworthy decision?
```

Sprint 11.78 establishes that distinction for regression execution.

---

## CI/CD Interpretation

A CI system can now reason about regression execution more safely.

### Successful Gate

```text
AI Test Lab
    ↓
Regression completed
    ↓
Candidate acceptable
    ↓
exit 0
    ↓
pipeline continues
```

### Quality Regression

```text
AI Test Lab
    ↓
Regression completed
    ↓
Candidate violates regression policy
    ↓
exit 1
    ↓
quality gate blocks candidate
```

### Invalid Invocation

```text
AI Test Lab
    ↓
CLI/input contract invalid
    ↓
exit 2
    ↓
pipeline configuration must be fixed
```

### Infrastructure Failure

```text
AI Test Lab
    ↓
Regression could not complete
    ↓
exit 3
    ↓
decision is unavailable
```

This separation is essential for reliable automated quality enforcement.

---

## Design Principles Preserved

Sprint 11.78 continues several architectural principles established throughout Sprint 11.

### Thin CLI

The CLI does not implement regression algorithms.

It remains responsible for:

- validating invocation requirements,
- connecting runtime inputs,
- translating application results into process behavior,
- handling process-level failures.

Regression logic remains below the CLI boundary.

### Deterministic Automation

CI/CD callers receive stable exit semantics instead of depending on Python traceback behavior.

### No False Evidence

AI Test Lab does not generate a regression-result artifact when regression execution never completed.

### Separation of Quality Failure and System Failure

A candidate regression and a regression-engine failure are distinct operational states.

The CLI now preserves that distinction.

---

## Acceptance Criteria

Sprint 11.78 is complete when all of the following are true:

- [x] Regression execution exceptions do not escape through the CLI.
- [x] Regression execution failures produce a controlled `stderr` message.
- [x] Regression execution failures return exit code `3`.
- [x] Regression-result construction is skipped after execution failure.
- [x] Regression-result artifact writing is skipped after execution failure.
- [x] Regression infrastructure failure takes precedence over ordinary evaluation failures.
- [x] Existing regression CLI behavior remains unchanged.
- [x] Focused regression CLI tests pass.
- [x] Full AI Test Lab test suite passes.

---

## Final Result

Sprint 11.78 completes the missing process-level failure boundary around regression execution.

Before this sprint:

```text
Regression runtime failure
        ↓
uncaught implementation exception
```

After this sprint:

```text
Regression runtime failure
        ↓
stable CLI diagnostic
        ↓
no false regression artifact
        ↓
deterministic exit code 3
```

The regression CLI now distinguishes a **quality decision** from a **failure to produce a quality decision**, making AI Test Lab safer and more predictable for CI/CD quality-gate usage.