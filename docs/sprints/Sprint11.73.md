# Sprint 11.73 — Regression CLI Input Contract

## Summary

Sprint 11.73 defines the command-line input contract required to request evaluation-run regression from AI Test Lab.

Sprint 11.72 introduced a stable application-facing regression entry point:

```python
execute_evaluation_run_regression(...)
```

That entry point requires explicit baseline and candidate inputs. However, the CLI previously exposed only:

```text
--regression-result-output
```

This meant the command line could specify where a regression result should be written, but it could not explicitly identify the baseline public report or the baseline provenance required to perform a reproducible regression comparison.

Sprint 11.73 closes that contract gap.

The CLI now exposes three regression-related arguments:

```text
--regression-baseline-report
--regression-baseline-provenance
--regression-result-output
```

These arguments form one atomic CLI contract.

The central rule introduced by this sprint is:

> **Regression CLI inputs must be supplied completely or not supplied at all.**

A normal evaluation remains valid with no regression arguments.

A regression-enabled invocation becomes valid only when all three regression arguments are supplied together.

Sprint 11.73 intentionally does not execute regression. Its responsibility is limited to defining and validating the CLI-facing input boundary that a later integration sprint can safely connect to the Sprint 11.72 regression entry point.

---

## Objective

Provide an explicit, deterministic CLI contract for requesting evaluation-run regression.

The CLI must be capable of identifying:

1. the baseline public evaluation report;
2. the stored baseline evaluation-run provenance;
3. the destination for the public regression result.

The sprint must also prevent incomplete regression configurations from reaching later application layers.

---

## Problem Before Sprint 11.73

Before this sprint, the CLI already exposed:

```text
--regression-result-output
```

Example:

```powershell
ai-test-lab `
  --regression-result-output results/regression-result.json
```

This argument specified only the destination of a future regression result.

It did not answer two critical questions:

```text
Which baseline evaluation report should be used?

Which provenance record belongs to that baseline?
```

The regression entry point created in Sprint 11.72 requires explicit runtime inputs.

Conceptually:

```text
candidate evaluation results
        +
baseline public report
        +
baseline provenance
        +
candidate identity
        +
candidate dataset version
        +
public report schema version
        ↓
execute_evaluation_run_regression(...)
```

Without corresponding CLI inputs, the command line could not represent the baseline portion of that contract.

That created an incomplete application boundary.

---

## Solution

Sprint 11.73 adds two new command-line arguments:

```text
--regression-baseline-report
--regression-baseline-provenance
```

Together with the existing:

```text
--regression-result-output
```

the CLI now has an explicit regression input contract.

Example:

```powershell
ai-test-lab `
  --dataset regression-suite `
  --dataset-version 3 `
  --regression-baseline-report results/baseline.json `
  --regression-baseline-provenance results/baseline-provenance.json `
  --regression-result-output results/regression-result.json
```

Conceptually:

```text
CLI
 │
 ├── --regression-baseline-report
 ├── --regression-baseline-provenance
 └── --regression-result-output
              │
              ▼
       validated regression
          CLI contract
              │
              ▼
     future execution wiring
```

---

## New CLI Arguments

### `--regression-baseline-report`

Type:

```python
Path
```

Purpose:

Identifies the versioned public AI Test Lab evaluation report that should serve as the regression baseline.

Example:

```powershell
--regression-baseline-report results/baseline.json
```

This sprint does not read or validate the contents of that report.

It only captures the path as part of the CLI contract.

---

### `--regression-baseline-provenance`

Type:

```python
Path
```

Purpose:

Identifies the stored evaluation-run provenance associated with the selected baseline report.

Example:

```powershell
--regression-baseline-provenance results/baseline-provenance.json
```

The provenance file is required because regression eligibility depends on compatibility between baseline and candidate evaluation runs.

Sprint 11.73 does not load or interpret the provenance file.

That behavior remains inside the established regression runtime.

---

### `--regression-result-output`

Type:

```python
Path
```

Purpose:

Specifies the destination path for the future public regression result.

Example:

```powershell
--regression-result-output results/regression-result.json
```

This argument existed before Sprint 11.73.

The sprint changes its effective contract by requiring it to participate in the complete regression argument set.

---

## Atomic Regression Input Contract

The three regression CLI arguments are treated as one logical configuration:

```text
regression baseline report
        +
regression baseline provenance
        +
regression result output
```

The valid states are:

```text
none supplied
```

or:

```text
all supplied
```

Any partial configuration is rejected.

Formally:

```text
0 of 3 supplied → valid

3 of 3 supplied → valid

1 of 3 supplied → invalid

2 of 3 supplied → invalid
```

---

## Why All-or-None Validation Matters

Allowing partial regression configuration would introduce ambiguous runtime states.

For example:

```powershell
--regression-result-output results/regression.json
```

would identify an output file without identifying the baseline.

Likewise:

```powershell
--regression-baseline-report results/baseline.json
```

would identify a report but provide no provenance record.

And:

```powershell
--regression-baseline-report results/baseline.json `
--regression-baseline-provenance results/baseline-provenance.json
```

would identify a complete baseline but provide no declared regression-result destination.

Rather than allowing incomplete configurations to flow deeper into the system, Sprint 11.73 rejects them at the argument-parsing boundary.

This keeps invalid application state out of the regression runtime.

---

## Validation Rule

The implementation groups the three CLI values:

```python
regression_arguments = (
    args.regression_baseline_report,
    args.regression_baseline_provenance,
    args.regression_result_output,
)
```

and rejects partial configuration:

```python
if any(value is not None for value in regression_arguments) and not all(
    value is not None for value in regression_arguments
):
    parser.error(
        "--regression-baseline-report, "
        "--regression-baseline-provenance, and "
        "--regression-result-output must be supplied together"
    )
```

This produces one compact invariant:

> **Regression mode cannot exist in a partially configured state.**

---

## Valid CLI States

### Normal evaluation

No regression arguments:

```powershell
ai-test-lab `
  --dataset regression-suite
```

Result:

```text
valid
```

Regression remains disabled.

---

### Complete regression configuration

```powershell
ai-test-lab `
  --dataset regression-suite `
  --regression-baseline-report results/baseline.json `
  --regression-baseline-provenance results/baseline-provenance.json `
  --regression-result-output results/regression-result.json
```

Result:

```text
valid
```

The CLI configuration is complete and can be consumed by a later execution-wiring layer.

Sprint 11.73 itself still does not execute regression.

---

## Invalid CLI States

### Baseline report only

```powershell
--regression-baseline-report results/baseline.json
```

Result:

```text
rejected
```

---

### Baseline provenance only

```powershell
--regression-baseline-provenance results/baseline-provenance.json
```

Result:

```text
rejected
```

---

### Result output only

```powershell
--regression-result-output results/regression-result.json
```

Result:

```text
rejected
```

---

### Baseline report and provenance without result output

```powershell
--regression-baseline-report results/baseline.json `
--regression-baseline-provenance results/baseline-provenance.json
```

Result:

```text
rejected
```

---

### Baseline report and result output without provenance

```powershell
--regression-baseline-report results/baseline.json `
--regression-result-output results/regression-result.json
```

Result:

```text
rejected
```

---

### Baseline provenance and result output without baseline report

```powershell
--regression-baseline-provenance results/baseline-provenance.json `
--regression-result-output results/regression-result.json
```

Result:

```text
rejected
```

---

## Architecture

Sprint 11.73 adds a CLI contract above the regression execution boundary established in Sprint 11.72.

```text
User / CI / Future Automation
              │
              ▼
        AI Test Lab CLI
              │
              ├── baseline report path
              ├── baseline provenance path
              └── regression result path
              │
              ▼
       CLI contract validation
              │
              ▼
      complete configuration
              │
              ▼
        future CLI wiring
              │
              ▼
execute_evaluation_run_regression(...)
              │
              ▼
 regression runtime assembly
              │
              ▼
 comparison → gate → enforcement
```

Sprint 11.73 stops at:

```text
complete configuration
```

The downward execution connection remains intentionally deferred.

---

## Relationship to Sprint 11.72

Sprint 11.72 created:

```python
execute_evaluation_run_regression(...)
```

as the stable application-facing execution boundary.

Sprint 11.73 creates the command-line contract needed to eventually invoke that boundary safely.

The relationship is therefore:

```text
Sprint 11.72
Regression Entry Point
        ↑
        │
future wiring
        │
Sprint 11.73
Regression CLI Input Contract
```

The two sprints deliberately separate:

```text
execution architecture
```

from:

```text
command-line interface design
```

This prevents the CLI from becoming coupled to internal regression construction details.

---

## Explicit Inputs Preserve Reproducibility

Sprint 11.73 continues the explicit-input design established in the regression architecture.

The CLI does not attempt to discover:

```text
the newest baseline
the latest successful run
a matching provenance file
a preferred dataset version
a promoted baseline
```

Instead, the caller provides the baseline paths explicitly.

This improves reproducibility because a regression invocation can later be reconstructed from known inputs.

Conceptually:

```text
same candidate
+
same baseline report
+
same baseline provenance
+
same contract versions
=
reconstructable regression execution
```

Automatic baseline selection may be introduced later as a separate policy layer.

It does not belong inside the CLI parsing contract.

---

## No Automatic Baseline Discovery

Sprint 11.73 intentionally does not add arguments such as:

```text
--latest-baseline
--auto-baseline
--find-baseline
--promote-baseline
```

Those options would introduce baseline-selection policy.

Baseline selection is materially different from baseline execution.

The regression runtime should compare against the baseline it is given.

A higher-level workflow may eventually decide which baseline should be supplied.

Keeping those responsibilities separate protects deterministic behavior and keeps future policy replaceable.

---

## No Filesystem Validation Yet

The CLI currently validates configuration completeness, not filesystem state.

Sprint 11.73 does not check whether:

```text
baseline report exists
baseline provenance exists
output parent directory exists
files contain valid JSON
report schema is supported
provenance is compatible
```

Those checks belong to established downstream boundaries.

For example:

```text
CLI parser
    ↓
syntactic/configuration validation

regression runtime
    ↓
report loading
provenance loading
schema validation
compatibility validation
```

This prevents duplicate validation logic.

---

## Error Boundary

Incomplete regression input is treated as a CLI usage error.

The parser exits using the standard `argparse` behavior:

```text
SystemExit: 2
```

This is appropriate because the failure occurs before application execution.

Examples include:

```text
missing baseline report
missing baseline provenance
missing regression output path
```

Downstream runtime failures remain separate concerns.

---

## Test Coverage

Sprint 11.73 extends:

```text
tests/cli/test_arguments.py
```

The test suite verifies:

### Default behavior

All regression arguments default to:

```python
None
```

This preserves ordinary non-regression CLI execution.

---

### Complete regression configuration

Supplying all three arguments parses them as:

```python
pathlib.Path
```

and preserves their values.

---

### Incomplete configuration rejection

Parameterized coverage verifies rejection of every partial combination:

```text
report only

provenance only

output only

report + provenance

report + output

provenance + output
```

This exhaustively tests the all-or-none contract.

---

## Verification Results

### Focused CLI argument suite

Command:

```powershell
pytest .\tests\cli\test_arguments.py -v
```

Result:

```text
16 passed in 0.09s
```

---

### Full AI Test Lab suite

Command:

```powershell
pytest -q
```

Result:

```text
618 passed in 11.58s
```

The full suite passing confirms that the new CLI validation does not regress existing framework behavior.

---

## Files Changed

```text
src/cli/arguments.py
tests/cli/test_arguments.py
docs/sprints/sprint11.73.md
```

---

## Files Intentionally Not Changed

Sprint 11.73 does not require changes to regression internals such as:

```text
src/evaluation_run_regression_entry_point.py
src/evaluation_run_regression_runtime.py
src/evaluation_run_regression_orchestrator.py
src/evaluation_run_case_regression_execution.py
```

It also does not require CLI execution changes yet.

This is intentional.

The sprint defines the input boundary without modifying the execution boundary.

---

## Non-Goals

Sprint 11.73 intentionally does not implement:

- regression execution from the CLI;
- baseline discovery;
- latest-baseline selection;
- baseline promotion;
- baseline persistence policy;
- report loading;
- provenance loading;
- candidate provenance construction;
- regression result serialization;
- CLI exit-code behavior for regression enforcement;
- CI/CD regression gates;
- regression artifact publication;
- regression history;
- API regression endpoints;
- dashboards;
- statistical regression thresholds;
- drift monitoring;
- governance policy;
- compliance workflows.

These remain separate architectural concerns.

---

## IP Protection Boundary

Sprint 11.73 exposes only configuration required by the public application boundary.

It does not expose:

- proprietary regression scoring logic;
- internal governance policy;
- evidence-intelligence mechanisms;
- commercial baseline-selection strategies;
- compliance orchestration;
- protected internal decision logic.

The CLI captures paths and validates completeness.

Regression behavior continues to remain behind the established regression execution boundary.

---

## Architectural Principle

The most important rule introduced by Sprint 11.73 is:

> **Validate regression configuration at the CLI boundary, but keep regression behavior behind the regression entry point.**

The CLI should know:

```text
what the user supplied
```

It should not need to know:

```text
how regression internals are assembled
how eligibility is determined
how cases are compared
how gating is evaluated
how enforcement is decided
```

That separation keeps the architecture shallow and replaceable.

---

## Before Sprint 11.73

```text
CLI
 │
 └── --regression-result-output
           │
           ▼
     incomplete regression
        configuration
```

The CLI could identify an output destination but could not identify the complete baseline.

---

## After Sprint 11.73

```text
CLI
 │
 ├── --regression-baseline-report
 ├── --regression-baseline-provenance
 └── --regression-result-output
           │
           ▼
       all-or-none
        validation
           │
           ▼
   complete regression
      input contract
```

The CLI now has enough information to support deterministic regression execution in a later sprint.

---

## Sprint Progression

The regression architecture now progresses through:

```text
Regression contracts
        ↓
Baseline acquisition boundary
        ↓
Stored baseline acquisition
        ↓
Regression orchestration
        ↓
Case-level regression gate
        ↓
Regression enforcement
        ↓
Case-level execution composition
        ↓
Stored baseline provenance loading
        ↓
Candidate provenance construction
        ↓
Regression runtime assembly
        ↓
Regression entry-point integration
        ↓
Regression CLI input contract
        ↓
Future CLI execution wiring
        ↓
Future result serialization / exit-code policy / CI integration
```

Sprint 11.73 marks the transition from:

```text
application-invokable regression capability
```

to:

```text
CLI-representable regression configuration
```

The next architectural step can therefore focus solely on wiring validated CLI state into the existing regression entry point.

---

## Acceptance Criteria

Sprint 11.73 is complete when:

- [x] `--regression-baseline-report` exists.
- [x] `--regression-baseline-provenance` exists.
- [x] `--regression-result-output` remains supported.
- [x] All three values use `pathlib.Path`.
- [x] All three default to `None`.
- [x] Normal evaluation with no regression arguments remains valid.
- [x] Supplying all regression arguments is valid.
- [x] Supplying only one regression argument is rejected.
- [x] Supplying any two regression arguments is rejected.
- [x] All incomplete argument combinations are tested.
- [x] No regression execution is introduced.
- [x] Existing regression internals remain unchanged.
- [x] Focused CLI tests pass.
- [x] Full project regression tests pass.

---

## Final Result

Sprint 11.73 gives AI Test Lab a complete and deterministic CLI representation of a regression request without prematurely coupling command-line parsing to regression execution.

The CLI can now express:

```text
this baseline report
+
this baseline provenance
+
this regression result destination
```

while rejecting incomplete configurations before they enter the application runtime.

This creates a clean foundation for the next integration step:

```text
validated CLI regression request
        ↓
execute_evaluation_run_regression(...)
```

without duplicating or exposing regression internals.