# Sprint 11.85 — Real CLI Process Contract Verification

## Status

**Completed**

## Summary

Sprint 11.85 verifies that AI Test Lab's **actual CLI executable path** exposes the expected process behavior to external callers.

The previous CLI exit-code hardening sequence established and protected the semantic process-status contract:

```text
Sprint 11.81 → Define the exit-code vocabulary
Sprint 11.82 → Complete CLI adoption
Sprint 11.83 → Enforce semantic exit-code usage
Sprint 11.84 → Verify the Python process boundary
```

Sprint 11.85 extends that protection one layer further.

Instead of directly raising `SystemExit(CliExitCode(...))` inside a child interpreter, the new tests execute the real CLI entry point:

```text
python -m src.cli.app
```

and verify that real CLI scenarios cross the complete application and operating-system boundary correctly.

The verified path is now:

```text
real CLI invocation
        ↓
argument parser
        ↓
application behavior
        ↓
semantic outcome
        ↓
CliExitCode
        ↓
SystemExit
        ↓
Python process termination
        ↓
OS-visible exit status
```

Sprint 11.85 verifies two deterministic executable scenarios:

```text
successful CLI operation → SUCCESS → 0

invalid CLI invocation → INPUT_ERROR → 2
```

The invalid invocation is additionally verified to:

```text
write its diagnostic to stderr
write no normal output to stdout
```

No production CLI behavior changes.

No public command-line interface changes.

No exit-code values change.

No runtime dependencies are added.

---

## Objective

Verify that representative AI Test Lab CLI commands expose the established process contract through the **real executable entry point**, not only through isolated unit or synthetic process-boundary tests.

The primary invariant is:

```text
real CLI command
    ↓
real application execution
    ↓
correct semantic classification
    ↓
correct OS-visible process result
```

For the deterministic scenarios selected for this sprint:

```text
--list-evaluation-profiles
        ↓
SUCCESS
        ↓
0

incomplete regression invocation
        ↓
INPUT_ERROR
        ↓
2
```

The invalid-input scenario must also preserve the CLI diagnostic channel contract:

```text
normal output       → stdout
invocation error    → stderr
```

---

## Background

The CLI exit-code architecture was hardened incrementally across several focused sprints.

### Sprint 11.81 — Exit-Code Vocabulary

Sprint 11.81 centralized CLI process outcomes using:

```python
class CliExitCode(IntEnum):
    SUCCESS = 0
    FAILURE = 1
    INPUT_ERROR = 2
    INFRASTRUCTURE_ERROR = 3
```

This replaced unexplained process-status literals with explicit semantic values.

---

### Sprint 11.82 — Exit-Code Adoption

Sprint 11.82 completed adoption of `CliExitCode` across remaining CLI return paths.

The CLI process contract became explicit throughout application-level execution.

---

### Sprint 11.83 — Source-Level Enforcement

Sprint 11.83 introduced an automated contract test preventing raw process-exit literals from being reintroduced into CLI implementation code.

The resulting invariant became:

```text
CLI process decision
        ↓
CliExitCode
        ↓
stable integer mapping
```

---

### Sprint 11.84 — Python Process Boundary Verification

Sprint 11.84 verified that all four supported `CliExitCode` values survive:

```text
CliExitCode
    ↓
SystemExit
    ↓
real child Python interpreter
    ↓
OS-visible process status
```

The process-boundary test verified:

| Semantic outcome | Exit code |
|---|---:|
| `SUCCESS` | `0` |
| `FAILURE` | `1` |
| `INPUT_ERROR` | `2` |
| `INFRASTRUCTURE_ERROR` | `3` |

However, those tests intentionally used a small Python `-c` expression that directly raised `SystemExit`.

That correctly verified Python's process boundary, but it did not execute the actual AI Test Lab CLI application.

Sprint 11.85 closes that remaining gap.

---

## Why Sprint 11.85 Is Different

Sprint 11.84 answered:

> If AI Test Lab selects a `CliExitCode`, will Python expose that value correctly to the operating system?

Sprint 11.85 answers:

> Does the real AI Test Lab CLI select and expose the correct process result when invoked as an actual command?

The difference is significant.

### Sprint 11.84

```text
child Python interpreter
        ↓
CliExitCode
        ↓
SystemExit
        ↓
OS status
```

### Sprint 11.85

```text
child Python interpreter
        ↓
python -m src.cli.app
        ↓
argument parsing
        ↓
CLI application logic
        ↓
CliExitCode
        ↓
SystemExit
        ↓
OS status
```

Sprint 11.85 therefore validates the executable integration boundary rather than only the process mechanism.

---

## Implementation

### Added Test File

```text
tests/cli/test_cli_process_contract.py
```

The file contains two focused subprocess tests.

---

## Successful Real CLI Invocation

The first test executes:

```text
python -m src.cli.app --list-evaluation-profiles
```

using the active interpreter through:

```python
sys.executable
```

The test verifies:

```python
completed.returncode == CliExitCode.SUCCESS
```

The complete runtime path is:

```text
sys.executable
        ↓
-m src.cli.app
        ↓
--list-evaluation-profiles
        ↓
real CLI parser
        ↓
profile listing behavior
        ↓
SUCCESS
        ↓
SystemExit
        ↓
process status 0
```

This is a deterministic success path because it does not require:

- Ollama,
- model execution,
- network access,
- datasets,
- external storage,
- regression artifacts.

---

## Invalid Real CLI Invocation

The second test executes an intentionally incomplete regression invocation:

```text
python -m src.cli.app
    --regression-result-output
    results/regression.json
```

Regression mode requires all three regression arguments to be supplied together:

```text
--regression-baseline-report
--regression-baseline-provenance
--regression-result-output
```

Providing only the result-output argument is therefore an invalid invocation.

The real argument parser rejects the command and returns:

```text
INPUT_ERROR → 2
```

The test verifies:

```python
completed.returncode == CliExitCode.INPUT_ERROR
```

This proves that parser-level invocation failure survives the entire executable process path.

---

## Diagnostic Stream Verification

Sprint 11.85 does not stop at checking the numeric process status.

The invalid-invocation test also verifies the CLI's external diagnostic-channel behavior.

The expected parser diagnostic includes:

```text
--regression-baseline-report, --regression-baseline-provenance,
and --regression-result-output must be supplied together
```

The test verifies that the message appears in:

```text
stderr
```

and that:

```text
stdout == ""
```

The executable contract therefore includes both:

```text
semantic process result
```

and:

```text
diagnostic stream placement
```

The verified behavior is:

```text
invalid invocation
        ↓
INPUT_ERROR
        ↓
process status 2

diagnostic
        ↓
stderr

normal stdout
        ↓
empty
```

---

## Why `sys.executable` Is Required

The subprocess tests use:

```python
sys.executable
```

rather than a hard-coded command such as:

```text
python
python3
py
```

This ensures that the child process executes with the same Python interpreter used by the active test environment.

In the current Windows development environment, that means the subprocess uses the project virtual environment interpreter.

This avoids platform-specific assumptions and improves CI portability.

---

## Why the Sprint Verifies Only Two Executable Scenarios

The CLI process vocabulary contains four semantic outcomes:

```text
SUCCESS
FAILURE
INPUT_ERROR
INFRASTRUCTURE_ERROR
```

Sprint 11.85 intentionally does **not** manufacture real subprocess scenarios for every category.

Existing test layers already verify:

```text
FAILURE
INFRASTRUCTURE_ERROR
```

at the application level, and Sprint 11.84 proves that all four `CliExitCode` values cross the Python process boundary correctly.

Artificially forcing regression or infrastructure failures through the full executable path would introduce unnecessary complexity, brittle fixtures, or test-only production hooks.

The layered architecture already provides the required guarantees:

```text
application-level tests
        ↓
verify semantic classification

Sprint 11.84
        ↓
verify every exit value crosses Python process boundary

Sprint 11.85
        ↓
verify representative real CLI executable paths
```

This preserves a narrow sprint scope while maintaining strong coverage.

---

## Layered CLI Process Contract

After Sprint 11.85, the CLI process contract is protected at five complementary levels.

### 1. Semantic Vocabulary

```text
src/cli/exit_codes.py
```

Defines:

```text
SUCCESS
FAILURE
INPUT_ERROR
INFRASTRUCTURE_ERROR
```

---

### 2. Stable Numeric Mapping

```text
tests/cli/test_exit_codes.py
```

Protects:

```text
semantic value
        ↓
stable process integer
```

---

### 3. Source-Level Usage Enforcement

```text
tests/test_exit_code_contract.py
```

Protects:

```text
CLI process decision
        ↓
CliExitCode
```

and prevents unexplained raw process-exit literals from returning to CLI implementation code.

---

### 4. Generic Python Process Boundary

```text
tests/cli/test_exit_code_boundary.py
```

Protects:

```text
CliExitCode
        ↓
SystemExit
        ↓
child Python process
        ↓
OS-visible process status
```

for all four supported values.

---

### 5. Real CLI Executable Boundary

```text
tests/cli/test_cli_process_contract.py
```

Protects:

```text
real CLI invocation
        ↓
parser / application behavior
        ↓
CliExitCode
        ↓
SystemExit
        ↓
OS-visible status
```

and verifies representative diagnostic stream behavior.

---

## Complete Contract Architecture

The CLI process path is now protected as:

```text
CLI command
    ↓
argument parsing
    ↓
application behavior
    ↓
semantic classification
    ↓
CliExitCode
    ↓
stable numeric mapping
    ↓
source-level enforcement
    ↓
SystemExit
    ↓
Python process termination
    ↓
OS-visible process status
```

For invocation failures, Sprint 11.85 additionally protects:

```text
diagnostic classification
        ↓
stderr
```

This is the interface consumed by:

- shell scripts,
- CI/CD pipelines,
- test runners,
- automation systems,
- parent processes,
- build tooling,
- deployment orchestration.

---

## Manual Verification

### Successful Invocation

Command:

```powershell
python -m src.cli.app --list-evaluation-profiles
$LASTEXITCODE
```

Observed output:

```text
Available evaluation profiles:
  deep-quality
  default
  enterprise
  fast-ci
  rag
```

Observed PowerShell process status:

```text
0
```

This verifies:

```text
real successful CLI invocation
        ↓
SUCCESS
        ↓
OS process status 0
```

---

### Invalid Regression Invocation

Command:

```powershell
python -m src.cli.app --regression-result-output .\results\regression.json
$LASTEXITCODE
```

Observed parser diagnostic:

```text
ai-test-lab: error: --regression-baseline-report,
--regression-baseline-provenance,
and --regression-result-output must be supplied together
```

Observed PowerShell process status:

```text
2
```

This verifies:

```text
real invalid CLI invocation
        ↓
INPUT_ERROR
        ↓
OS process status 2
```

---

## Test Verification

### Sprint 11.85 Focused Tests

Command:

```powershell
pytest .\tests\cli\test_cli_process_contract.py -v
```

Result:

```text
2 passed in 2.27s
```

Verified cases:

```text
real CLI success       → 0
real CLI input error   → 2
```

The invalid-invocation test also verifies:

```text
diagnostic → stderr
stdout     → empty
```

---

## CLI-Focused Regression Suite

Command:

```powershell
pytest .\tests\cli .\tests\test_exit_code_contract.py -v
```

Result:

```text
46 passed in 3.31s
```

This suite includes:

- CLI argument parsing,
- evaluation-profile behavior,
- regression argument validation,
- diagnostics,
- exit-code definitions,
- generic process-boundary verification,
- real executable process-contract verification,
- regression execution behavior,
- regression result output,
- source-level exit-code enforcement.

The previous Sprint 11.84 CLI-focused baseline was:

```text
44 passed
```

Sprint 11.85 adds:

```text
2 tests
```

resulting in:

```text
44 + 2 = 46
```

---

## Full Project Regression Suite

Command:

```powershell
pytest -q
```

Result:

```text
642 passed in 12.63s
```

The previous full-suite baseline after Sprint 11.84 was:

```text
640 passed
```

Sprint 11.85 adds exactly two tests:

```text
640 + 2 = 642
```

No regressions were detected.

---

## Diff Validation

Command:

```powershell
git diff --check
```

Result:

```text
clean
```

No whitespace errors were reported.

---

## Scope Guard

Sprint 11.85 intentionally does **not** introduce:

- new CLI commands,
- new CLI options,
- new exit-code categories,
- changes to exit-code numeric values,
- changes to `CliExitCode`,
- changes to regression policy,
- changes to quality-gate behavior,
- changes to evaluation behavior,
- changes to model execution,
- changes to dataset behavior,
- new exception types,
- new logging infrastructure,
- new diagnostic architecture,
- new report schemas,
- new regression schemas,
- new provenance schemas,
- network dependencies,
- Ollama dependencies,
- external services,
- synthetic production failure hooks,
- generalized subprocess infrastructure.

The sprint has one responsibility:

> Verify representative AI Test Lab commands through the real executable CLI process boundary.

---

## Compatibility

Sprint 11.85 is backward-compatible.

It does not change:

- CLI syntax,
- CLI options,
- supported process-status values,
- profile behavior,
- dataset execution,
- model execution,
- evaluation execution,
- regression execution,
- quality gates,
- report generation,
- provenance handling,
- regression artifacts,
- external schemas,
- public interfaces.

External callers continue to observe the established process contract:

| Outcome | Process status |
|---|---:|
| Success | `0` |
| Evaluation/regression failure | `1` |
| Invalid invocation/input | `2` |
| Infrastructure failure | `3` |

Sprint 11.85 adds verification only.

---

## Design Principles

### Test the Interface External Automation Actually Uses

CI/CD systems do not call internal Python functions.

They execute commands and inspect:

```text
process status
stdout
stderr
```

Sprint 11.85 therefore verifies the real executable boundary.

---

### Keep Process Tests Deterministic

The selected executable scenarios require no:

- LLM,
- Ollama server,
- network service,
- mutable infrastructure,
- model download,
- dataset fixture,
- external API.

This keeps the tests fast and reliable.

---

### Avoid Duplicating Existing Coverage

Sprint 11.85 does not reproduce every application-level failure scenario as a subprocess test.

Each test layer retains a specific responsibility.

This prevents redundant and brittle end-to-end coverage.

---

### Preserve the Public CLI Boundary

No internal implementation details are exposed through the new tests.

The tests interact only with the existing public executable interface:

```text
python -m src.cli.app
```

This keeps the verification aligned with the established AI Test Lab public/private architecture boundary.

---

## Acceptance Criteria

- [x] A dedicated real CLI process-contract test file exists.
- [x] Tests execute the actual `src.cli.app` module.
- [x] Tests launch a real child Python process.
- [x] Tests use `sys.executable`.
- [x] Successful CLI invocation returns `SUCCESS`.
- [x] Successful CLI invocation produces OS status `0`.
- [x] Incomplete regression invocation returns `INPUT_ERROR`.
- [x] Invalid invocation produces OS status `2`.
- [x] Invalid invocation diagnostic is emitted through `stderr`.
- [x] Invalid invocation produces no normal `stdout` output.
- [x] Existing Sprint 11.84 process-boundary tests remain intact.
- [x] Existing exit-code semantic tests remain intact.
- [x] Existing source-level contract enforcement remains intact.
- [x] No production CLI behavior changes.
- [x] No CLI syntax changes.
- [x] No exit-code values change.
- [x] No runtime dependencies are added.
- [x] No Ollama dependency is introduced.
- [x] No network dependency is introduced.
- [x] Focused Sprint 11.85 tests pass.
- [x] CLI-focused regression suite passes.
- [x] Full project regression suite passes.
- [x] Diff validation passes.
- [x] No unrelated functionality is modified.

---

## Result

Sprint 11.85 closes the gap between the generic Python process boundary and the actual AI Test Lab executable interface.

Before Sprint 11.85:

```text
semantic CLI outcome
        ↓
CliExitCode
        ↓
stable numeric mapping
        ↓
source-level enforcement
        ↓
SystemExit
        ↓
verified Python process boundary
```

After Sprint 11.85:

```text
real AI Test Lab command
        ↓
real CLI parser
        ↓
real application behavior
        ↓
semantic CLI outcome
        ↓
CliExitCode
        ↓
SystemExit
        ↓
real child process
        ↓
verified OS-visible status
```

For invalid invocations:

```text
error diagnostic
        ↓
verified stderr channel
```

The CLI process contract is therefore protected from semantic classification all the way through the executable boundary consumed by external automation.

---

## Final Sprint Summary

Sprint 11.85 adds real executable verification to AI Test Lab's CLI process contract.

The sprint:

- adds `tests/cli/test_cli_process_contract.py`,
- executes the actual CLI through `python -m src.cli.app`,
- verifies a real successful command returns process status `0`,
- verifies a real invalid invocation returns process status `2`,
- verifies invalid-invocation diagnostics are emitted through `stderr`,
- verifies invalid invocations produce no normal stdout,
- reuses `sys.executable` for portability,
- preserves the existing four-value `CliExitCode` contract,
- preserves all production CLI behavior,
- adds no runtime dependencies,
- requires no Ollama or network access,
- increases the CLI-focused suite from `44` to `46` passing tests,
- increases the full regression suite from `640` to `642` passing tests.

Final verification:

```text
Sprint 11.85 tests:   2 passed
CLI-focused suite:   46 passed
Full project suite: 642 passed
Diff check:          clean
```

The hardened CLI process-contract sequence is now:

```text
11.81  Define semantic exit codes
  ↓
11.82  Adopt them across CLI paths
  ↓
11.83  Enforce semantic usage
  ↓
11.84  Verify generic Python process boundary
  ↓
11.85  Verify the real CLI executable boundary
```

AI Test Lab can now treat its CLI process behavior as a stable, semantic, enforced, process-tested, and executable-verified automation contract.