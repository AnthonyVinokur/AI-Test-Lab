# Sprint 11.59 — CLI Regression Result Persistence Seam

## Objective

Add the smallest CLI-owned integration seam for persisting an already-built
`EvaluationRunRegressionResult`.

Sprint 11.59 connects the CLI layer to the deterministic JSON file writer from
Sprint 11.58 without adding command-line arguments or constructing regression
decisions during a normal evaluation run.

## Problem

Sprint 11.58 made approved regression results persistable, but the CLI layer
did not yet have an explicit entry point for using that persistence contract.

Directly wiring the full CLI would require additional decisions about baseline
selection, regression comparison orchestration, and output-path arguments.
Those concerns are deliberately kept outside this slice.

## Scope

Sprint 11.59 adds:

- a CLI-owned `write_cli_regression_result` function
- delegation to `write_evaluation_run_regression_result_json`
- exact deterministic ALLOW and BLOCK output tests
- a delegation test proving that the approved result and destination path are
  passed through unchanged

## Design

The new seam is located in:

```text
src/cli/regression_output.py
```

Its flow is:

```text
Already-built EvaluationRunRegressionResult
                    ↓
       CLI persistence seam
                    ↓
 Sprint 11.58 deterministic file writer
                    ↓
          Public JSON artifact
```

The CLI adapter has one responsibility: connect a future CLI caller to the
existing persistence boundary.

## Public / Private Boundary

The adapter accepts only the stable public result contract:

```text
EvaluationRunRegressionResult
```

It does not accept or inspect metric comparisons, regression gates,
enforcement internals, or other protected runtime objects.

It does not serialize with `__dict__`, `dataclasses.asdict`, or any automatic
object traversal. Serialization remains owned by the explicit serializer and
deterministic JSON encoder introduced in Sprints 11.56 and 11.57.

```text
Protected regression logic
            ↓
Approved public result
==============================
CLI persistence seam
            ↓
Existing deterministic writer
            ↓
External JSON file
```

## Deterministic Output

The seam delegates to the Sprint 11.58 writer, so output remains byte-for-byte
stable:

```json
{"enforcement":"allow","exit_code":0}
```

or:

```json
{"enforcement":"block","exit_code":1}
```

No CLI-specific serializer or alternate JSON formatting path is introduced.

## Tests

Focused tests verify:

1. The exact approved result object and path are delegated unchanged.
2. An ALLOW result produces the exact deterministic public JSON.
3. A BLOCK result produces the exact deterministic public JSON and preserves
   nested-directory creation through the existing writer.

The focused test module is:

```text
tests/cli/test_regression_output.py
```

## Verification

Focused Sprint 11.59 plus serializer, encoder, and writer boundary tests:

```text
16 passed in 0.11s
```

Complete CI-equivalent unit suite:

```text
530 passed, 1 deselected in 1.33s
```

The deselected test is the existing real Ollama integration test, matching the
repository's GitHub Actions test command.

Whitespace verification:

```text
git diff --check
```

completed without errors.

## Explicitly Out of Scope

Sprint 11.59 does not add:

- a regression output-path command-line argument
- a default regression output path
- normal-run CLI wiring
- baseline or candidate input selection
- regression comparison orchestration
- regression result construction
- new JSON fields or schema versioning
- timestamps, run IDs, history, aggregation, APIs, or CI/CD integration

## Acceptance Criteria

- The CLI layer owns a named regression-result persistence seam.
- The seam accepts an already-built public `EvaluationRunRegressionResult`.
- The seam delegates to the existing Sprint 11.58 writer.
- The seam contains no regression decision logic or serialization logic.
- ALLOW and BLOCK files remain byte-for-byte deterministic.
- Focused and full test suites pass.
- `git diff --check` reports no whitespace errors.

## Next Small Slice

Sprint 11.60 can add a dedicated CLI output-path argument and wire it to this
seam once the CLI has an approved public result available. Regression input and
comparison orchestration should remain separate unless a later sprint defines
their contracts explicitly.

## Result

The persistence stack now reaches a CLI-owned boundary:

```text
Stable public result
        ↓
Explicit serializer
        ↓
Deterministic JSON encoder
        ↓
JSON file writer
        ↓
CLI persistence seam
```

This is a small, reversible integration step that preserves the established
public/private boundary and prepares the CLI for explicit argument wiring in a
later sprint.
