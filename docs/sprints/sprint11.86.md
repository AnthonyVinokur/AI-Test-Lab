# Sprint 11.86 — CLI Output-Channel Contract Verification

## Status

**Completed**

---

## Summary

Sprint 11.86 strengthens AI Test Lab's command-line interface contract by verifying not only **which process exit code** a real CLI invocation returns, but also **which output stream external callers receive information on**.

The preceding CLI hardening sequence established a layered process contract:

```text
Sprint 11.81 → Define the semantic exit-code vocabulary
Sprint 11.82 → Complete CLI exit-code adoption
Sprint 11.83 → Enforce semantic exit-code usage
Sprint 11.84 → Verify the Python process boundary
Sprint 11.85 → Verify the real CLI executable boundary
Sprint 11.86 → Verify stdout / stderr channel behavior
```

Sprint 11.85 already executed the real application entry point:

```text
python -m src.cli.app
```

and proved that representative CLI scenarios expose the correct operating-system-visible process status.

Sprint 11.86 extends that contract by protecting another part of the interface consumed by:

- CI/CD pipelines,
- shell scripts,
- test automation,
- parent processes,
- build systems,
- deployment tooling,
- developer scripts.

That interface consists of three externally observable values:

```text
process exit status
stdout
stderr
```

Sprint 11.86 verifies the following invariant:

```text
successful informational command
        ↓
SUCCESS
        ↓
exit status 0
        ↓
normal output on stdout
        ↓
stderr empty
```

and preserves the previously verified invalid-input behavior:

```text
invalid CLI invocation
        ↓
INPUT_ERROR
        ↓
exit status 2
        ↓
stdout empty
        ↓
diagnostic on stderr
```

No production CLI behavior changes.

No CLI syntax changes.

No exit-code values change.

No report, regression, evaluation, or model behavior changes.

The sprint strengthens automated verification of the existing public process interface.

---

## Objective

Protect the CLI output-channel contract exposed by the real AI Test Lab executable entry point.

The primary requirement is:

```text
normal successful output → stdout
diagnostics/errors        → stderr
```

while preserving the semantic process-status contract:

```text
successful command   → SUCCESS     → 0
invalid invocation   → INPUT_ERROR → 2
```

The complete externally observable contract becomes:

```text
CLI invocation
      ↓
argument parsing
      ↓
application behavior
      ↓
semantic outcome
      ↓
CliExitCode
      ↓
SystemExit
      ↓
OS-visible exit status
      +
stdout
      +
stderr
```

---

## Background

AI Test Lab's CLI process boundary has been hardened incrementally rather than through one large architectural change.

This keeps each sprint narrow, independently testable, and easy to review.

### Sprint 11.81 — Semantic Exit-Code Vocabulary

Sprint 11.81 centralized CLI process outcomes using:

```python
class CliExitCode(IntEnum):
    SUCCESS = 0
    FAILURE = 1
    INPUT_ERROR = 2
    INFRASTRUCTURE_ERROR = 3
```

This replaced unexplained process-status literals with named semantic outcomes.

The contract became:

```text
application outcome
        ↓
semantic exit category
        ↓
stable process integer
```

---

### Sprint 11.82 — Exit-Code Contract Completion

Sprint 11.82 completed adoption of `CliExitCode` across the CLI's remaining application-level return paths.

The semantic process vocabulary became consistently used by the command-line layer.

---

### Sprint 11.83 — Exit-Code Contract Enforcement

Sprint 11.83 introduced automated protection preventing raw process-exit literals from being reintroduced into CLI implementation code.

The resulting invariant became:

```text
CLI process decision
        ↓
CliExitCode
```

rather than:

```text
CLI process decision
        ↓
unexplained integer literal
```

---

### Sprint 11.84 — Python Process-Boundary Verification

Sprint 11.84 verified that all supported semantic exit values survive the real Python process boundary:

```text
CliExitCode
      ↓
SystemExit
      ↓
child Python interpreter
      ↓
operating-system-visible status
```

The four protected mappings are:

| Semantic outcome | Process status |
|---|---:|
| `SUCCESS` | `0` |
| `FAILURE` | `1` |
| `INPUT_ERROR` | `2` |
| `INFRASTRUCTURE_ERROR` | `3` |

---

### Sprint 11.85 — Real CLI Process Contract Verification

Sprint 11.85 moved one integration layer outward.

Instead of testing only:

```text
CliExitCode → SystemExit → OS
```

it executed the actual AI Test Lab command:

```text
python -m src.cli.app
```

This verified representative executable scenarios through the complete path:

```text
real command
      ↓
argument parser
      ↓
CLI application
      ↓
semantic outcome
      ↓
CliExitCode
      ↓
SystemExit
      ↓
operating-system process result
```

Sprint 11.85 verified:

```text
successful profile listing → SUCCESS     → 0
invalid regression input   → INPUT_ERROR → 2
```

It also verified that the invalid invocation placed its diagnostic on `stderr` rather than `stdout`.

---

## Why Sprint 11.86 Is Needed

A command-line program's external contract is larger than its process status.

Automation commonly interacts with three channels:

```text
return code
stdout
stderr
```

A caller may use them independently.

For example:

```powershell
python -m src.cli.app --list-evaluation-profiles
```

A CI job or wrapper script may expect:

```text
return code = 0

stdout:
Available evaluation profiles:
  ...

stderr:
<empty>
```

Likewise, an invalid invocation may be expected to produce:

```text
return code = 2

stdout:
<empty>

stderr:
diagnostic explaining the invalid command
```

If normal output accidentally moved to `stderr`, or an error message leaked into `stdout`, scripts consuming the CLI could break even though the numeric exit code remained correct.

Sprint 11.86 therefore protects the **channel semantics** of the executable interface.

---

## External CLI Contract

After Sprint 11.86, representative CLI behavior is protected as follows.

### Successful informational invocation

```text
python -m src.cli.app --list-evaluation-profiles
```

Expected external behavior:

```text
exit status = 0
stdout      = normal profile-listing output
stderr      = empty
```

Semantic mapping:

```text
valid command
      ↓
successful operation
      ↓
CliExitCode.SUCCESS
      ↓
0
```

Channel mapping:

```text
normal information
      ↓
stdout
```

---

### Invalid regression invocation

An intentionally incomplete regression command is executed with:

```text
--regression-result-output results/regression.json
```

without the other required regression arguments.

The regression CLI contract requires these arguments to be supplied together:

```text
--regression-baseline-report
--regression-baseline-provenance
--regression-result-output
```

The expected external behavior is:

```text
exit status = 2
stdout      = empty
stderr      = invocation diagnostic
```

Semantic mapping:

```text
invalid invocation
      ↓
CliExitCode.INPUT_ERROR
      ↓
2
```

Channel mapping:

```text
diagnostic
      ↓
stderr
```

---

## Implementation

Sprint 11.86 strengthens:

```text
tests/cli/test_cli_process_contract.py
```

No production file is required to change.

The existing successful real-CLI test already verified:

```python
completed.returncode == CliExitCode.SUCCESS
```

Sprint 11.86 adds assertions protecting successful output placement:

```python
assert "Available evaluation profiles:" in completed.stdout
assert "default" in completed.stdout
assert completed.stderr == ""
```

The successful executable contract therefore becomes:

```text
real CLI invocation
      ↓
successful profile listing
      ↓
SUCCESS
      ↓
process status 0
      +
expected informational content on stdout
      +
no stderr output
```

---

## Why the Test Does Not Assert the Entire Profile Listing

Sprint 11.86 intentionally avoids comparing `stdout` against one exact multiline string.

For example, the test does **not** require:

```text
Available evaluation profiles:
  deep-quality
  default
  enterprise
  fast-ci
  rag
```

to remain byte-for-byte identical forever.

Instead, it verifies stable semantic markers:

```python
"Available evaluation profiles:" in completed.stdout
"default" in completed.stdout
```

This distinction matters.

The contract being protected is:

```text
successful information belongs on stdout
```

not:

```text
the profile catalog must never evolve
```

Future legitimate profile additions should therefore not break this process-boundary test unnecessarily.

This reduces brittle coupling while still protecting the external CLI interface.

---

## Output-Channel Invariants

Sprint 11.86 establishes two complementary channel invariants.

### Success invariant

```text
successful informational operation
        ↓
stdout contains expected information
stderr is empty
```

### Input-error invariant

```text
invalid invocation
        ↓
stdout is empty
stderr contains diagnostic
```

Together:

```text
                         ┌───────────────┐
                         │ CLI invocation│
                         └───────┬───────┘
                                 ↓
                         semantic outcome
                                 ↓
                   ┌─────────────┴─────────────┐
                   ↓                           ↓
                SUCCESS                    INPUT_ERROR
                   ↓                           ↓
                   0                           2
                   ↓                           ↓
          information → stdout       diagnostic → stderr
          stderr      → empty        stdout     → empty
```

---

## Why stdout and stderr Matter

Exit codes answer:

> Did the command succeed, fail, receive invalid input, or encounter infrastructure trouble?

Output channels answer a different question:

> What kind of information did the command emit?

These contracts are complementary.

### `stdout`

Standard output is appropriate for normal command output that another process may consume.

Examples include:

- profile listings,
- generated command results,
- machine-readable data,
- normal informational output.

### `stderr`

Standard error is appropriate for diagnostics that explain why normal execution could not proceed.

Examples include:

- invalid command usage,
- malformed arguments,
- missing required related arguments,
- infrastructure diagnostics,
- runtime failure diagnostics.

Keeping these channels distinct improves:

- shell composition,
- CI/CD integration,
- redirect behavior,
- log processing,
- machine parsing,
- diagnostic clarity.

---

## Why This Is an Automation Contract

A human using a terminal may visually see both streams together.

Automation does not necessarily treat them that way.

A script can independently capture:

```python
completed.stdout
completed.stderr
completed.returncode
```

Shell environments can also redirect them separately.

For example:

```text
stdout → artifact or parser
stderr → diagnostic log
```

A stable output-channel contract therefore reduces ambiguity for systems integrating with AI Test Lab.

---

## Test Verification

### Focused Sprint 11.86 Verification

Command:

```powershell
pytest .\tests\cli\test_cli_process_contract.py -v
```

Result:

```text
2 passed in 2.38s
```

The focused executable contract verifies:

```text
real CLI success
    → SUCCESS
    → status 0
    → expected stdout
    → empty stderr

real CLI invalid input
    → INPUT_ERROR
    → status 2
    → empty stdout
    → diagnostic stderr
```

---

## Full Project Regression Suite

Command:

```powershell
pytest -q
```

Result:

```text
642 passed in 8.58s
```

The full project regression suite remains green.

The Sprint 11.85 full-suite baseline was:

```text
642 passed
```

Sprint 11.86 introduces no additional test cases.

Instead, it strengthens assertions in an existing executable process-contract test.

Therefore:

```text
Sprint 11.85 baseline = 642
Sprint 11.86 result   = 642
```

This is intentional.

The sprint increases **contract strength**, not test-count volume.

No regressions were detected.

---

## Test-Count Philosophy

A higher test count is not automatically stronger verification.

Sprint 11.86 demonstrates this directly.

Before:

```text
successful process test
        ↓
verify exit status
```

After:

```text
successful process test
        ↓
verify exit status
        +
verify stdout semantics
        +
verify stderr isolation
```

The number of tests remains unchanged:

```text
2 process-contract tests
```

but the observable behavior protected by those tests increases.

This keeps the suite focused and avoids artificial test inflation.

---

## Complete CLI Contract Architecture

After Sprint 11.86, the CLI's external process behavior is protected across several complementary layers.

### Layer 1 — Semantic Vocabulary

```text
src/cli/exit_codes.py
```

Defines stable process categories:

```text
SUCCESS
FAILURE
INPUT_ERROR
INFRASTRUCTURE_ERROR
```

---

### Layer 2 — Stable Numeric Mapping

Tests protect the mapping:

```text
SUCCESS              → 0
FAILURE              → 1
INPUT_ERROR           → 2
INFRASTRUCTURE_ERROR  → 3
```

---

### Layer 3 — Source-Level Enforcement

CLI implementation code is protected against reintroducing unexplained raw process-status literals.

```text
CLI outcome
      ↓
CliExitCode
```

---

### Layer 4 — Python Process Boundary

All semantic values are verified through:

```text
CliExitCode
      ↓
SystemExit
      ↓
child interpreter
      ↓
OS-visible process status
```

---

### Layer 5 — Real CLI Executable Boundary

Representative commands execute:

```text
python -m src.cli.app
```

and verify actual application behavior through the process boundary.

---

### Layer 6 — Output-Channel Contract

Sprint 11.86 adds:

```text
normal output → stdout
diagnostics   → stderr
```

for representative real executable scenarios.

---

## Complete External Process Model

The protected external CLI path is now:

```text
user / automation
        ↓
python -m src.cli.app
        ↓
argument parser
        ↓
application behavior
        ↓
semantic classification
        ↓
CliExitCode
        ↓
SystemExit
        ↓
operating-system-visible process status
        +
stdout channel
        +
stderr channel
```

This gives external automation a predictable three-part interface:

```text
returncode
stdout
stderr
```

---

## Scope Guard

Sprint 11.86 intentionally does **not** introduce:

- new CLI commands,
- new CLI arguments,
- new process-status categories,
- new exit-code values,
- changes to `CliExitCode`,
- new exception classes,
- new regression behavior,
- new regression policy,
- new evaluation behavior,
- new quality-gate behavior,
- model execution changes,
- dataset changes,
- provenance changes,
- report schema changes,
- regression schema changes,
- public DTO changes,
- new dependencies,
- new subprocess abstractions,
- logging infrastructure,
- generalized output-routing infrastructure,
- test-only production hooks.

The sprint has one narrow responsibility:

> Verify that representative real CLI commands preserve the expected stdout/stderr channel contract.

---

## Production-Code Impact

```text
Production code changes: none
```

Sprint 11.86 verifies existing behavior rather than introducing new application semantics.

This is important because the sprint is a **contract-hardening sprint**, not a feature sprint.

The desirable result is:

```text
behavior already correct
        ↓
tests make correctness explicit
        ↓
future regression becomes detectable
```

---

## Compatibility

Sprint 11.86 is backward-compatible.

It does not change:

- CLI syntax,
- command names,
- available options,
- exit-code mappings,
- evaluation profiles,
- profile selection,
- dataset execution,
- model execution,
- evaluation execution,
- regression execution,
- report generation,
- quality gates,
- provenance handling,
- artifact formats,
- schemas,
- public APIs.

External callers continue to observe:

| Outcome | Process status |
|---|---:|
| Success | `0` |
| Evaluation/regression failure | `1` |
| Invalid invocation/input | `2` |
| Infrastructure failure | `3` |

Sprint 11.86 additionally protects representative stream semantics:

| Scenario | stdout | stderr |
|---|---|---|
| Successful informational command | normal output | empty |
| Invalid invocation | empty | diagnostic |

---

## Design Principles

### Protect Observable Behavior

CLI consumers interact with observable process behavior, not internal Python implementation details.

The contract therefore includes:

```text
returncode
stdout
stderr
```

---

### Test the Real Boundary

The tests execute:

```text
python -m src.cli.app
```

rather than mocking CLI internals.

This protects the same application boundary used by external automation.

---

### Avoid Brittle Exact-Output Assertions

The success test checks stable semantic content rather than freezing every character of the current profile listing.

This preserves useful flexibility while still detecting output-channel regressions.

---

### Prefer Narrow Contract Sprints

Sprint 11.86 does not mix output-channel verification with:

- CLI redesign,
- logging redesign,
- regression changes,
- reporting changes,
- model behavior,
- dataset behavior.

The result is easier to reason about, review, and maintain.

---

### Do Not Inflate Test Counts Artificially

Existing tests should be strengthened when the scenario already represents the required behavior.

Sprint 11.86 therefore improves the assertions of the successful real-process test instead of creating redundant subprocess cases.

---

## Reliability Impact

Before Sprint 11.86, the CLI process architecture strongly protected:

```text
semantic result
      ↓
exit code
```

After Sprint 11.86, the contract additionally protects:

```text
semantic result
      ↓
exit code
      +
output-channel placement
```

The resulting interface is better suited for:

- CI/CD quality gates,
- shell scripting,
- automated regression execution,
- developer tooling,
- orchestration,
- future platform integration.

---

## Security and IP Boundary

Sprint 11.86 does not expose new proprietary evaluation internals.

The verified interface consists only of already-public process-level behavior:

```text
exit status
stdout
stderr
```

No internal scoring logic, governance logic, evaluation intelligence, proprietary orchestration, or protected evidence-processing implementation is exposed.

The existing AI Test Lab public/private architecture boundary remains unchanged.

---

## Result

Sprint 11.86 successfully strengthens the real CLI process contract without modifying production behavior.

The verified external behavior is now:

```text
SUCCESS
    ↓
status 0
    ↓
normal information on stdout
    ↓
stderr empty
```

and:

```text
INPUT_ERROR
    ↓
status 2
    ↓
stdout empty
    ↓
diagnostic on stderr
```

Focused verification:

```text
2 passed
```

Full regression verification:

```text
642 passed
```

Production changes:

```text
none
```

Behavioral regressions:

```text
none detected
```

---

## Sprint 11.86 Completion Statement

Sprint 11.86 completes the next layer of AI Test Lab's CLI process-contract hardening by formally protecting output-channel semantics at the real executable boundary.

The CLI is now protected not merely as:

```text
command → integer exit code
```

but as the fuller automation interface:

```text
command
   ↓
semantic outcome
   ↓
process status
   +
stdout
   +
stderr
```

This provides a stronger and more predictable foundation for future CI/CD quality gates, automation integrations, and production-grade command-line workflows.