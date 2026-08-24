# Sprint 11.60 - CLI Regression Result Output Path

## Objective

Add a dedicated, optional command-line argument for selecting where an approved
public regression result will eventually be written.

Sprint 11.60 establishes CLI ownership of the output-path contract without
adding regression comparison orchestration or manufacturing a regression result
inside the existing evaluation workflow.

## Problem

Sprint 11.59 introduced the CLI-owned persistence seam:

```text
write_cli_regression_result(...)
```

That seam can persist an already-built public
`EvaluationRunRegressionResult`, but the CLI parser did not provide a dedicated
way for a caller to select the destination path.

Reusing the existing `--report` argument would mix two different artifacts:

- the normal evaluation report
- the public regression enforcement result

These artifacts have different contracts and responsibilities and therefore
need separate output arguments.

## Scope

Sprint 11.60 adds:

- the optional `--regression-result-output` CLI argument
- conversion of the supplied value to `pathlib.Path`
- a default value of `None`
- focused tests for both default and explicitly supplied behavior
- documentation of the argument's intentionally narrow boundary

## CLI Contract

The new argument is:

```text
--regression-result-output PATH
```

Example:

```powershell
ai-test-lab `
    --regression-result-output results/regression-result.json
```

When supplied, the parsed value is:

```python
Path("results/regression-result.json")
```

When omitted, the value is:

```python
None
```

## Why the Default Is None

Sprint 11.60 does not assign an automatic regression-result filename.

A default file path could imply that every normal evaluation run already
produces an approved regression result. That is not yet true.

Using `None` makes the behavior explicit:

```text
Argument omitted
      ↓
No regression output requested
```

and:

```text
Argument supplied
      ↓
Destination path is available to future regression orchestration
```

This avoids accidental files, placeholder results, and hidden regression
decisions.

## Separation from Existing Reports

The CLI now recognizes three separate output concepts:

```text
--report
    Normal JSON evaluation report

--html-report
    Normal HTML evaluation report

--regression-result-output
    Optional public regression enforcement result
```

The new argument does not replace, modify, or share a default with either
existing report option.

## Public / Private Boundary

The output-path argument contains no regression policy or evaluation data.

It does not expose:

- baseline or candidate internals
- metric comparison details
- regression gate internals
- enforcement policy internals
- proprietary scoring or governance logic

The intended future flow remains:

```text
Protected regression processing
              ↓
Approved EvaluationRunRegressionResult
========================================
CLI persistence seam
              ↓
User-selected output path
              ↓
Deterministic public JSON
```

Only the approved public result may cross into the existing CLI persistence
seam.

## Implementation

The argument is defined in:

```text
src/cli/arguments.py
```

Its parser configuration is:

```python
parser.add_argument(
    "--regression-result-output",
    type=Path,
    default=None,
    help=(
        "Optional destination path for the public regression "
        "result JSON."
    ),
)
```

No changes are made to:

```text
src/cli/app.py
src/cli/regression_output.py
```

The existing application flow does not yet construct an
`EvaluationRunRegressionResult`. Wiring the path into `main()` without such a
result would require comparison and orchestration decisions outside this
sprint's boundary.

## Tests

Focused argument tests verify:

1. Omitting the option produces `None`.
2. Supplying the option produces the expected `Path`.
3. Existing CLI argument behavior remains unchanged.

The updated test module is:

```text
tests/cli/test_arguments.py
```

## Verification

Focused argument tests:

```text
9 passed in 0.08s
```

Complete CLI test suite:

```text
17 passed in 0.49s
```

Complete local test suite:

```text
532 passed in 10.59s
```

Whitespace verification:

```text
git diff --check
```

completed without errors.

## Explicitly Out of Scope

Sprint 11.60 does not add:

- a default regression-result output path
- regression-result construction
- baseline input selection
- candidate input selection
- baseline-versus-candidate comparison orchestration
- regression gate execution from the normal CLI
- enforcement decision construction in `main()`
- unconditional regression file creation
- changes to the public regression-result schema
- new JSON fields or schema versioning
- timestamps, run IDs, history, or aggregation
- CI/CD regression execution

## Acceptance Criteria

- The CLI accepts `--regression-result-output PATH`.
- The supplied value is parsed as `pathlib.Path`.
- Omitting the argument produces `None`.
- Existing report arguments remain unchanged.
- No regression decision or comparison logic is added.
- No file is written merely because the parser recognizes the argument.
- Focused and full test suites pass.
- `git diff --check` reports no whitespace errors.

## Next Small Slice

A later sprint can connect this parsed path to the Sprint 11.59 persistence seam
when the CLI has an explicitly approved public
`EvaluationRunRegressionResult`.

Baseline selection and regression comparison orchestration should remain
separate until their input and public-boundary contracts are deliberately
defined.

## Result

The CLI now owns an explicit destination contract for future public regression
output:

```text
--regression-result-output PATH
                 ↓
Optional pathlib.Path
                 ↓
Future approved public regression result
                 ↓
Existing CLI persistence seam
                 ↓
Deterministic JSON artifact
```

This is a small, reversible step that prepares the CLI for regression-result
wiring without weakening the established public/private boundary.