# Sprint 11.77 — Regression CLI Artifact Failure Handling

## Goal

Define deterministic CLI behavior when the required regression result artifact cannot be persisted.

Sprint 11.76 established the regression CLI result-output contract. Sprint 11.77 hardens that contract by ensuring filesystem failures during artifact persistence do not escape as uncontrolled exceptions or produce misleading regression exit behavior.

## Problem

Regression execution may complete successfully, but the required regression result artifact can still fail to reach disk because of conditions such as:

- parent directory creation failure
- permission denial
- filesystem write failure
- unavailable or full storage

Without an explicit failure boundary, these errors propagate directly from the filesystem and bypass the CLI's established process-level contract.

## Design

The persistence layer now translates expected filesystem failures into a dedicated domain exception:

`EvaluationRunRegressionResultWriteError`

The low-level regression result writer catches `OSError` and raises the dedicated exception while preserving the original exception through Python exception chaining.

The CLI application boundary catches only this known regression artifact failure and maps it to:

`exit code 3`

The regression result output adapter remains a thin delegation layer.

## Exit-Code Contract

- `0` — regression execution completed with an ALLOW result
- `1` — regression execution completed with a BLOCK result
- `2` — invalid input or configuration
- `3` — required regression result artifact could not be persisted

Artifact persistence failure takes precedence over the normal regression verdict exit code because the required evidence artifact was not successfully produced.

Examples:

- ALLOW + successful artifact write → `0`
- BLOCK + successful artifact write → `1`
- ALLOW + artifact write failure → `3`
- BLOCK + artifact write failure → `3`

## Implementation

### Regression result writer

`src/evaluation_run_regression_result_writer.py`

Added:

`EvaluationRunRegressionResultWriteError`

The writer now wraps filesystem-related `OSError` failures originating from directory creation or file writing.

The original exception remains available through `__cause__`.

Broad `Exception` handling is intentionally avoided so programming defects and unexpected failures remain visible.

### CLI application

`src/cli/app.py`

The regression result artifact write is now executed inside a narrow exception boundary.

When `EvaluationRunRegressionResultWriteError` is raised:

- a regression artifact error is written to stderr
- the CLI returns exit code `3`
- the regression ALLOW/BLOCK exit code is not returned

### Tests

Added regression result writer tests covering:

- parent directory creation failure
- file write failure
- domain exception translation
- preservation of the original exception cause

Added CLI regression tests covering:

- regression artifact failure exit code
- stderr diagnostic behavior
- artifact failure precedence over an ALLOW result
- artifact failure precedence over a BLOCK result

## Verification

Full test suite:

`628 passed`

`git diff --check` completed without whitespace errors.

## Scope Boundary

Sprint 11.77 applies specifically to the regression result artifact controlled by:

`--regression-result-output`

General JSON and HTML report artifact failures remain outside this sprint.

## Result

Regression CLI artifact persistence now has a deterministic operational failure contract.

A regression run can no longer appear operationally successful when its required regression result artifact cannot be written.