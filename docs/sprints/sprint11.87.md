# Sprint 11.87 — Real CLI Failure Outcome Contract Verification

## Status

**Completed**

---

## Summary

Sprint 11.87 strengthens AI Test Lab's command-line interface contract by verifying that a **valid CLI operation whose result is a failure** is exposed correctly through the real operating-system process boundary.

The preceding CLI hardening sequence established and progressively verified the semantic process contract:

```text
Sprint 11.81 → Define semantic CLI exit codes
Sprint 11.82 → Complete adoption of semantic exit codes
Sprint 11.83 → Enforce semantic exit-code usage
Sprint 11.84 → Verify the Python process boundary
Sprint 11.85 → Verify the real CLI executable boundary
Sprint 11.86 → Verify stdout / stderr channel behavior
Sprint 11.87 → Verify the real CLI FAILURE outcome
```

Before this sprint, the real executable process tests already protected:

```text
SUCCESS     → exit status 0
INPUT_ERROR → exit status 2
```

Sprint 11.87 adds executable verification for:

```text
FAILURE → exit status 1
```

The verified scenario uses dataset validation because it provides a clean semantic distinction between:

```text
invalid command or invalid invocation
        ↓
INPUT_ERROR
        ↓
2
```

and:

```text
valid command
        ↓
operation executes normally
        ↓
validation verdict fails
        ↓
FAILURE
        ↓
1
```

No production behavior changes.

No CLI syntax changes.

No exit-code values change.

No evaluation, regression, model, reporting, or dataset-runtime behavior changes.

This sprint strengthens automated verification of the existing public CLI process contract.

---

## Objective

Protect the real executable mapping:

```text
valid CLI operation
        ↓
completed operation
        ↓
failed business/validation outcome
        ↓
CliExitCode.FAILURE
        ↓
SystemExit
        ↓
operating-system-visible exit status 1
```

The sprint also protects the associated output-channel behavior:

```text
validation result information → stdout
stderr                        → empty
```

The objective is not to introduce a new failure condition.

The objective is to prove that an already-defined semantic failure survives the complete executable boundary exactly as intended.

---

## Background

AI Test Lab uses semantic exit codes rather than unexplained process-status integers.

The CLI vocabulary is:

```text
SUCCESS               → 0
FAILURE               → 1
INPUT_ERROR           → 2
INFRASTRUCTURE_ERROR  → 3
```

These categories communicate different classes of outcome to:

- CI/CD systems,
- shell scripts,
- parent processes,
- test automation,
- build pipelines,
- deployment tooling,
- developer workflows.

The distinction matters because not every non-zero process result represents the same condition.

For example:

```text
command malformed
    ≠
command valid but evaluated result failed
```

A caller may legitimately react differently to those two conditions.

Sprint 11.87 protects that distinction at the real executable boundary.

---

## Why Sprint 11.87 Is Needed

Prior process-boundary verification already demonstrated:

### Successful informational command

```text
python -m src.cli.app --list-evaluation-profiles
```

Contract:

```text
return code = 0
stdout      = normal output
stderr      = empty
```

Semantic outcome:

```text
SUCCESS
```

---

### Invalid regression invocation

An incomplete regression invocation produces:

```text
return code = 2
stdout      = empty
stderr      = invocation diagnostic
```

Semantic outcome:

```text
INPUT_ERROR
```

---

However, those two scenarios did not verify a third important case:

> What happens when the command itself is valid, execution completes normally, but the operation's verdict is unsuccessful?

That scenario belongs to:

```text
CliExitCode.FAILURE
```

and must not be confused with:

```text
INPUT_ERROR
```

or:

```text
INFRASTRUCTURE_ERROR
```

Sprint 11.87 closes that gap.

---

## Selected Verification Scenario

The sprint uses managed-dataset validation.

The CLI already supports:

```text
--validate-dataset
```

Dataset validation is an appropriate executable contract test because it can produce a deterministic semantic failure without depending on:

- Ollama,
- network access,
- model execution,
- external APIs,
- timing,
- environmental instability,
- artificial production hooks.

The test creates a temporary managed dataset that is structurally valid but semantically invalid.

Specifically:

```text
dataset status = active
entries        = empty
```

AI Test Lab's dataset validator treats this condition as:

```text
active_dataset_empty
```

The validation command therefore:

1. parses successfully,
2. loads the dataset successfully,
3. executes validation normally,
4. discovers a validation error,
5. reports the failed validation,
6. returns `CliExitCode.FAILURE`,
7. exits the child Python process with status `1`.

This is exactly the behavior Sprint 11.87 needs to protect.

---

## Verified Contract

The executable path is:

```text
python -m src.cli.app
        ↓
argument parsing
        ↓
managed dataset loading
        ↓
dataset validation
        ↓
validation errors discovered
        ↓
validation result = failed
        ↓
CliExitCode.FAILURE
        ↓
SystemExit
        ↓
child Python interpreter
        ↓
OS-visible return code 1
```

Output behavior is also verified:

```text
stdout:
    validation diagnostic information
    active_dataset_empty
    Dataset validation failed.

stderr:
    empty
```

---

## FAILURE vs INPUT_ERROR

A major purpose of this sprint is to protect semantic separation between two different non-zero outcomes.

### FAILURE

```text
valid request
    ↓
operation executes
    ↓
operation produces an unsuccessful verdict
    ↓
FAILURE
    ↓
1
```

Example:

```text
dataset validation completed
but validation errors were found
```

---

### INPUT_ERROR

```text
invalid request
    ↓
operation cannot validly proceed
    ↓
INPUT_ERROR
    ↓
2
```

Example:

```text
required related regression arguments were not supplied together
```

---

The distinction can be summarized as:

```text
FAILURE     = "The requested operation ran and failed its verdict."

INPUT_ERROR = "The requested operation could not validly begin."
```

This distinction is important for automation.

A CI pipeline may intentionally handle these outcomes differently.

For example:

```text
1 → quality or validation failure
2 → caller/configuration error
```

---

## Implementation

Sprint 11.87 extends:

```text
tests/cli/test_cli_process_contract.py
```

with one additional executable-level test:

```python
def test_real_cli_dataset_validation_failure_returns_failure_exit_code(
    tmp_path,
) -> None:
```

The test creates an isolated temporary dataset repository using `tmp_path`.

This avoids:

- modifying repository datasets,
- relying on persistent local state,
- sharing mutable test fixtures,
- machine-specific paths,
- external services.

The test then executes the real application:

```python
subprocess.run(
    [
        sys.executable,
        "-m",
        "src.cli.app",
        "--validate-dataset",
        dataset_id,
        "--dataset-storage",
        str(dataset_storage),
    ],
    check=False,
    capture_output=True,
    text=True,
)
```

This is important.

The test does not call:

```python
main(...)
```

directly.

Instead, it starts another Python interpreter and executes the actual CLI module.

Therefore the test protects the complete process path:

```text
application semantics
        ↓
CliExitCode.FAILURE
        ↓
SystemExit
        ↓
Python child process
        ↓
OS-visible process status
```

---

## Assertions

The new executable contract verifies:

```python
assert completed.returncode == CliExitCode.FAILURE
```

This protects:

```text
FAILURE → 1
```

It also verifies stable semantic output markers:

```python
assert "active_dataset_empty" in completed.stdout
assert "Dataset validation failed." in completed.stdout
```

and output-channel isolation:

```python
assert completed.stderr == ""
```

The protected behavior is therefore:

```text
valid validation command
        ↓
validation failure
        ↓
return code 1
        +
failure information on stdout
        +
empty stderr
```

---

## Why stdout Is Correct for This Failure

A failed validation verdict is not the same as a command-processing error.

The application successfully performed the requested operation.

It produced a legitimate result:

```text
Dataset validation failed.
```

That result belongs to normal command output.

Therefore:

```text
validation result → stdout
```

rather than:

```text
validation result → stderr
```

`stderr` remains reserved for diagnostics where execution cannot validly proceed or infrastructure fails.

This gives the CLI a clearer external model:

```text
successful operation result       → stdout
failed operation verdict          → stdout + non-zero semantic status
invalid invocation diagnostic     → stderr
infrastructure diagnostic         → stderr
```

---

## Process Contract After Sprint 11.87

The real executable test matrix now protects:

| Scenario | Semantic outcome | OS exit status | stdout | stderr |
|---|---|---:|---|---|
| List evaluation profiles | `SUCCESS` | `0` | Normal information | Empty |
| Dataset validation failure | `FAILURE` | `1` | Validation result | Empty |
| Invalid regression invocation | `INPUT_ERROR` | `2` | Empty | Diagnostic |

The fourth semantic category remains defined and separately protected at lower application layers:

```text
INFRASTRUCTURE_ERROR → 3
```

A real executable infrastructure-error scenario is intentionally not forced into Sprint 11.87 because doing so would currently require additional environmental coupling or artificial process-control mechanisms.

That concern is better addressed independently rather than weakening the process-contract test architecture.

---

## Why Infrastructure Error Is Not Forced Into This Sprint

A contract test is strongest when the tested condition is:

- deterministic,
- natural,
- reproducible,
- isolated,
- representative of real behavior.

The `FAILURE` scenario satisfies all of those requirements through dataset validation.

A real executable `INFRASTRUCTURE_ERROR` scenario would currently require reaching deeper regression execution paths and potentially interacting with:

- model execution,
- baseline artifacts,
- regression provenance,
- filesystem failures,
- external runtime availability.

Introducing a test-only production switch merely to force such a condition would reduce architectural quality.

Sprint 11.87 therefore follows a deliberate rule:

> Do not distort production architecture merely to increase process-test coverage.

`INFRASTRUCTURE_ERROR` executable verification can be addressed separately if a clean deterministic boundary becomes available.

---

## Test Verification

### Focused CLI Process Contract

Command:

```powershell
pytest .\tests\cli\test_cli_process_contract.py -v
```

Result:

```text
3 passed
```

The focused test file now protects:

```text
SUCCESS     → 0
FAILURE     → 1
INPUT_ERROR → 2
```

through real child-process CLI execution.

---

## Full Regression Suite

Command:

```powershell
pytest -q
```

Result:

```text
643 passed in 9.33s
```

Previous Sprint 11.86 baseline:

```text
642 passed
```

Sprint 11.87 result:

```text
643 passed
```

Change:

```text
+1 executable process-contract test
```

No regressions were detected.

---

## Test-Count Integrity

During implementation, an incomplete infrastructure-error test temporarily existed without assertions.

Because a pytest test that returns normally is considered successful, that incomplete test temporarily increased the suite count without actually protecting behavior.

It was removed before Sprint 11.87 completion.

The final verified count is:

```text
643 passed
```

This reinforces an important testing principle:

> A larger test count is not useful unless every test protects meaningful behavior.

Sprint 11.87 therefore records only the completed executable `FAILURE` contract test.

---

## Production-Code Impact

```text
Production code changes: none
```

Sprint 11.87 does not modify application behavior.

It verifies behavior already implemented by the CLI.

The only functional change to the repository is stronger automated contract coverage.

---

## Scope Guard

Sprint 11.87 intentionally does **not** introduce:

- new CLI commands,
- new CLI flags,
- new exit-code values,
- new semantic outcome categories,
- changes to `CliExitCode`,
- changes to dataset validation rules,
- new exception classes,
- model execution changes,
- regression policy changes,
- quality-gate changes,
- report-schema changes,
- provenance-schema changes,
- DTO changes,
- new dependencies,
- logging infrastructure,
- subprocess abstractions,
- test-only production switches,
- artificial infrastructure failures.

The sprint has one narrow responsibility:

> Verify that a real CLI validation failure reaches the operating system as `CliExitCode.FAILURE` / process status `1`.

---

## Architectural Value

Sprint 11.87 strengthens the boundary between AI Test Lab and external automation.

The CLI is increasingly becoming a stable machine-consumable interface rather than merely a human-facing terminal command.

External tooling can now rely on a clearer outcome vocabulary:

```text
0 → requested operation succeeded
1 → requested operation completed but produced a failing verdict
2 → invocation/input was invalid
3 → infrastructure prevented normal completion
```

This enables future CI/CD logic such as:

```text
exit 0 → continue pipeline
exit 1 → fail quality gate
exit 2 → flag pipeline/configuration defect
exit 3 → flag infrastructure/runtime incident
```

Sprint 11.87 therefore contributes directly to the longer-term goal of reliable CI quality-gate integration.

---

## CLI Contract Architecture

After Sprint 11.87:

### Layer 1 — Semantic Vocabulary

```text
CliExitCode
```

defines:

```text
SUCCESS
FAILURE
INPUT_ERROR
INFRASTRUCTURE_ERROR
```

---

### Layer 2 — Numeric Stability

```text
SUCCESS               → 0
FAILURE               → 1
INPUT_ERROR           → 2
INFRASTRUCTURE_ERROR  → 3
```

---

### Layer 3 — Source-Level Enforcement

CLI decision paths use semantic exit codes instead of unexplained process integers.

---

### Layer 4 — Python Process Boundary

Semantic values are verified through:

```text
CliExitCode
    ↓
SystemExit
    ↓
child interpreter
    ↓
OS process status
```

---

### Layer 5 — Real CLI Execution

Tests invoke:

```text
python -m src.cli.app
```

rather than bypassing the executable interface.

---

### Layer 6 — Output Channels

Representative scenarios protect the distinction between:

```text
stdout
stderr
returncode
```

---

### Layer 7 — Failure Verdict Verification

Sprint 11.87 explicitly verifies:

```text
valid operation
    ↓
failed verdict
    ↓
FAILURE
    ↓
exit status 1
```

---

## Complete External Model

The protected architecture now looks like:

```text
CI / shell / user / automation
            ↓
    python -m src.cli.app
            ↓
      argument parsing
            ↓
    application operation
            ↓
      semantic outcome
            ↓
        CliExitCode
            ↓
        SystemExit
            ↓
    operating-system process
            ↓
 ┌──────────┼──────────┐
 ↓          ↓          ↓
status     stdout      stderr
```

Representative verified mappings:

```text
SUCCESS
    → 0
    → normal stdout
    → empty stderr

FAILURE
    → 1
    → failed-operation result on stdout
    → empty stderr

INPUT_ERROR
    → 2
    → empty stdout
    → diagnostic stderr
```

---

## Acceptance Criteria

Sprint 11.87 is complete when:

- [x] A real CLI command produces a deterministic semantic `FAILURE`.
- [x] The command is executed through `python -m src.cli.app`.
- [x] The child process exits with status `1`.
- [x] The test compares the process result against `CliExitCode.FAILURE`.
- [x] Failed validation information appears on `stdout`.
- [x] `stderr` remains empty for the failed validation verdict.
- [x] No external model or network dependency is required.
- [x] No production behavior is changed.
- [x] Focused CLI process tests pass.
- [x] Full project regression suite passes.
- [x] Final suite result is `643 passed`.

---

## Final Result

Sprint 11.87 adds one narrow but important guarantee:

```text
A valid AI Test Lab CLI operation that completes normally
but produces a failing validation verdict
is exposed to external automation as:

CliExitCode.FAILURE
        ↓
process status 1
```

The external CLI contract now has real executable verification for three distinct semantic outcomes:

```text
SUCCESS     → 0
FAILURE     → 1
INPUT_ERROR → 2
```

This improves the reliability of AI Test Lab as a future CI/CD quality-gate component while preserving the project's incremental, deterministic, and contract-first development approach.