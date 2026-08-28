# Sprint 11.84 — CLI Exit-Code Boundary Verification

## Status

**Completed**

## Summary

Sprint 11.84 verifies that AI Test Lab's centralized CLI exit-code contract survives the complete Python process boundary and is exposed to external callers as the correct operating-system process status.

The CLI exit-code hardening sequence now consists of four distinct protections:

```text
Sprint 11.81 → Define the exit-code vocabulary
Sprint 11.82 → Complete CLI adoption
Sprint 11.83 → Enforce semantic exit-code usage
Sprint 11.84 → Verify the external process boundary
```

The authoritative process-level vocabulary remains:

| Semantic outcome | `CliExitCode` | Process status |
|---|---:|---:|
| Success | `SUCCESS` | `0` |
| Evaluation or regression failure | `FAILURE` | `1` |
| Invalid input or invocation | `INPUT_ERROR` | `2` |
| Infrastructure failure | `INFRASTRUCTURE_ERROR` | `3` |

Sprint 11.84 adds focused subprocess verification proving that all four values cross a real Python process boundary correctly.

No production CLI behavior changes.

No exit-code values change.

No public command-line interface changes.

---

## Objective

Verify the complete process-status path:

```text
CLI outcome
    ↓
semantic classification
    ↓
CliExitCode
    ↓
SystemExit
    ↓
Python process termination
    ↓
OS-visible exit status
```

The required invariant is:

```text
SUCCESS              → 0
FAILURE              → 1
INPUT_ERROR           → 2
INFRASTRUCTURE_ERROR  → 3
```

The sprint verifies this behavior at the process boundary rather than merely checking integer constants or direct return values from `main()`.

---

## Background

The previous CLI exit-code sprints hardened different parts of the same contract.

### Sprint 11.81 — Contract Definition

Sprint 11.81 established the centralized semantic vocabulary:

```python
class CliExitCode(IntEnum):
    SUCCESS = 0
    FAILURE = 1
    INPUT_ERROR = 2
    INFRASTRUCTURE_ERROR = 3
```

This made process outcomes explicit and readable instead of relying on unexplained numeric literals.

### Sprint 11.82 — Contract Adoption

Sprint 11.82 completed adoption of `CliExitCode` across remaining CLI process-return paths.

The CLI no longer needed raw process decisions such as:

```python
return 0
return 1
```

for normal process-status handling.

### Sprint 11.83 — Contract Enforcement

Sprint 11.83 added:

```text
tests/test_exit_code_contract.py
```

That test scans the CLI source tree and prevents raw process-status literals from being reintroduced.

The architecture therefore became self-enforcing:

```text
CLI process decision
        ↓
CliExitCode
        ↓
stable integer value
```

However, one layer remained to verify explicitly.

The internal contract could be correct while the external process boundary remained untested.

Sprint 11.84 closes that final verification gap.

---

## Process Boundary

The AI Test Lab CLI terminates through:

```python
if __name__ == "__main__":
    raise SystemExit(main())
```

The effective runtime path is therefore:

```text
main(...)
    ↓
CliExitCode / integer
    ↓
SystemExit(...)
    ↓
Python interpreter terminates
    ↓
parent process or shell receives exit status
```

This boundary matters because shell scripts, CI pipelines, deployment systems, automation tools, and other process supervisors do not inspect Python enums.

They observe the operating-system process status.

Sprint 11.84 verifies that the semantic contract reaches that external boundary intact.

---

## Implementation

### Added Test File

```text
tests/cli/test_exit_code_boundary.py
```

The test launches a real child Python interpreter through `subprocess.run()` and passes each supported `CliExitCode` through `SystemExit`.

```python
from __future__ import annotations

import subprocess
import sys

import pytest

from src.cli.exit_codes import CliExitCode


@pytest.mark.parametrize(
    ("exit_code", "expected"),
    [
        (CliExitCode.SUCCESS, 0),
        (CliExitCode.FAILURE, 1),
        (CliExitCode.INPUT_ERROR, 2),
        (CliExitCode.INFRASTRUCTURE_ERROR, 3),
    ],
)
def test_cli_exit_codes_cross_python_process_boundary(
    exit_code: CliExitCode,
    expected: int,
) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from src.cli.exit_codes import CliExitCode; "
                f"raise SystemExit(CliExitCode({int(exit_code)}))"
            ),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == expected
```

The implementation intentionally uses:

```python
sys.executable
```

instead of assuming a platform-specific `python` executable name.

This ensures that the child process uses the same Python interpreter as the active test environment.

---

## Why a Subprocess Test Is Necessary

A unit test such as:

```python
assert CliExitCode.SUCCESS == 0
```

verifies the enum contract.

A test such as:

```python
assert main(...) == 0
```

verifies application return behavior.

Neither independently verifies the operating-system process boundary.

Sprint 11.84 verifies:

```text
CliExitCode
    ↓
SystemExit
    ↓
real child Python process
    ↓
subprocess.returncode
```

That is the interface observed by external automation.

---

## Verified Boundary Matrix

Sprint 11.84 verifies all supported process outcomes:

| Semantic value | Expected OS status | Verified |
|---|---:|---|
| `CliExitCode.SUCCESS` | `0` | Yes |
| `CliExitCode.FAILURE` | `1` | Yes |
| `CliExitCode.INPUT_ERROR` | `2` | Yes |
| `CliExitCode.INFRASTRUCTURE_ERROR` | `3` | Yes |

The process-status contract is therefore complete across the supported vocabulary.

---

## Manual Shell Verification

In addition to the automated subprocess test, representative real CLI invocations were verified from PowerShell.

### Successful CLI Execution

Command:

```powershell
python -m src.cli.app --list-evaluation-profiles
$LASTEXITCODE
```

The CLI successfully listed the available profiles:

```text
deep-quality
default
enterprise
fast-ci
rag
```

PowerShell observed:

```text
0
```

This confirms:

```text
successful CLI execution
        ↓
SUCCESS
        ↓
process status 0
```

### Invalid CLI Invocation

Command:

```powershell
python -m src.cli.app --regression-result-output .\results\regression.json
$LASTEXITCODE
```

The argument parser rejected the incomplete regression argument set because the regression baseline report, baseline provenance, and result-output arguments must be supplied together.

PowerShell observed:

```text
2
```

This confirms that parser-level invalid invocation semantics also reach the shell correctly.

---

## Existing Runtime Coverage

Sprint 11.84 does not recreate the larger regression execution scenarios already covered elsewhere.

Existing CLI tests already verify application-level decisions including:

```text
successful execution
regression block
invalid regression invocation
artifact failure
regression execution failure
```

Those tests establish that application logic selects the appropriate exit-code category.

Sprint 11.84 adds the missing independent guarantee that those categories can cross the process boundary correctly.

This separation keeps the architecture clean:

```text
application tests
    ↓
verify which exit code should be selected

boundary tests
    ↓
verify the selected exit code reaches the OS intact
```

---

## Layered CLI Exit-Code Protection

The CLI exit-code contract is now protected at four complementary layers.

### 1. Vocabulary

```text
src/cli/exit_codes.py
```

Defines the supported semantic outcomes.

```text
SUCCESS
FAILURE
INPUT_ERROR
INFRASTRUCTURE_ERROR
```

### 2. Numeric Mapping

```text
tests/cli/test_exit_codes.py
```

Protects:

```text
semantic value → stable integer
```

### 3. Usage Enforcement

```text
tests/test_exit_code_contract.py
```

Protects:

```text
CLI process decision → CliExitCode
```

and prevents raw numeric process exits from returning to the CLI implementation.

### 4. Process Boundary

```text
tests/cli/test_exit_code_boundary.py
```

Protects:

```text
CliExitCode
    ↓
SystemExit
    ↓
Python process
    ↓
OS-visible status
```

Together:

```text
CLI outcome
    ↓
semantic classification
    ↓
CliExitCode
    ↓
stable integer mapping
    ↓
enforced usage
    ↓
SystemExit
    ↓
verified process status
```

---

## Design Principles

### Verify Contracts at Their Consumer Boundary

The consumer of a process exit code is not the Python function returning it.

The consumer is the shell, CI runner, parent process, or automation system observing the terminated process.

Therefore the contract must be tested at that boundary.

### Keep Boundary Tests Deterministic

The process-boundary test does not invoke:

- Ollama,
- external models,
- network services,
- datasets,
- regression artifacts,
- external storage,
- real infrastructure failures.

The test verifies only the process-status mechanism.

This keeps the test fast, deterministic, portable, and suitable for CI.

### Reuse Existing Semantics

Sprint 11.84 introduces no new classification policy.

It verifies the contract already established by previous sprints.

---

## Scope Guard

Sprint 11.84 intentionally does **not** introduce:

- new exit-code categories,
- new CLI commands,
- new CLI arguments,
- changes to `CliExitCode`,
- changes to regression policy,
- changes to quality-gate policy,
- new exception classes,
- new diagnostics,
- new logging infrastructure,
- shell-specific production logic,
- new dataset behavior,
- new report schemas,
- new artifact schemas,
- new model execution behavior,
- a generalized subprocess testing framework,
- Ollama dependencies,
- network dependencies.

The sprint has one responsibility:

> Verify that the established semantic CLI exit-code contract survives the Python process boundary intact.

---

## Compatibility

Sprint 11.84 is backward-compatible.

It does not change:

- CLI command syntax,
- supported exit-code values,
- stdout behavior,
- stderr behavior,
- dataset execution,
- evaluation execution,
- regression execution,
- regression enforcement,
- quality gates,
- report generation,
- artifact formats,
- provenance,
- evaluation profiles,
- model-provider behavior,
- CI/CD integration.

External callers continue to observe:

```text
0 / 1 / 2 / 3
```

with the same meanings as before.

---

## Verification

### Focused Boundary Test

```text
4 passed in 0.57s
```

The four parametrized cases verify:

```text
0 → process status 0
1 → process status 1
2 → process status 2
3 → process status 3
```

### CLI-Focused Regression Suite

Command:

```powershell
pytest .\tests\cli .\tests\test_exit_code_contract.py -v
```

Result:

```text
44 passed in 1.04s
```

This includes:

- argument parsing,
- evaluation-profile CLI behavior,
- diagnostics,
- exit-code definitions,
- process-boundary verification,
- regression execution,
- regression result output,
- source-level exit-code enforcement.

### Full Project Regression Suite

Command:

```powershell
pytest -q
```

Result:

```text
640 passed in 11.21s
```

The previous full-suite baseline was:

```text
636 passed
```

Sprint 11.84 adds four parametrized boundary cases:

```text
636 + 4 = 640
```

### Diff Validation

Command:

```powershell
git diff --cached --check
```

Result:

```text
clean
```

A Windows LF-to-CRLF conversion notice was emitted while staging the test file, but no whitespace errors were reported.

---

## Acceptance Criteria

- [x] A dedicated CLI process-boundary test exists.
- [x] The boundary test launches a real child Python process.
- [x] The active Python interpreter is selected through `sys.executable`.
- [x] `CliExitCode.SUCCESS` produces process status `0`.
- [x] `CliExitCode.FAILURE` produces process status `1`.
- [x] `CliExitCode.INPUT_ERROR` produces process status `2`.
- [x] `CliExitCode.INFRASTRUCTURE_ERROR` produces process status `3`.
- [x] The test validates `subprocess.returncode`.
- [x] Real PowerShell success execution returns `0`.
- [x] Real PowerShell invalid invocation returns `2`.
- [x] Existing application-level exit-code tests remain green.
- [x] Existing source-level exit-code enforcement remains green.
- [x] No production CLI behavior changes.
- [x] No runtime dependencies added.
- [x] No Ollama dependency introduced.
- [x] No network dependency introduced.
- [x] CLI-focused regression suite passes.
- [x] Full project regression suite passes.
- [x] Cached diff validation passes.
- [x] No unrelated functionality is modified.

---

## Result

Sprint 11.84 completes the current CLI exit-code hardening sequence.

Before Sprint 11.84:

```text
semantic vocabulary
        ↓
stable mapping
        ↓
consistent usage
        ↓
automated source enforcement
```

After Sprint 11.84:

```text
semantic vocabulary
        ↓
stable mapping
        ↓
consistent usage
        ↓
automated source enforcement
        ↓
SystemExit boundary
        ↓
verified OS-visible process status
```

The CLI's exit-code architecture is now protected from internal semantic classification through the process interface consumed by external automation.

---

## Final Sprint Summary

Sprint 11.84 verifies the external boundary of AI Test Lab's CLI exit-code contract.

The sprint:

- adds `tests/cli/test_exit_code_boundary.py`,
- verifies all four supported exit codes through real child Python processes,
- confirms `SystemExit` preserves the `0 / 1 / 2 / 3` contract,
- supplements existing application-level exit-code coverage,
- preserves all production CLI behavior,
- introduces no runtime dependencies,
- requires no Ollama or network access,
- confirms representative shell-level behavior manually,
- increases the full regression suite from `636` to `640` passing tests.

Final verification:

```text
Boundary tests:       4 passed
CLI-focused suite:    44 passed
Full project suite:   640 passed
Cached diff check:    clean
```

The completed hardening sequence is:

```text
11.81  Define
  ↓
11.82  Adopt
  ↓
11.83  Enforce
  ↓
11.84  Verify the process boundary
```

AI Test Lab can now treat CLI process status as a stable, explicitly classified, automatically enforced, and externally verified automation contract.