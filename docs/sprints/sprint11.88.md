# Sprint 11.88 — Deterministic Infrastructure-Error Process Contract

## Status

**Completed**

Sprint 11.88 strengthens the AI Test Lab CLI process contract by proving that infrastructure failures produce a deterministic operating-system exit code.

The CLI now has verified subprocess behavior for all four public exit-code categories:

| Exit Code | Meaning |
|---:|---|
| `0` | Successful execution |
| `1` | Evaluation or validation completed but failed |
| `2` | Invalid user input or invocation |
| `3` | Infrastructure or runtime failure |

This sprint specifically closes the final gap: proving exit code `3` through a real CLI subprocess rather than only through mocked unit-level execution.

---

## Objective

The objective of Sprint 11.88 was to establish a reliable process-level contract for infrastructure failures.

The required behavior was:

```text
Infrastructure failure
        ↓
CLI recognizes the failure category
        ↓
stable diagnostic written to stderr
        ↓
no Python traceback exposed as normal CLI output
        ↓
process terminates with exit code 3
```

This distinction is important for CI/CD systems and automation because an infrastructure problem must not be confused with:

- a quality-gate failure,
- a failed evaluation,
- a dataset validation failure,
- or an invalid command invocation.

---

## Problem

Before this sprint, AI Test Lab already defined:

```python
CliExitCode.INFRASTRUCTURE_ERROR == 3
```

and regression-specific infrastructure paths could return exit code `3`.

However, those behaviors were primarily verified inside the Python process using mocks.

That left an important process-boundary question unanswered:

> When AI Test Lab is launched as a real operating-system process and encounters an infrastructure failure, does the actual process reliably terminate with exit code `3`?

For CI/CD integration, the answer must be deterministic.

---

## Existing Process Contract

Before Sprint 11.88, the real CLI subprocess contract already covered:

### Successful execution

```text
exit code = 0
```

Example:

```text
ai-test-lab --list-evaluation-profiles
```

---

### Evaluation or validation failure

```text
exit code = 1
```

Example:

```text
dataset validation completes and finds invalid dataset content
```

The CLI successfully performed its job, but the evaluated condition failed.

---

### Invalid invocation

```text
exit code = 2
```

Example:

```text
incomplete regression arguments
```

This represents a caller or command-line usage error.

---

### Missing process-level coverage

The remaining unverified category was:

```text
infrastructure failure → exit code 3
```

Sprint 11.88 closes that gap.

---

# Design Decision

## Do Not Depend on Ollama

The first candidate infrastructure-process test attempted to trigger regression execution with missing baseline artifacts.

That approach failed before reaching the intended infrastructure boundary.

The subprocess returned:

```text
Input error: 'example'
```

with:

```text
exit code = 2
```

because the named dataset did not exist.

This demonstrated an important testing principle:

> A deterministic process-contract test must control every earlier execution boundary.

The infrastructure test must not depend on:

- Ollama availability,
- model installation,
- network behavior,
- machine configuration,
- external services,
- timing,
- or unrelated dataset state.

---

# Deterministic Failure Strategy

Sprint 11.88 uses a real local filesystem failure.

The test creates an empty prompt file:

```json
[]
```

This allows the CLI to proceed through normal input loading without executing an actual model request.

The test then deliberately creates a directory and supplies that directory as the JSON report output path.

Conceptually:

```text
empty prompts
    ↓
0 model test executions
    ↓
CLI reaches report generation
    ↓
JSON report target is an existing directory
    ↓
file write raises an OS-level filesystem error
    ↓
CLI classifies it as infrastructure failure
    ↓
stderr receives stable diagnostic
    ↓
process exits with code 3
```

This mechanism is deterministic and entirely local.

---

# Implementation

## Infrastructure Diagnostic

A general infrastructure diagnostic was added to the CLI diagnostics layer:

```python
def print_infrastructure_error(error: object) -> None:
    print(
        f"Infrastructure error: {error}",
        file=sys.stderr,
    )
```

This keeps infrastructure diagnostics consistent with the existing CLI error-routing model.

The diagnostic is written to:

```text
stderr
```

rather than standard output.

---

## Report-Writing Infrastructure Boundary

Report generation is now protected with a targeted filesystem exception boundary.

Conceptually:

```python
try:
    JsonReporter(args.report).write(results)
    HtmlReporter(args.html_report).write(results)
except OSError as error:
    print_infrastructure_error(error)
    return CliExitCode.INFRASTRUCTURE_ERROR
```

The implementation intentionally catches:

```python
OSError
```

rather than:

```python
Exception
```

---

# Why `OSError` Is Important

Using a broad exception handler such as:

```python
except Exception:
```

would make the CLI more difficult to debug.

Programming defects such as:

```text
TypeError
AttributeError
AssertionError
unexpected internal logic defects
```

should not automatically be relabeled as ordinary infrastructure conditions.

The targeted boundary instead handles operating-system and filesystem failures such as:

```text
PermissionError
FileNotFoundError
IsADirectoryError
other filesystem I/O failures
```

These belong to the `OSError` hierarchy.

The result is a stronger classification boundary:

```text
known user mistake
    → INPUT_ERROR

completed evaluation with failed condition
    → FAILURE

known filesystem/infrastructure problem
    → INFRASTRUCTURE_ERROR

unexpected programming defect
    → remains visible during development
```

This preserves debuggability while still providing deterministic automation behavior.

---

# Process-Level Test

The process-contract suite now includes a real subprocess infrastructure test.

Conceptually:

```python
def test_real_cli_report_write_failure_returns_infrastructure_error(
    tmp_path,
) -> None:
    prompts_path = tmp_path / "empty-prompts.json"
    prompts_path.write_text("[]", encoding="utf-8")

    invalid_report_path = tmp_path / "report-target"
    invalid_report_path.mkdir()

    html_report_path = tmp_path / "report.html"

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "src.cli.app",
            "--prompts",
            str(prompts_path),
            "--report",
            str(invalid_report_path),
            "--html-report",
            str(html_report_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == CliExitCode.INFRASTRUCTURE_ERROR
    assert "Infrastructure error:" in completed.stderr
    assert "Traceback" not in completed.stderr
```

This verifies the behavior at the true operating-system process boundary.

---

# Verified CLI Exit-Code Matrix

Sprint 11.88 completes the real subprocess classification matrix:

| Scenario | Expected Exit Code | stdout | stderr |
|---|---:|---|---|
| Successful CLI operation | `0` | Normal command output | Empty |
| Evaluation / validation failure | `1` | Evaluation or validation results | Empty |
| Invalid command/input | `2` | Minimal or empty | Input diagnostic |
| Infrastructure failure | `3` | No false success output | Infrastructure diagnostic |

The CLI can now communicate four materially different execution outcomes to CI/CD and shell automation.

---

# Why This Matters for CI/CD

CI systems generally inspect process exit codes rather than understanding internal Python exceptions.

Without deterministic classification, these two failures might appear identical:

```text
Model quality failed
```

and:

```text
AI Test Lab could not write its report
```

They are operationally very different.

After Sprint 11.88:

```text
exit 1
```

means:

> AI Test Lab successfully performed the evaluation, but the evaluated condition failed.

While:

```text
exit 3
```

means:

> AI Test Lab could not reliably complete the required infrastructure operation.

This allows CI pipelines to respond differently.

Example:

```text
exit 1
    → fail quality gate

exit 2
    → fix pipeline invocation

exit 3
    → investigate infrastructure/runtime environment
```

This becomes increasingly important as AI Test Lab moves toward automated quality gates and production CI integration.

---

# Testing

## Focused Process Contract

The process-level CLI suite was executed after implementation.

Result:

```text
4 passed
```

The four verified subprocess conditions are:

```text
SUCCESS
FAILURE
INPUT_ERROR
INFRASTRUCTURE_ERROR
```

---

## Full Regression Suite

The complete AI Test Lab test suite was executed.

Final result:

```text
644 passed in 16.14s
```

No regressions were introduced.

---

# Acceptance Criteria

Sprint 11.88 is complete because the following requirements are satisfied:

- [x] Infrastructure failures have a dedicated process-level contract.
- [x] Infrastructure failures return exit code `3`.
- [x] The behavior is verified through a real subprocess.
- [x] The test does not depend on Ollama availability.
- [x] The test does not depend on external services or networking.
- [x] The failure mechanism is deterministic.
- [x] Infrastructure diagnostics are written to `stderr`.
- [x] Python traceback text is not exposed as part of the expected CLI diagnostic.
- [x] Report filesystem errors are classified as infrastructure failures.
- [x] Exception handling remains targeted rather than catching every `Exception`.
- [x] Existing exit codes `0`, `1`, and `2` continue to behave correctly.
- [x] Full regression suite passes.
- [x] `644 passed in 16.14s`.

---

# Architectural Result

AI Test Lab now has a stable four-state CLI process contract:

```text
                    AI Test Lab CLI
                          │
          ┌───────────────┼────────────────┐
          │               │                │
       SUCCESS          FAILURE        INPUT ERROR
          │               │                │
          0               1                2
                          │
                   INFRASTRUCTURE
                       ERROR
                          │
                          3
```

More precisely:

```text
0 → command completed successfully

1 → command completed, but evaluation/validation failed

2 → caller supplied invalid input or invocation

3 → runtime/infrastructure prevented reliable completion
```

This contract is now verified at the operating-system subprocess boundary.

---

# Engineering Principles Reinforced

Sprint 11.88 reinforces several long-term AI Test Lab design principles.

## Determinism

Tests should not depend on transient external conditions when a controlled local failure can prove the same contract.

## Explicit Failure Classification

Different failure categories should remain distinguishable to automation.

## Stable Process Interfaces

Exit codes are part of the public CLI contract and must be tested like any other external API.

## Narrow Exception Boundaries

Known infrastructure failures should be classified without hiding unrelated programming defects.

## CI/CD Readiness

Machine-readable process behavior is essential for reliable quality gates and automated pipelines.

---

# Summary

Sprint 11.88 completes the deterministic CLI exit-code process contract.

Before this sprint, AI Test Lab already defined infrastructure exit code `3`, but the real subprocess boundary was not fully proven.

The sprint introduced a deterministic local filesystem failure that:

```text
does not require Ollama
does not require networking
does not rely on timing
does not use subprocess mocks
```

and verifies:

```text
filesystem infrastructure failure
        ↓
stable stderr diagnostic
        ↓
no expected traceback leakage
        ↓
real process exit code 3
```

Final verification:

```text
4 CLI process-contract tests passed
644 total tests passed in 16.14s
```

AI Test Lab now exposes a complete and test-backed CLI process contract suitable for increasingly strict CI/CD quality-gate integration.