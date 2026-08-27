# Sprint 11.80 — Regression Preflight Diagnostic Hardening

## Status

**Completed**

Sprint 11.80 strengthens the AI Test Lab regression CLI by completing the diagnostic boundary introduced in Sprint 11.79.

Sprint 11.79 established centralized diagnostic helpers for CLI failures. However, three regression preflight validation paths still formatted their own `Input error:` messages directly inside `src/cli/app.py`.

Sprint 11.80 removes that remaining duplication.

The regression CLI now routes all supported preflight input failures through the same centralized diagnostic function:

```python
print_input_error(...)
```

This keeps diagnostic formatting consistent, independently testable, and separated from CLI orchestration.

---

## Objective

Complete the regression CLI input-diagnostic boundary without changing runtime behavior.

The CLI must continue to:

- reject invalid regression invocations before evaluation begins,
- write input diagnostics to `stderr`,
- preserve the stable `Input error:` prefix,
- return exit code `2` for invalid regression input,
- avoid executing regression logic when preflight validation fails,
- keep diagnostic formatting out of CLI orchestration code.

The intended flow is:

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

---

## Background

Recent Sprint 11 work progressively established the regression CLI as a dependable CI/CD-facing quality-gate interface.

The relevant sequence now includes:

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

with dedicated helpers for:

```python
print_input_error(...)
print_regression_execution_error(...)
print_regression_artifact_error(...)
```

That sprint centralized most diagnostic formatting.

However, three early regression validation paths still remained directly embedded inside:

```text
src/cli/app.py
```

Those paths handled:

1. regression requested without a managed dataset,
2. regression requested without an explicit dataset version,
3. regression requested with more than one model.

Their behavior was correct, but their implementation bypassed the diagnostic abstraction that Sprint 11.79 had established.

Sprint 11.80 closes that gap.

---

# Problem

Before Sprint 11.80, regression preflight validation contained direct formatting such as:

```python
print(
    "Input error: regression execution requires "
    "a managed --dataset.",
    file=sys.stderr,
)
```

and similar blocks for dataset-version and model-count validation.

This created two different ways for the application to produce the same category of diagnostic.

Conceptually:

```text
Input failure from runtime loading
        ↓
print_input_error(...)
```

but:

```text
Input failure from regression preflight
        ↓
manual print(..., file=sys.stderr)
```

The observable behavior was identical, but the architectural path was inconsistent.

That inconsistency matters because CLI diagnostics are part of the public process contract.

If diagnostic representation is duplicated, future changes could accidentally introduce differences in:

- prefixes,
- punctuation,
- output streams,
- formatting,
- classification,
- test coverage.

---

# Design Principle

Sprint 11.80 applies a simple rule:

> CLI orchestration determines what failed. The diagnostics layer determines how that failure is presented.

The CLI should therefore own:

- regression preflight rules,
- failure classification,
- control flow,
- exit-code selection.

The diagnostics module should own:

- stable message prefixes,
- rendering,
- output to `stderr`.

The resulting boundary is:

```text
app.py
  │
  ├── detects invalid regression request
  │
  ├── classifies it as an input error
  │
  └── calls print_input_error(...)
            │
            ↓
      diagnostics.py
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

Regression preflight validation previously formatted its own diagnostics.

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

The observable CLI messages remain unchanged.

For example:

```text
Input error: regression execution requires a managed --dataset.
```

and:

```text
Input error: regression execution requires exactly one model.
```

still go to:

```text
stderr
```

and still produce:

```text
exit code 2
```

---

# Removed Direct Diagnostic Dependency

Once the remaining regression preflight diagnostics were routed through:

```python
print_input_error(...)
```

`src/cli/app.py` no longer needed to directly use:

```python
sys.stderr
```

for these paths.

This further reinforces the separation between:

```text
CLI orchestration
```

and:

```text
diagnostic transport and formatting
```

---

# Test Hardening

## Modified File

```text
tests/cli/test_regression_execution.py
```

Existing regression preflight tests already verified that invalid commands:

- return exit code `2`,
- do not run normal model execution,
- do not execute regression comparison.

Sprint 11.80 extends those tests to verify the observable diagnostic contract as well.

---

## Managed Dataset Requirement

Regression execution requires a managed dataset.

An invocation using prompt-file input is rejected before regression execution begins.

The test now verifies:

```text
stdout = empty
```

```text
stderr =
Input error: regression execution requires a managed --dataset.
```

and:

```text
exit code = 2
```

This confirms both control-flow behavior and user-visible behavior.

---

## Single-Model Requirement

Regression execution currently supports exactly one candidate model.

When multiple models are supplied, the CLI must reject the request before model execution.

The test verifies:

```text
MultiModelRunner.run_tests()
```

is not called.

It also verifies:

```text
execute_evaluation_run_regression()
```

is not called.

The emitted diagnostic must remain:

```text
Input error: regression execution requires exactly one model.
```

on:

```text
stderr
```

with:

```text
exit code 2
```

---

# Why `stderr` Matters

CLI consumers distinguish normal program output from diagnostics through process streams.

AI Test Lab preserves this convention:

```text
stdout
```

is used for normal execution information and reports.

```text
stderr
```

is used for failures and invalid command diagnostics.

This matters for:

- shell scripts,
- CI pipelines,
- GitHub Actions,
- automated test harnesses,
- future process wrappers,
- external integrations.

A caller can therefore independently capture:

```text
normal output
```

and:

```text
failure diagnostics
```

without parsing a mixed stream.

---

# Exit-Code Contract

Sprint 11.80 does not change exit-code semantics.

The regression CLI continues to maintain the existing process contract.

```text
0
```

Successful regression execution.

```text
1
```

Regression quality gate blocks the candidate or ordinary evaluation failures are reported where applicable.

```text
2
```

Invalid CLI input or configuration.

```text
3
```

Regression infrastructure, execution, or artifact failure.

Sprint 11.80 specifically strengthens the relationship:

```text
invalid regression preflight input
        ↓
Input error: ...
        ↓
stderr
        ↓
exit code 2
```

---

# Architectural Impact

Sprint 11.80 is intentionally small, but it removes an important inconsistency.

Before:

```text
app.py
 ├── orchestration
 ├── validation
 ├── exit-code decisions
 └── some diagnostic formatting
```

After:

```text
app.py
 ├── orchestration
 ├── validation
 └── exit-code decisions

diagnostics.py
 └── diagnostic representation
```

This reduces coupling and gives the CLI a cleaner architecture.

---

# What Sprint 11.80 Does Not Do

Sprint 11.80 intentionally avoids expanding scope.

It does not introduce:

- a logging framework,
- structured JSON diagnostics,
- telemetry,
- tracing,
- exception hierarchies,
- new regression algorithms,
- new comparison metrics,
- new quality-gate rules,
- provenance changes,
- result-schema changes,
- artifact-format changes,
- new exit codes.

These would represent separate architectural concerns.

The purpose of Sprint 11.80 is narrower:

> Finish centralizing regression preflight diagnostics and prove that the public CLI contract remains stable.

---

# Verification

Focused CLI diagnostic and regression tests:

```text
13 passed in 0.61s
```

Full project regression suite:

```text
633 passed in 11.82s
```

The complete test suite passes after the change.

This demonstrates that the refactor preserved existing behavior across the wider AI Test Lab framework.

---

# Acceptance Criteria

Sprint 11.80 is complete when:

- [x] regression preflight errors use `print_input_error(...)`
- [x] direct preflight `stderr` formatting is removed from `app.py`
- [x] missing managed dataset remains an input failure
- [x] missing explicit dataset version remains an input failure
- [x] multiple-model regression remains an input failure
- [x] preflight failures return exit code `2`
- [x] diagnostics are written to `stderr`
- [x] diagnostics retain the stable `Input error:` prefix
- [x] invalid regression commands do not execute regression logic
- [x] focused CLI tests pass
- [x] the complete project test suite passes
- [x] no regression runtime semantics change

---

# Result

Sprint 11.80 completes the centralization of regression preflight diagnostics.

The regression CLI now follows one consistent pattern:

```text
detect
    ↓
classify
    ↓
diagnose
    ↓
return deterministic exit code
```

The CLI remains responsible for orchestration.

The diagnostic layer remains responsible for representation.

The regression engine remains responsible for regression behavior.

That separation is important as AI Test Lab continues evolving toward a dependable automated quality-gate platform for CI/CD environments.

---

## Final Sprint Summary

Sprint 11.80 hardened the regression CLI by routing its remaining preflight input failures through the centralized diagnostic contract established in Sprint 11.79.

The change removes duplicated diagnostic formatting from `src/cli/app.py`, strengthens tests around `stderr` output, preserves deterministic exit-code behavior, and leaves regression execution semantics unchanged.

Verification completed successfully:

```text
Focused tests: 13 passed
Full suite:     633 passed
```

Sprint 11.80 therefore leaves the regression CLI with a cleaner and more durable boundary between validation, diagnostics, and execution.