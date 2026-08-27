# Sprint 11.80 — Regression Preflight Diagnostic Hardening

## Status

**Completed**

## Summary

Sprint 11.80 completes the regression CLI diagnostic boundary introduced in Sprint 11.79.

Sprint 11.79 centralized CLI diagnostic formatting behind dedicated helper functions. However, several regression preflight validation paths in `src/cli/app.py` still formatted their own `Input error:` messages directly.

Sprint 11.80 removes that remaining duplication.

All supported regression preflight input failures now use the same centralized diagnostic path:

```python
print_input_error(...)
```

The sprint preserves the existing public CLI contract:

- invalid regression input is rejected before evaluation begins,
- diagnostics are written to `stderr`,
- input failures use the stable `Input error:` prefix,
- invalid input returns exit code `2`,
- regression execution does not begin when preflight validation fails,
- observable CLI behavior remains unchanged.

The result is a cleaner separation between CLI orchestration and diagnostic representation.

---

## Objective

Complete the regression CLI input-diagnostic boundary without changing runtime semantics.

The intended contract is:

```text
Regression command received
        ↓
Preflight validation
        ↓
Invalid regression input
        ↓
print_input_error(...)
        ↓
stderr
        ↓
exit code 2
```

Sprint 11.80 is therefore a hardening and architectural-consistency sprint rather than a feature expansion.

---

## Background

Recent Sprint 11 work progressively established regression execution as a dependable CI/CD-facing quality-gate interface.

The relevant sequence is:

```text
Regression CLI input contract
        ↓
Regression execution wiring
        ↓
Regression exit-code enforcement
        ↓
Regression result-output contract
        ↓
Regression artifact failure handling
        ↓
Regression execution failure handling
        ↓
Regression diagnostic contract
        ↓
Regression preflight diagnostic hardening
```

Sprint 11.79 introduced:

```text
src/cli/diagnostics.py
```

with centralized helpers for:

```python
print_input_error(...)
print_regression_execution_error(...)
print_regression_artifact_error(...)
```

Most CLI failures were already routed through these helpers.

Three regression preflight checks still bypassed that abstraction:

1. regression requested without a managed dataset,
2. regression requested without an explicit dataset version,
3. regression requested with more than one model.

Those checks behaved correctly, but they still owned their own formatting and direct `stderr` output.

Sprint 11.80 closes that architectural gap.

---

# Problem

Before Sprint 11.80, regression preflight validation directly formatted diagnostics inside `src/cli/app.py`.

Conceptually, the CLI had two different paths for the same failure category.

### Runtime input failure

```text
Input failure
    ↓
print_input_error(...)
    ↓
stderr
```

### Regression preflight input failure

```text
Input failure
    ↓
manual print(..., file=sys.stderr)
    ↓
stderr
```

The observable output was equivalent, but the implementation was inconsistent.

That matters because CLI diagnostics are part of the public process contract.

Duplicated diagnostic formatting can eventually cause drift in:

- message prefixes,
- punctuation,
- output streams,
- wording,
- classification,
- tests,
- downstream CI parsing.

The goal of Sprint 11.80 is to ensure one representation path exists for one diagnostic category.

---

# Design Principle

Sprint 11.80 applies the following architectural rule:

> CLI orchestration determines what failed. The diagnostics layer determines how that failure is presented.

The CLI remains responsible for:

- identifying invalid commands,
- enforcing preflight rules,
- classifying failures,
- controlling execution flow,
- selecting the appropriate exit-code category.

The diagnostics layer remains responsible for:

- stable diagnostic prefixes,
- rendering,
- writing diagnostic output to `stderr`.

The resulting boundary is:

```text
src/cli/app.py
        │
        ├── detects invalid regression request
        │
        ├── classifies it as an input failure
        │
        └── calls print_input_error(...)
                         │
                         ↓
              src/cli/diagnostics.py
                         │
                         ├── applies stable prefix
                         └── writes to stderr
```

This keeps responsibilities narrow and composable.

---

# Implementation

## Modified File

```text
src/cli/app.py
```

Regression preflight validation previously produced diagnostics directly.

### Before

```python
if regression_requested:
    if args.dataset is None:
        print(
            "Input error: regression execution requires "
            "a managed --dataset.",
            file=sys.stderr,
        )
        return 2

    if args.dataset_version is None:
        print(
            "Input error: regression execution requires "
            "an explicit --dataset-version.",
            file=sys.stderr,
        )
        return 2

    if len(args.models) != 1:
        print(
            "Input error: regression execution requires "
            "exactly one model.",
            file=sys.stderr,
        )
        return 2
```

### After

```python
if regression_requested:
    if args.dataset is None:
        print_input_error(
            "regression execution requires a managed --dataset."
        )
        return 2

    if args.dataset_version is None:
        print_input_error(
            "regression execution requires an explicit "
            "--dataset-version."
        )
        return 2

    if len(args.models) != 1:
        print_input_error(
            "regression execution requires exactly one model."
        )
        return 2
```

No user-visible wording changed.

For example:

```text
Input error: regression execution requires a managed --dataset.
```

and:

```text
Input error: regression execution requires exactly one model.
```

continue to be emitted to:

```text
stderr
```

with:

```text
exit code 2
```

---

# Removed Direct Diagnostic Dependency

Once the remaining regression preflight failures were routed through:

```python
print_input_error(...)
```

`src/cli/app.py` no longer needed to directly manage `sys.stderr` for those paths.

This reinforces a cleaner ownership model:

```text
app.py
    → orchestration and classification

diagnostics.py
    → rendering and diagnostic transport
```

The change reduces coupling and makes the CLI easier to evolve safely.

---

# Preflight Validation Cases

Sprint 11.80 centralizes three regression-specific input failures.

## 1. Managed Dataset Required

Regression execution requires a managed dataset.

A prompt-file invocation cannot be used as a regression candidate because regression provenance depends on managed dataset identity and versioning.

Invalid invocation:

```text
--prompts ...
--regression-result-output ...
```

Expected behavior:

```text
stderr:
Input error: regression execution requires a managed --dataset.

exit code:
2
```

Regression execution must not begin.

---

## 2. Explicit Dataset Version Required

Regression execution requires an explicit dataset version.

This prevents an implicit "latest" dataset state from becoming part of a regression comparison without being recorded explicitly.

Invalid invocation:

```text
--dataset candidate-suite
--regression-result-output ...
```

without:

```text
--dataset-version
```

Expected behavior:

```text
stderr:
Input error: regression execution requires an explicit --dataset-version.

exit code:
2
```

This preserves reproducibility and provenance integrity.

---

## 3. Exactly One Candidate Model Required

The current regression execution contract supports one candidate model per regression comparison.

An invocation containing multiple models is rejected before model execution begins.

Invalid invocation:

```text
--models model-a model-b
```

Expected behavior:

```text
stderr:
Input error: regression execution requires exactly one model.

exit code:
2
```

Neither candidate execution nor regression comparison should run.

---

# Test Hardening

## Modified File

```text
tests/cli/test_regression_execution.py
```

Existing regression tests already verified control flow.

Sprint 11.80 extends that verification to include the observable diagnostic contract.

The tests now protect:

- exact diagnostic category,
- `stderr` usage,
- absence of unexpected `stdout`,
- deterministic exit code,
- prevention of downstream execution.

This is important because a CLI contract is more than a return value.

It consists of:

```text
command
    +
stdout
    +
stderr
    +
exit code
    +
side effects
```

Sprint 11.80 ensures those pieces remain aligned.

---

# Why `stderr` Matters

Command-line programs distinguish normal output from diagnostics using process streams.

AI Test Lab follows that convention.

## `stdout`

Used for normal execution output such as:

- evaluation summaries,
- report locations,
- successful informational output.

## `stderr`

Used for:

- invalid input,
- regression execution failures,
- artifact failures,
- other diagnostic information.

This separation matters for:

- PowerShell scripts,
- shell pipelines,
- GitHub Actions,
- CI/CD runners,
- test harnesses,
- wrapper processes,
- future API or service adapters.

A caller can independently capture:

```text
normal program output
```

and:

```text
failure diagnostics
```

without parsing a mixed stream.

---

# Exit-Code Contract

Sprint 11.80 does not introduce or modify exit-code semantics.

The CLI continues to preserve the established process contract.

| Exit code | Meaning |
|---|---|
| `0` | Successful execution or regression gate allows the candidate |
| `1` | Evaluation failure or regression gate blocks the candidate |
| `2` | Invalid CLI input or configuration |
| `3` | Regression infrastructure, execution, or artifact failure |

Sprint 11.80 specifically hardens:

```text
invalid regression preflight input
        ↓
Input error: ...
        ↓
stderr
        ↓
exit code 2
```

The sprint changes implementation ownership, not observable behavior.

---

# Architectural Impact

Before Sprint 11.80:

```text
app.py
 ├── orchestration
 ├── validation
 ├── exit-code decisions
 └── some diagnostic formatting
```

After Sprint 11.80:

```text
app.py
 ├── orchestration
 ├── validation
 └── exit-code decisions

diagnostics.py
 └── diagnostic representation
```

This produces a stronger separation of concerns.

That boundary becomes increasingly important as AI Test Lab grows into a CI/CD quality-gate platform because public process behavior must remain deterministic even when internal implementation evolves.

---

# Compatibility

Sprint 11.80 is backward-compatible.

It does not change:

- CLI arguments,
- dataset semantics,
- regression comparison behavior,
- provenance construction,
- regression enforcement,
- report schemas,
- artifact formats,
- quality-gate decisions,
- process exit codes,
- diagnostic wording.

Existing callers should observe the same behavior before and after the refactor.

---

# Scope Guard

Sprint 11.80 intentionally does **not** introduce:

- structured JSON diagnostics,
- a logging framework,
- tracing,
- telemetry,
- new exception hierarchies,
- new exit codes,
- new regression algorithms,
- additional comparison metrics,
- statistical regression analysis,
- new quality-gate rules,
- provenance changes,
- report-schema changes,
- artifact-format changes.

Those concerns belong to separate architectural increments.

The sprint has one responsibility:

> Complete regression preflight diagnostic centralization while preserving the existing public CLI contract.

---

# Verification

Focused regression and diagnostic tests:

```text
13 passed in 0.61s
```

Full project regression suite:

```text
633 passed in 11.82s
```

The complete suite passes after the change.

This demonstrates that diagnostic centralization preserved behavior across the broader framework.

---

# Acceptance Criteria

- [x] regression preflight failures use `print_input_error(...)`
- [x] direct regression preflight `stderr` formatting is removed from `app.py`
- [x] missing managed dataset remains an input failure
- [x] missing explicit dataset version remains an input failure
- [x] multiple-model regression remains an input failure
- [x] input failures return exit code `2`
- [x] input diagnostics are emitted to `stderr`
- [x] diagnostics retain the stable `Input error:` prefix
- [x] invalid regression commands do not execute regression logic
- [x] focused CLI tests pass
- [x] complete project test suite passes
- [x] regression runtime semantics remain unchanged

---

# Result

Sprint 11.80 completes the centralization of regression preflight diagnostics.

The regression CLI now follows a consistent failure-processing pattern:

```text
detect
   ↓
classify
   ↓
diagnose
   ↓
return deterministic exit code
```

Each layer now has a clearer responsibility:

```text
CLI orchestration
    → detects and classifies failures

Diagnostic layer
    → renders stable human-readable diagnostics

Regression engine
    → owns regression behavior
```

This reduces duplication, improves testability, and strengthens the CLI as a durable automation boundary for CI/CD environments.

---

# Final Sprint Summary

Sprint 11.80 hardened the regression CLI by routing its remaining regression preflight input failures through the centralized diagnostic contract introduced in Sprint 11.79.

The sprint:

- removed duplicated diagnostic formatting from `src/cli/app.py`,
- standardized preflight failures through `print_input_error(...)`,
- preserved `stderr` behavior,
- preserved exit code `2` for invalid input,
- strengthened CLI contract tests,
- prevented invalid regression invocations from reaching execution,
- introduced no changes to regression algorithms or public behavior.

Verification completed successfully:

```text
Focused tests: 13 passed
Full suite:     633 passed
```

Sprint 11.80 therefore leaves AI Test Lab with a cleaner and more durable boundary between validation, diagnostics, and regression execution.