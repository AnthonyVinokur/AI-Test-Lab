# Sprint 11.83 — CLI Exit-Code Contract Enforcement

## Status

**Completed**

## Summary

Sprint 11.83 converts the CLI exit-code convention established in Sprints 11.81 and 11.82 into an automated repository invariant.

Sprint 11.81 introduced the authoritative process-level vocabulary:

```python
from enum import IntEnum


class CliExitCode(IntEnum):
    SUCCESS = 0
    FAILURE = 1
    INPUT_ERROR = 2
    INFRASTRUCTURE_ERROR = 3
```

Sprint 11.82 completed adoption of that vocabulary across the remaining CLI command paths by removing the final raw `return 0` / `return 1` process literals.

Sprint 11.83 adds permanent regression protection so those raw process literals cannot be reintroduced accidentally.

The sprint adds a focused contract test that scans the CLI source tree and fails if direct process-status literals appear again.

The resulting rule is:

```text
CLI process outcome
        ↓
semantic classification
        ↓
CliExitCode
        ↓
stable integer process status
```

and never:

```text
CLI process outcome
        ↓
unexplained return 0 / 1 / 2 / 3
```

No runtime behavior changes.

No exit-code values change.

This sprint makes the exit-code contract self-enforcing.

---

## Objective

Prevent future CLI changes from bypassing the centralized `CliExitCode` contract.

The required invariant is:

> Explicit CLI process-status decisions must use `CliExitCode` rather than direct numeric literals.

The contract test protects against reintroducing constructs such as:

```python
return 0
return 1
return 2
return 3
```

or:

```python
SystemExit(0)
SystemExit(1)
SystemExit(2)
SystemExit(3)
```

Instead, process outcomes must be represented semantically:

```python
return CliExitCode.SUCCESS
return CliExitCode.FAILURE
return CliExitCode.INPUT_ERROR
return CliExitCode.INFRASTRUCTURE_ERROR
```

---

## Background

Sprint 11 has progressively hardened the AI Test Lab CLI into a dependable automation boundary.

Relevant progression:

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
        ↓
CLI exit-code contract enforcement
```

The last three sprints form a deliberate three-step sequence:

```text
Sprint 11.81 → define the contract
Sprint 11.82 → complete adoption
Sprint 11.83 → enforce the invariant
```

---

## Problem

Before Sprint 11.83, the CLI exit-code contract was correct but still depended partly on developer discipline.

Sprint 11.82 verified the source manually with:

```powershell
Get-ChildItem .\src\cli -Recurse -Filter *.py |
    Select-String -Pattern 'return\s+[0-3]\b|SystemExit\([0-3]\)'
```

The expected result was:

```text
no matches
```

That proved the migration was complete at that moment.

However, a manual scan does not protect the repository from future regressions.

A later change could accidentally introduce:

```python
return 1
```

and still appear behaviorally correct because the operating system would receive the expected numeric value.

The problem is architectural, not merely behavioral.

The numeric value might be correct while the semantic contract is bypassed.

Sprint 11.83 closes that gap.

---

## Design Principle

Sprint 11.83 establishes this repository rule:

> Important automation contracts should be executable, not merely documented.

The exit-code contract now exists at three levels:

```text
Documentation
     ↓
Semantic type
     ↓
Automated enforcement
```

Specifically:

```text
docs
     ↓
CliExitCode(IntEnum)
     ↓
test_exit_code_contract.py
```

---

## Implementation

### Added File

```text
tests/test_exit_code_contract.py
```

The test scans:

```text
src/cli/**/*.py
```

for direct numeric process exits.

Core implementation:

```python
from pathlib import Path
import re


CLI_ROOT = Path("src/cli")

RAW_PROCESS_EXIT_PATTERN = re.compile(
    r"return\s+[0-3]\b|SystemExit\([0-3]\)"
)


def test_cli_does_not_use_raw_process_exit_codes() -> None:
    violations: list[str] = []

    for path in CLI_ROOT.rglob("*.py"):
        source = path.read_text(encoding="utf-8")

        for line_number, line in enumerate(source.splitlines(), start=1):
            if RAW_PROCESS_EXIT_PATTERN.search(line):
                violations.append(
                    f"{path}:{line_number}: {line.strip()}"
                )

    assert not violations, (
        "CLI process exit codes must use CliExitCode:\n"
        + "\n".join(violations)
    )
```

The implementation intentionally remains small and local.

No generalized linting framework was introduced.

No new dependency was added.

No AST-processing infrastructure was added.

---

## What the Test Protects

The test rejects direct process literals such as:

```python
return 0
return 1
return 2
return 3
```

and:

```python
SystemExit(0)
SystemExit(1)
SystemExit(2)
SystemExit(3)
```

The supported semantic vocabulary remains:

| Semantic value | Integer | Meaning |
|---|---:|---|
| `CliExitCode.SUCCESS` | `0` | Requested operation completed successfully |
| `CliExitCode.FAILURE` | `1` | Execution completed but produced a failing quality or validation outcome |
| `CliExitCode.INPUT_ERROR` | `2` | Invocation or configuration is invalid |
| `CliExitCode.INFRASTRUCTURE_ERROR` | `3` | Infrastructure prevented a trustworthy result |

The operating-system interface remains unchanged.

---

## Failure Behavior

If a future change introduces:

```python
return 1
```

inside `src/cli`, the contract test records:

- the file,
- the line number,
- the offending source line.

The assertion then fails with a diagnostic similar to:

```text
CLI process exit codes must use CliExitCode:
src/cli/example.py:42: return 1
```

This makes the failure actionable during local development and CI.

---

## Relationship to Existing Exit-Code Tests

Sprint 11.81 protects the numeric mapping:

```text
semantic name → stable integer
```

Sprint 11.83 protects usage:

```text
CLI process decision → semantic name
```

Together:

```text
CLI outcome
    ↓
CliExitCode
    ↓
stable numeric value
```

Both ends of the contract are now protected.

---

## Compatibility

Sprint 11.83 is backward-compatible.

It does not change:

- CLI arguments,
- numeric exit values,
- stdout behavior,
- stderr behavior,
- dataset behavior,
- evaluation behavior,
- regression behavior,
- quality-gate policy,
- diagnostics,
- report schemas,
- artifact schemas,
- provenance,
- evaluation profiles,
- shell integration,
- CI/CD integration.

For external consumers:

```text
before: 0 / 1 / 2 / 3
after:  0 / 1 / 2 / 3
```

There is no observable process-contract change.

---

## Scope Guard

Sprint 11.83 intentionally does not introduce:

- new exit-code categories,
- new CLI commands,
- new runtime branches,
- new exception classes,
- new logging infrastructure,
- telemetry,
- JSON diagnostics,
- generalized repository linting,
- AST-based static analysis,
- shell-specific exit handling,
- API status mappings,
- regression-policy changes,
- quality-gate changes,
- dataset-validation changes,
- report-format changes.

The sprint has one responsibility:

> Ensure the centralized CLI exit-code contract cannot be bypassed by raw process literals.

---

## Verification

Focused contract test:

```text
1 passed in 0.05s
```

CLI-focused suite:

```text
39 passed in 0.61s
```

Full project suite:

```text
636 passed in 10.51s
```

Formatting verification:

```text
git diff --check
```

Result:

```text
clean
```

The full-suite count increased from `635` to `636` because Sprint 11.83 adds one new contract test.

---

## Acceptance Criteria

- [x] A dedicated CLI exit-code usage contract test exists.
- [x] The test scans the CLI source tree.
- [x] Raw `return 0` is rejected.
- [x] Raw `return 1` is rejected.
- [x] Raw `return 2` is rejected.
- [x] Raw `return 3` is rejected.
- [x] Direct `SystemExit(0)` is rejected.
- [x] Direct `SystemExit(1)` is rejected.
- [x] Direct `SystemExit(2)` is rejected.
- [x] Direct `SystemExit(3)` is rejected.
- [x] Violations include file and line information.
- [x] No new runtime dependencies are introduced.
- [x] Existing numeric exit-code semantics remain unchanged.
- [x] CLI-focused tests pass.
- [x] Full project regression suite passes.
- [x] `git diff --check` passes.
- [x] No unrelated runtime behavior changes are introduced.

---

## Result

Sprint 11.83 turns the CLI exit-code architecture into an enforced invariant.

Before:

```text
documented rule
      +
central enum
      +
developer discipline
```

After:

```text
documented rule
      +
central enum
      +
automated contract test
      ↓
CI enforcement
```

The process boundary now has three durable protections:

```text
semantic vocabulary
        ↓
stable integer mapping
        ↓
usage enforcement
```

---

## Final Sprint Summary

Sprint 11.83 completes the enforcement phase of the CLI exit-code work.

The sprint:

- adds `tests/test_exit_code_contract.py`,
- converts the previous manual literal scan into an automated pytest invariant,
- prevents direct `return 0 / 1 / 2 / 3` process semantics from returning to the CLI,
- prevents direct `SystemExit(0 / 1 / 2 / 3)` usage,
- preserves the existing `0 / 1 / 2 / 3` external interface,
- preserves all CLI runtime behavior,
- adds no dependencies,
- increases the full regression suite from `635` to `636` tests.

Verification:

```text
Contract test:    1 passed
CLI suite:        39 passed
Full suite:       636 passed
git diff --check: clean
```

With Sprint 11.83 complete, AI Test Lab's CLI exit-code contract is no longer only centralized and consistently used; it is also permanently enforced by the test suite.
