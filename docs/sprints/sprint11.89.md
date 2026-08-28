# Sprint 11.89 — CLI Contract Hardening & Sprint 11 Closure

## Status

**Completed**

Sprint 11.89 closes Sprint 11 by hardening the AI Test Lab CLI process contract, completing diagnostic coverage, validating CI-facing behavior, and confirming the entire framework remains regression-safe.

This sprint intentionally consolidates several tightly related verification tasks into one larger closure milestone rather than continuing with many small `11.xx` increments.

The result is a stable public CLI contract suitable for shell automation, CI/CD pipelines, regression gates, and future platform integration.

---

# Objective

The objective of Sprint 11.89 was to finalize the CLI execution boundary introduced and strengthened throughout the later Sprint 11 work.

The public process contract is:

```text
0 → SUCCESS
1 → FAILURE
2 → INPUT_ERROR
3 → INFRASTRUCTURE_ERROR
```

Each exit code communicates a materially different outcome to external automation.

The sprint focused on proving that these outcomes remain:

- deterministic,
- observable,
- semantically distinct,
- correctly routed between `stdout` and `stderr`,
- free from misleading success output,
- resistant to accidental contract drift,
- and safe for CI/CD consumption.

---

# Final CLI Exit-Code Contract

## Exit Code 0 — SUCCESS

```text
CliExitCode.SUCCESS == 0
```

Meaning:

> The requested operation completed successfully.

Examples include:

```text
evaluation profile listing
successful evaluation
successful dataset validation
successful regression allow decision
```

Normal command output is emitted through:

```text
stdout
```

No error diagnostic is expected on:

```text
stderr
```

---

## Exit Code 1 — FAILURE

```text
CliExitCode.FAILURE == 1
```

Meaning:

> AI Test Lab completed the requested operation, but the evaluated condition failed.

Examples include:

```text
dataset validation failure
evaluation failure
quality-gate failure
regression block decision
```

This distinction is important.

Exit code `1` does **not** mean that AI Test Lab itself failed to operate.

It means the framework successfully performed its job and produced a negative evaluation outcome.

---

## Exit Code 2 — INPUT_ERROR

```text
CliExitCode.INPUT_ERROR == 2
```

Meaning:

> The caller supplied an invalid command, configuration, or invocation.

Examples include:

```text
invalid evaluation profile
incomplete regression arguments
unsupported input combination
invalid dataset configuration
```

Input diagnostics are routed to:

```text
stderr
```

This allows CI/CD systems to distinguish a pipeline configuration problem from an actual evaluation failure.

---

## Exit Code 3 — INFRASTRUCTURE_ERROR

```text
CliExitCode.INFRASTRUCTURE_ERROR == 3
```

Meaning:

> AI Test Lab could not reliably complete the requested operation because of an infrastructure or runtime failure.

Examples include:

```text
report filesystem write failure
regression artifact persistence failure
runtime infrastructure failure
unavailable required infrastructure
```

Infrastructure diagnostics are emitted to:

```text
stderr
```

This outcome is intentionally distinct from:

```text
evaluation failure
input error
successful execution
```

---

# Final Public Process Matrix

| Outcome | Exit Code | Meaning |
|---|---:|---|
| Success | `0` | Command completed successfully |
| Failure | `1` | Command completed, but evaluation or validation failed |
| Input error | `2` | Caller supplied invalid input or invocation |
| Infrastructure error | `3` | Runtime or infrastructure prevented reliable completion |

This matrix is now verified at multiple layers.

---

# Infrastructure Output Contract Hardening

Sprint 11.88 established deterministic subprocess coverage for infrastructure failures.

Sprint 11.89 tightened that contract further.

The real CLI infrastructure test now verifies:

```python
assert completed.returncode == CliExitCode.INFRASTRUCTURE_ERROR
assert "Infrastructure error:" in completed.stderr
assert "Traceback" not in completed.stderr
assert "JSON report:" not in completed.stdout
assert "HTML report:" not in completed.stdout
```

This confirms that an infrastructure failure:

```text
returns exit code 3
writes its diagnostic to stderr
does not expose traceback text as expected CLI output
does not falsely claim report generation succeeded
```

---

# Important Contract Refinement

During Sprint 11.89, the first proposed hardening assertion was:

```python
assert completed.stdout == ""
```

The real subprocess test correctly failed.

The CLI had already emitted legitimate progress information:

```text
Loaded 0 test(s) from prompt file ...
```

before the later filesystem failure occurred.

That result exposed an important process-design distinction.

The correct infrastructure contract is **not**:

```text
infrastructure failure
    ↓
stdout must always be completely empty
```

A process may legitimately emit progress before encountering a later failure.

The correct contract is:

```text
progress output before the failure
        ↓
allowed

failure occurs
        ↓
no false completion output
no false success output
infrastructure diagnostic → stderr
exit code → 3
```

Therefore Sprint 11.89 verifies that these success-style messages are absent:

```text
JSON report:
HTML report:
```

when report generation actually failed.

This is more realistic and more durable than requiring globally empty `stdout`.

---

# Why This Matters

A CI pipeline must be able to distinguish:

```text
AI quality failed
```

from:

```text
the test infrastructure failed
```

and from:

```text
the pipeline called AI Test Lab incorrectly
```

Those conditions require different responses.

For example:

```text
exit 0
    → continue deployment

exit 1
    → block deployment because quality failed

exit 2
    → fix CI configuration or invocation

exit 3
    → investigate runtime or infrastructure
```

Without explicit process semantics, these outcomes can become indistinguishable to automation.

---

# Diagnostic Contract Completion

Sprint 11.89 also completed direct unit coverage for the general infrastructure diagnostic:

```python
print_infrastructure_error()
```

The test verifies:

```python
print_infrastructure_error("disk unavailable")
```

produces:

```text
stdout:
<empty>

stderr:
Infrastructure error: disk unavailable
```

Conceptually:

```python
assert captured.out == ""
assert captured.err == "Infrastructure error: disk unavailable\n"
```

Infrastructure diagnostics now have the same direct contract coverage as the existing input, regression-execution, and regression-artifact diagnostics.

---

# Layered Contract Verification

The exit-code contract is intentionally tested at several layers.

These tests are related but not redundant.

---

## Layer 1 — Numeric Contract

File:

```text
tests/cli/test_exit_codes.py
```

This layer verifies that the public numeric meanings remain frozen:

```text
SUCCESS              = 0
FAILURE              = 1
INPUT_ERROR          = 2
INFRASTRUCTURE_ERROR = 3
```

It also verifies that these values remain integer-compatible for use by Python and operating-system process boundaries.

---

## Layer 2 — Python Process Boundary

File:

```text
tests/cli/test_exit_code_boundary.py
```

This layer verifies that each `CliExitCode` survives:

```python
raise SystemExit(...)
```

and becomes the expected operating-system return code.

Conceptually:

```text
CliExitCode
    ↓
SystemExit
    ↓
Python process
    ↓
OS return code
```

---

## Layer 3 — Real AI Test Lab CLI Process

File:

```text
tests/cli/test_cli_process_contract.py
```

This layer launches AI Test Lab as a real subprocess and verifies real CLI behavior.

The suite covers:

```text
success
failure
input error
infrastructure error
```

This is the most important external verification layer because it proves the behavior seen by:

```text
shell scripts
GitHub Actions
CI runners
deployment pipelines
external automation
```

---

## Layer 4 — Diagnostic Unit Contract

File:

```text
tests/cli/test_diagnostics.py
```

This layer verifies stable diagnostic prefixes and output-channel routing.

Covered diagnostics include:

```text
Input error:
Regression execution error:
Regression artifact error:
Infrastructure error:
```

---

# Deterministic Infrastructure Failure Strategy

The infrastructure subprocess test remains deliberately independent of external model infrastructure.

The test does not require:

```text
Ollama
network connectivity
remote APIs
model downloads
timing assumptions
external services
```

Instead, it uses a controlled local filesystem condition.

The test:

```text
creates an empty prompts file
        ↓
loads zero tests
        ↓
uses an existing directory as the JSON report destination
        ↓
report file creation fails
        ↓
OSError boundary is triggered
        ↓
Infrastructure error diagnostic
        ↓
exit code 3
```

This produces a deterministic and reproducible failure path.

---

# Exception Boundary

The report-writing boundary continues to catch:

```python
OSError
```

rather than:

```python
Exception
```

This design is intentional.

Filesystem and operating-system problems belong to the infrastructure classification.

Unexpected programming defects should not automatically be converted into ordinary infrastructure failures.

Conceptually:

```text
known user mistake
    → INPUT_ERROR

completed evaluation with negative result
    → FAILURE

known filesystem/runtime failure
    → INFRASTRUCTURE_ERROR

unexpected programming defect
    → remains visible for debugging
```

This protects debuggability and prevents broad exception masking.

---

# Test Consolidation Decision

Sprint 11.89 reviewed the apparent overlap between:

```text
test_exit_codes.py
test_exit_code_boundary.py
test_cli_process_contract.py
```

The conclusion was to retain all three.

They prove different contracts:

```text
test_exit_codes.py
    → numeric semantic contract

test_exit_code_boundary.py
    → Python/OS process compatibility

test_cli_process_contract.py
    → real AI Test Lab behavior
```

Removing one of these layers would reduce the ability to localize future failures.

The existing layered structure is therefore retained.

---

# CI/CD Readiness

At the end of Sprint 11.89, CI consumers can depend on the following interface:

```text
AI Test Lab CLI
        │
        ├── 0 → operation succeeded
        │
        ├── 1 → quality/evaluation condition failed
        │
        ├── 2 → invocation/input problem
        │
        └── 3 → infrastructure/runtime problem
```

Automation no longer needs to infer the meaning of failures from Python exceptions or loosely formatted console output.

That creates a clean foundation for future CI quality-gate integration.

---

# Public / Private Architecture Boundary

Sprint 11.89 preserves the AI Test Lab IP-protection boundary.

The CLI exposes only what external consumers require:

```text
stable exit codes
stable public diagnostics
public evaluation output
public report artifacts
```

The CLI contract does not require exposing:

```text
internal scoring algorithms
private governance rules
proprietary orchestration logic
commercial evidence intelligence
internal implementation details
```

Infrastructure diagnostics remain operational rather than architectural.

---

# Verification

## Infrastructure Diagnostic Tests

Command:

```powershell
pytest .\tests\cli\test_diagnostics.py -v
```

Result:

```text
4 passed in 0.06s
```

---

## Real CLI Process Contract

Command:

```powershell
pytest .\tests\cli\test_cli_process_contract.py -v
```

Result:

```text
4 passed in 5.11s
```

Verified subprocess outcomes:

```text
SUCCESS
FAILURE
INPUT_ERROR
INFRASTRUCTURE_ERROR
```

---

## Full CLI Test Suite

Command:

```powershell
pytest .\tests\cli -v
```

Result:

```text
48 passed in 5.71s
```

The CLI suite remains completely green after the hardening work.

---

## Full AI Test Lab Regression Suite

Command:

```powershell
pytest -v
```

Result:

```text
645 passed in 15.72s
```

This verifies that Sprint 11.89 introduced no regressions across the broader framework.

The full suite includes coverage across:

```text
CLI behavior
datasets
evaluation profiles
evaluation pipelines
DeepEval integration
metric configuration
quality gates
regression comparison
regression enforcement
run identity
provenance
reproducibility
report generation
public report contracts
schema compatibility
report fingerprints
report consumers
evidence flow
IP/public-contract boundaries
Ollama integration
```

---

# Repository Hygiene

Before Sprint closure, the modified files were checked with:

```powershell
git diff --check
```

Result:

```text
no output
```

This confirms no detected whitespace errors in the pending diff.

---

# Files Changed

Sprint 11.89 modifies:

```text
tests/cli/test_cli_process_contract.py
tests/cli/test_diagnostics.py
docs/sprints/sprint11.89.md
```

The behavioral changes are intentionally small.

The value of the sprint comes from stronger contract verification rather than large production-code changes.

---

# Acceptance Criteria

Sprint 11.89 is complete when all of the following are satisfied:

- [x] Public CLI exit codes remain `0`, `1`, `2`, and `3`.
- [x] Success is distinguishable from evaluation failure.
- [x] Evaluation failure is distinguishable from input failure.
- [x] Input failure is distinguishable from infrastructure failure.
- [x] Infrastructure errors return exit code `3`.
- [x] Infrastructure diagnostics are written to `stderr`.
- [x] Infrastructure diagnostics have direct unit coverage.
- [x] Expected infrastructure handling does not expose traceback text.
- [x] Infrastructure failure does not emit false JSON report completion output.
- [x] Infrastructure failure does not emit false HTML report completion output.
- [x] Legitimate progress output before a later failure remains allowed.
- [x] Infrastructure process verification remains deterministic.
- [x] Infrastructure process verification does not require Ollama.
- [x] Infrastructure process verification does not require networking.
- [x] Narrow exception boundaries remain preserved.
- [x] Numeric exit-code coverage remains intact.
- [x] Python process-boundary coverage remains intact.
- [x] Real CLI subprocess coverage remains intact.
- [x] Full CLI suite passes.
- [x] `48 passed in 5.71s`.
- [x] Full framework regression suite passes.
- [x] `645 passed in 15.72s`.
- [x] `git diff --check` is clean.

---

# Architectural Result

Sprint 11 closes with a stable machine-facing CLI boundary:

```text
                       AI Test Lab
                           │
                           ▼
                      CLI Boundary
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
        ▼                  ▼                  ▼
     SUCCESS            FAILURE          INPUT ERROR
        │                  │                  │
        0                  1                  2
                           │
                           ▼
                  INFRASTRUCTURE ERROR
                           │
                           3
```

More precisely:

```text
0 → execution succeeded

1 → execution completed but quality/validation failed

2 → caller supplied invalid input

3 → infrastructure prevented reliable completion
```

This contract is now verified:

```text
as Python values
at the Python process boundary
through real AI Test Lab subprocess execution
through stable stderr diagnostic contracts
through the full framework regression suite
```

---

# Sprint 11 Closure

Sprint 11 evolved AI Test Lab from basic evaluation-profile configuration into a significantly stronger evaluation and regression platform foundation.

Across Sprint 11, the framework established and strengthened areas including:

```text
evaluation profiles
runtime metric configuration
metric thresholds
metric runtime options
public report contracts
report compatibility
contract fingerprints
capability discovery
public/private report boundaries
evaluation run identity
provenance
reproducibility
regression comparison
regression severity
regression tolerance
regression gates
regression enforcement
candidate/baseline handling
CLI regression execution
CLI process semantics
deterministic exit codes
CI-facing failure classification
```

Sprint 11.89 does not add another large feature on top of those capabilities.

Instead, it closes the layer by proving that its external process behavior is stable enough for the next stage of AI Test Lab development.

---

# Final Result

Sprint 11.89 completes CLI contract hardening and closes Sprint 11.

Final verification:

```text
Infrastructure diagnostics:
4 passed

Real CLI subprocess contract:
4 passed

Full CLI suite:
48 passed

Full AI Test Lab suite:
645 passed in 15.72s

git diff --check:
clean
```

AI Test Lab now has a durable command-line process contract suitable for increasingly strict regression automation and future CI/CD quality gates.

**Sprint 11 is complete.**