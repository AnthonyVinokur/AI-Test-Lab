# Sprint 11.61 - Discover the Regression CLI Integration Point

## Objective

Identify and document the smallest safe integration point through which the
normal CLI can eventually persist an approved public
`EvaluationRunRegressionResult`.

This is a discovery-only sprint. It does not add runtime regression
orchestration or change existing CLI behavior.

## Starting Point

Sprint 11.59 added the CLI-owned persistence seam:

```text
write_cli_regression_result(result, output_path)
```

Sprint 11.60 added the optional destination argument:

```text
--regression-result-output PATH
```

The remaining question was where these contracts should eventually connect to
the normal CLI execution flow.

## Current CLI Execution Flow

The normal evaluation path is implemented in:

```text
src/cli/app.py
```

Its runtime flow is:

```text
parse CLI arguments
        ↓
load evaluation profile
        ↓
load test cases
        ↓
MultiModelRunner.run_tests(...)
        ↓
list[TestResult]
        ↓
write normal JSON report
        ↓
write normal HTML report
        ↓
print result summary
        ↓
return ordinary evaluation exit code
```

The runner returns:

```python
list[TestResult]
```

It does not return an `EvaluationRunRegressionResult` or another run-level
regression contract.

## Discovered Integration Anchor

The future regression invocation belongs in `src/cli/app.py` after the normal
reports have been written and before the existing result summary and final exit
code are calculated:

```python
results = runner.run_tests(test_cases)

JsonReporter(args.report).write(results)
HtmlReporter(args.html_report).write(results)

# Future regression integration anchor.

(
    _,
    _,
    unexpected_failures,
    errors,
) = print_results(results)
```

This is an invocation anchor, not a location for implementing protected
regression policy.

## Why This Location Is Appropriate

At this location:

- candidate evaluation execution is complete
- normal JSON evidence has been written
- normal HTML evidence has been written
- the CLI still controls its final exit code
- the optional regression output path is available
- a future approved public regression result can be passed to the existing
  persistence seam

Writing the normal reports first also ensures that diagnostic evidence remains
available if regression enforcement eventually blocks the CLI run.

## Current Regression Comparison Contract

Regression comparison is implemented by:

```text
compare_evaluation_runs_for_regression(...)
```

It requires:

```python
baseline: EvaluationRunProvenance
candidate: EvaluationRunProvenance
baseline_results: tuple[EvaluationRunCaseResult, ...]
candidate_results: tuple[EvaluationRunCaseResult, ...]
```

It returns:

```python
EvaluationRunRegressionComparison
```

No `EvaluationRunSnapshot` or `EvaluationRunSummary` contract currently exists.

## Missing Inputs

The normal CLI currently provides only:

```python
list[TestResult]
```

It does not provide:

- baseline `EvaluationRunProvenance`
- candidate `EvaluationRunProvenance`
- baseline `EvaluationRunCaseResult` objects
- an explicit `TestResult` to `EvaluationRunCaseResult` adapter
- baseline selection or loading
- regression comparison orchestration
- regression gate orchestration
- regression enforcement orchestration
- an approved public `EvaluationRunRegressionResult`

Therefore, the parsed output path cannot yet be connected safely to
`write_cli_regression_result(...)`.

## Required Future Boundary

The CLI application must not directly manufacture regression decisions.

The intended future boundary is:

```text
Normal CLI evaluation results
             ↓
Protected regression orchestration
             ↓
Approved EvaluationRunRegressionResult
========================================
Public CLI boundary
             ↓
write_cli_regression_result(...)
             ↓
--regression-result-output
             ↓
Deterministic public JSON
```

Only the final approved public result should cross into the CLI persistence
seam.

## Public / Private Boundary

`src/cli/app.py` may eventually:

- recognize that regression output was requested
- invoke a deliberately defined regression workflow
- receive an approved `EvaluationRunRegressionResult`
- persist that result through `write_cli_regression_result(...)`
- apply its public exit-code contract

It should not directly own:

- baseline selection policy
- provenance construction policy
- comparison policy
- tolerance policy
- severity classification
- gate decision construction
- enforcement decision construction
- proprietary scoring or governance logic

## Silent Argument Behavior

The CLI currently accepts:

```text
--regression-result-output PATH
```

but `src/cli/app.py` does not read the parsed value.

Therefore, supplying the argument currently:

- does not write a regression file
- does not run regression comparison
- does not change the CLI exit code
- does not raise an error

This behavior is intentional preparation from Sprint 11.60, but it must not be
mistaken for completed regression execution support.

## Decision

Sprint 11.61 identifies:

```text
src/cli/app.py
```

as the owner of the future invocation point.

The specific anchor is:

```text
after normal JSON and HTML report persistence
before result-summary and final exit-code calculation
```

Regression-result production must remain outside `app.main()` behind a
deliberately defined orchestration boundary.

## Files Inspected

```text
src/cli/app.py
src/cli/arguments.py
src/cli/execution.py
src/cli/regression_output.py
src/multi_model_runner.py
src/evaluation_run_regression_comparison.py
docs/sprints/sprint11.60.md
```

## Production Changes

None.

No source files or tests are modified in this discovery sprint.

## Explicitly Out of Scope

Sprint 11.61 does not add:

- regression runtime wiring
- a baseline CLI argument
- baseline loading
- provenance construction
- conversion from `TestResult` to `EvaluationRunCaseResult`
- comparison orchestration
- gate orchestration
- enforcement construction
- regression-result construction
- regression exit-code precedence
- unconditional file creation
- public schema changes
- CI/CD integration

## Acceptance Criteria

- The current CLI execution path is documented.
- The future invocation anchor is identified precisely.
- Existing runner output is identified as `list[TestResult]`.
- Existing regression comparison inputs are documented.
- Missing orchestration inputs are documented.
- The public/private boundary remains intact.
- No runtime behavior changes.
- No regression artifact is manufactured by `app.main()`.

## Recommended Next Slice

The next sprint should define one narrow input boundary required by regression
orchestration before wiring the CLI.

A suitable next slice is discovery and definition of the candidate-result
adapter boundary:

```text
list[TestResult]
        ↓
explicit public-safe transformation
        ↓
tuple[EvaluationRunCaseResult, ...]
```

Baseline selection, provenance construction, comparison orchestration, and
enforcement should remain separate slices.

## Result

Sprint 11.61 establishes the exact future CLI invocation anchor without
prematurely connecting incomplete regression processing:

```text
normal evaluation completed
        ↓
normal reports persisted
        ↓
future protected regression workflow
        ↓
approved public result
        ↓
existing CLI persistence seam
        ↓
final CLI exit decision
```
