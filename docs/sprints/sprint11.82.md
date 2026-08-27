# Sprint 11.82 — CLI Exit-Code Contract Completion

## Status

**Completed**

## Summary

Sprint 11.82 completes the CLI exit-code centralization started in Sprint 11.81.

Sprint 11.81 introduced the authoritative process-level exit-code vocabulary:

```python
class CliExitCode(IntEnum):
    SUCCESS = 0
    FAILURE = 1
    INPUT_ERROR = 2
    INFRASTRUCTURE_ERROR = 3
```

That established a single semantic definition for AI Test Lab's process outcomes.

However, several legacy CLI command paths still returned raw numeric values such as:

```python
return 0
```

and:

```python
return 1
```

Sprint 11.82 removes those remaining magic-number process returns from the CLI layer.

The result is a completed process contract:

```text
CLI outcome
    ↓
semantic classification
    ↓
CliExitCode
    ↓
stable integer process status
```

No public exit-code values change.

No CLI behavior changes.

This sprint completes the migration from distributed numeric process statuses to one explicit semantic vocabulary.

---

## Objective

Ensure every explicit CLI process-return path uses the centralized `CliExitCode` contract rather than raw numeric literals.

The required invariant is:

```text
No CLI command path should communicate
process semantics through unexplained
return 0 / 1 / 2 / 3 literals.
```

Instead:

```python
return CliExitCode.SUCCESS
```

```python
return CliExitCode.FAILURE
```

```python
return CliExitCode.INPUT_ERROR
```

```python
return CliExitCode.INFRASTRUCTURE_ERROR
```

The numeric operating-system interface remains unchanged.

---

## Background

Sprint 11's regression work progressively hardened the CLI into a dependable automation boundary.

The relevant progression includes:

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
        ↓
CLI exit-code contract centralization
        ↓
CLI exit-code contract completion
```

Sprint 11.81 created:

```text
src/cli/exit_codes.py
```

with:

```python
class CliExitCode(IntEnum):
    SUCCESS = 0
    FAILURE = 1
    INPUT_ERROR = 2
    INFRASTRUCTURE_ERROR = 3
```

That established the semantic contract.

Sprint 11.82 ensures the remaining CLI command paths actually use it consistently.

---

# Problem

Before Sprint 11.82, AI Test Lab had one authoritative exit-code definition but still contained several legacy raw returns.

A repository scan identified:

```text
src/cli/app.py
    return 0
    return 1
    return 0

src/cli/dataset_commands.py
    return 0
    return 0
    return 0
```

These values were behaviorally correct.

The issue was architectural consistency.

For example:

```python
return 1
```

requires the reader to know that:

```text
1 = execution completed but produced a failing quality outcome
```

while:

```python
return CliExitCode.FAILURE
```

expresses that meaning directly.

Likewise:

```python
return 0
```

does not distinguish process semantics from an arbitrary internal numeric value.

The contract was centralized in definition but not yet fully centralized in usage.

---

# Design Principle

Sprint 11.82 establishes this rule:

> Process outcomes must be expressed semantically inside the CLI and numerically only at the process boundary.

Application code should reason about:

```text
SUCCESS
FAILURE
INPUT_ERROR
INFRASTRUCTURE_ERROR
```

The operating system continues to receive:

```text
0
1
2
3
```

Because `CliExitCode` derives from `IntEnum`, no translation layer is required.

The boundary remains:

```text
application semantics
        ↓
CliExitCode
        ↓
integer-compatible value
        ↓
SystemExit
        ↓
operating system / CI runner
```

---

# Implementation

Sprint 11.82 modifies two CLI modules.

```text
src/cli/app.py
src/cli/dataset_commands.py
```

No new exit-code categories are introduced.

---

## `src/cli/app.py`

Three remaining literal process returns were replaced.

### Dataset validation success

Before:

```python
if result.is_valid:
    print("\nDataset validation passed.")
    return 0
```

After:

```python
if result.is_valid:
    print("\nDataset validation passed.")
    return CliExitCode.SUCCESS
```

---

## Dataset validation failure

Before:

```python
print("\nDataset validation failed.")
return 1
```

After:

```python
print("\nDataset validation failed.")
return CliExitCode.FAILURE
```

This distinction is important.

An invalid dataset validation result is not an infrastructure failure and not a malformed command invocation.

Validation executed successfully and produced a negative result.

Therefore:

```text
dataset validation failed
        ↓
CliExitCode.FAILURE
        ↓
1
```

---

## Evaluation-profile listing

Before:

```python
if args.list_evaluation_profiles:
    print_evaluation_profiles(list_profiles())
    return 0
```

After:

```python
if args.list_evaluation_profiles:
    print_evaluation_profiles(list_profiles())
    return CliExitCode.SUCCESS
```

Successful informational commands now use the same semantic success vocabulary as other CLI paths.

---

# Dataset Command Completion

## Modified File

```text
src/cli/dataset_commands.py
```

The module now imports:

```python
from src.cli.exit_codes import CliExitCode
```

Three successful command paths were converted from:

```python
return 0
```

to:

```python
return CliExitCode.SUCCESS
```

These include:

- listing datasets when none exist,
- successfully listing available datasets,
- successfully displaying dataset information.

The observable process status remains:

```text
0
```

---

# Completed Exit-Code Contract

After Sprint 11.82, the CLI process vocabulary is:

| Semantic value | Integer | Meaning |
|---|---:|---|
| `CliExitCode.SUCCESS` | `0` | Requested operation completed successfully |
| `CliExitCode.FAILURE` | `1` | Execution completed but produced a failing quality/validation result |
| `CliExitCode.INPUT_ERROR` | `2` | Invocation or configuration is invalid |
| `CliExitCode.INFRASTRUCTURE_ERROR` | `3` | Infrastructure prevented a trustworthy result |

This table is now both:

```text
documented contract
```

and:

```text
code-level vocabulary
```

---

# Why `FAILURE` Is Different From `INPUT_ERROR`

Sprint 11.82 preserves an important process-level distinction.

Consider dataset validation.

If the user asks AI Test Lab to validate a legitimate dataset and validation discovers errors, the command itself was valid.

The system successfully performed the requested operation.

The result was negative.

Therefore:

```text
validation ran
        ↓
validation failed
        ↓
CliExitCode.FAILURE
        ↓
1
```

This is different from:

```text
invalid dataset identifier
        ↓
request cannot be processed correctly
        ↓
CliExitCode.INPUT_ERROR
        ↓
2
```

The distinction is valuable for automation.

A CI pipeline can treat:

```text
1
```

as:

> The quality check ran and blocked the candidate.

while:

```text
2
```

means:

> The invocation or configuration itself must be corrected.

---

# Why This Matters

Exit codes form a public machine-readable boundary.

A CI system may know nothing about AI Test Lab's internal Python classes.

It may only observe:

```text
command
stdout
stderr
exit status
artifacts
```

That makes exit-code semantics part of the product's external automation contract.

Centralizing those semantics improves:

- readability,
- maintainability,
- code review,
- CI predictability,
- compatibility,
- testability,
- future extension safety.

---

# Removal of Magic Process Numbers

Sprint 11.82 explicitly verifies that raw CLI process returns have been eliminated.

The verification scan is:

```powershell
Get-ChildItem .\src\cli -Recurse -Filter *.py |
    Select-String -Pattern 'return\s+[0-3]\b|SystemExit\([0-3]\)'
```

Expected result:

```text
no output
```

This means the CLI source contains no direct:

```text
return 0
return 1
return 2
return 3
SystemExit(0)
SystemExit(1)
SystemExit(2)
SystemExit(3)
```

process semantics.

The semantic contract is now used consistently.

---

# Relationship to Sprint 11.81

Sprint 11.81 and Sprint 11.82 intentionally divide the work into two small architectural increments.

## Sprint 11.81

Defined the vocabulary:

```text
CliExitCode
```

and protected the numeric mapping.

## Sprint 11.82

Completed adoption of that vocabulary across remaining CLI command handlers.

Conceptually:

```text
Sprint 11.81
    ↓
Define the contract

Sprint 11.82
    ↓
Complete contract usage
```

Together they establish a durable process boundary.

---

# Process-Level Architecture

Before Sprint 11.81:

```text
CLI
 ├── return 0
 ├── return 1
 ├── return 2
 └── return 3
```

After Sprint 11.81:

```text
CLI
 ├── CliExitCode
 ├── some semantic returns
 └── some legacy numeric returns
```

After Sprint 11.82:

```text
CLI
        ↓
CliExitCode
        ├── SUCCESS
        ├── FAILURE
        ├── INPUT_ERROR
        └── INFRASTRUCTURE_ERROR
        ↓
integer-compatible process status
```

The migration is complete.

---

# Compatibility

Sprint 11.82 is backward-compatible.

It does not change:

- numeric process statuses,
- CLI arguments,
- command syntax,
- dataset-validation semantics,
- dataset-management behavior,
- evaluation logic,
- regression comparison logic,
- regression enforcement,
- quality-gate policy,
- diagnostics,
- `stdout`,
- `stderr`,
- report schemas,
- artifact schemas,
- provenance,
- evaluation profiles.

For external callers:

```text
before
0 / 1 / 2 / 3

after
0 / 1 / 2 / 3
```

Only internal representation changes.

---

# Scope Guard

Sprint 11.82 intentionally does **not** introduce:

- additional process exit codes,
- shell-specific exit semantics,
- exception hierarchy changes,
- diagnostic-format changes,
- logging infrastructure,
- telemetry,
- JSON diagnostics,
- new dataset validation rules,
- new regression policies,
- new quality metrics,
- new quality-gate decisions,
- new artifact formats,
- API status-code mappings.

The sprint has one responsibility:

> Complete semantic adoption of the existing CLI process exit-code contract.

---

# Verification

CLI-focused test suite:

```text
39 passed in 0.69s
```

Full project regression suite:

```text
635 passed in 10.59s
```

Exit-code literal scan:

```text
no matches
```

Formatting verification:

```text
git diff --check
```

completed successfully with no remaining whitespace errors.

These checks demonstrate that the exit-code refactor preserves existing runtime behavior while completing the architectural contract.

---

# Acceptance Criteria

- [x] Dataset validation success uses `CliExitCode.SUCCESS`
- [x] Dataset validation failure uses `CliExitCode.FAILURE`
- [x] Evaluation-profile listing uses `CliExitCode.SUCCESS`
- [x] Dataset-list command success uses `CliExitCode.SUCCESS`
- [x] Empty dataset-list success uses `CliExitCode.SUCCESS`
- [x] Dataset-info success uses `CliExitCode.SUCCESS`
- [x] No CLI `return 0` process literals remain
- [x] No CLI `return 1` process literals remain
- [x] No CLI `return 2` process literals remain
- [x] No CLI `return 3` process literals remain
- [x] No direct `SystemExit(0..3)` literals remain
- [x] Existing numeric exit-code meanings remain unchanged
- [x] CLI-focused tests pass
- [x] Full project regression suite passes
- [x] `git diff --check` passes
- [x] No unrelated runtime behavior changes are introduced

---

# Result

Sprint 11.82 completes AI Test Lab's CLI exit-code contract.

The process boundary now follows one consistent pattern:

```text
operation executes
        ↓
outcome classified
        ↓
CliExitCode selected
        ↓
stable integer returned
        ↓
shell / CI/CD runner
```

The CLI no longer relies on scattered numeric literals to communicate process meaning.

Instead, every supported process category has a semantic name backed by a stable integer.

This creates a clearer and more durable automation contract for:

- local shell usage,
- PowerShell scripting,
- GitHub Actions,
- CI/CD quality gates,
- wrapper tools,
- future platform integrations.

---

## Final Sprint Summary

Sprint 11.82 completes the exit-code centralization introduced in Sprint 11.81.

The sprint:

- removed the final six raw CLI process-return literals,
- converted remaining success paths to `CliExitCode.SUCCESS`,
- converted dataset validation failure to `CliExitCode.FAILURE`,
- extended `CliExitCode` usage into dataset command handlers,
- preserved the existing `0 / 1 / 2 / 3` process interface,
- verified the CLI contains no remaining direct process-status literals,
- preserved all existing runtime and quality-gate behavior.

Verification:

```text
CLI tests:          39 passed
Full suite:         635 passed
Exit literal scan:  clean
git diff --check:   clean
```

With Sprint 11.82 complete, AI Test Lab now has one explicit and consistently applied process-level exit-code vocabulary across its CLI boundary.