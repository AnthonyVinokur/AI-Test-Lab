# Sprint 11.62 — Define the Candidate Regression Result Adapter Boundary

**Status:** Implemented
**Date:** August 24, 2026

## Summary

Sprint 11.62 defines the adapter boundary between candidate evaluation results produced by the normal CLI execution path and the case-level input required by the regression comparison engine.

The adapter converts:

```text
list[TestResult]
```

into:

```text
tuple[EvaluationRunCaseResult, ...]
```

This closes one of the missing boundaries identified during the Sprint 11.61 CLI regression integration-point discovery.

The sprint does not wire regression processing into the CLI.

## Problem

The normal evaluation workflow returns a mutable list of rich `TestResult` objects.

Each `TestResult` contains considerably more information than the regression comparison engine needs, including:

- Prompt content
- Actual model response
- Assertion details
- Evaluation metrics
- Engine execution results
- Timing measurements
- Token measurements
- Cost measurements
- Provider and model information

The regression comparison engine requires only:

- A stable case identifier
- The final pass/fail outcome

Passing complete `TestResult` objects directly into regression comparison would couple the comparison engine to the normal runtime model and expose unnecessary internal evaluation data across the boundary.

## Goal

Provide one explicit adapter that converts candidate CLI evaluation results into the existing immutable regression case contract.

## Implemented Boundary

The sprint adds:

```python
def adapt_candidate_regression_results(
    results: list[TestResult],
) -> tuple[EvaluationRunCaseResult, ...]:
    ...
```

The adapter accepts the exact collection type returned by `MultiModelRunner.run_tests()` and produces the exact case-result type accepted by `compare_evaluation_runs_for_regression()`.

## Field Mapping

The adapter uses the following explicit mapping:

| Candidate `TestResult` field | Regression field |
|---|---|
| `test_id` | `case_id` |
| `passed` | `passed` |

No other `TestResult` fields cross the adapter boundary.

## Boundary Flow

```text
CLI evaluation execution
        |
        v
list[TestResult]
        |
        v
adapt_candidate_regression_results(...)
        |
        v
tuple[EvaluationRunCaseResult, ...]
        |
        v
Future regression orchestration
```

## Validation

The adapter validates that:

1. The outer collection is a `list`.
2. Every collection member is a `TestResult`.
3. The resulting `case_id` satisfies the existing `EvaluationRunCaseResult` validation.
4. The resulting `passed` value satisfies the existing `EvaluationRunCaseResult` validation.

The adapter reuses the target contract's validation instead of duplicating its rules.

## Deterministic Behavior

The adapter:

- Preserves candidate result order.
- Returns an immutable tuple.
- Returns an empty tuple for an empty candidate result list.
- Performs no sorting.
- Performs no aggregation.
- Performs no serialization.
- Performs no external I/O.

## Multi-Model Boundary

`MultiModelRunner` can combine results from multiple models into one list.

Sprint 11.62 does not create synthetic case identifiers by combining model names with test identifiers. Model identity belongs to evaluation-run provenance, not case identity.

Future regression orchestration is responsible for selecting the results belonging to one provenance-compatible candidate run before invoking this adapter.

If results containing duplicate test identifiers reach the comparison boundary, the existing regression comparison validation rejects them.

## IP-Protection Boundary

The adapter protects internal evaluation details by allowing only the minimum required information to cross into regression comparison:

```text
Internal candidate TestResult
        |
        | explicit transformation
        v
EvaluationRunCaseResult
    - case_id
    - passed
```

The adapter does not expose:

- Prompt text
- Actual responses
- Assertion internals
- Metric configuration
- Metric results
- Engine execution details
- Runtime performance details
- Cost information
- Provider implementation details
- Protected scoring or orchestration logic

## Files Added

```text
src/candidate_regression_result_adapter.py
tests/test_candidate_regression_result_adapter.py
docs/sprints/sprint11.62.md
```

## Test Coverage

Focused tests verify:

1. Candidate results are mapped correctly.
2. Candidate result order is preserved.
3. The output is an immutable tuple.
4. Empty input produces an empty tuple.
5. Non-list input is rejected.
6. Non-`TestResult` members are rejected.
7. Invalid candidate case identifiers are rejected by the target contract.

Focused verification:

```text
6 passed
```

## Explicitly Out of Scope

Sprint 11.62 does not:

- Load a stored baseline.
- Build baseline case results.
- Construct candidate provenance.
- Construct baseline provenance.
- Determine regression eligibility.
- Compare evaluation runs.
- Build `EvaluationRunRegressionResult`.
- Serialize regression results.
- Write the CLI regression output file.
- Decide ALLOW or BLOCK.
- Change CLI exit codes.
- Wire regression execution into `src/cli/app.py`.
- Introduce CI/CD enforcement.
- Introduce schema changes.
- Introduce model-specific synthetic case identifiers.

## Acceptance Criteria

- [x] A dedicated candidate-result adapter exists.
- [x] The adapter accepts `list[TestResult]`.
- [x] The adapter returns `tuple[EvaluationRunCaseResult, ...]`.
- [x] Only `test_id` and `passed` cross the boundary.
- [x] Input order is preserved.
- [x] Empty input produces an empty tuple.
- [x] Invalid outer input is rejected.
- [x] Invalid member input is rejected.
- [x] Target contract validation remains authoritative.
- [x] No baseline or comparison responsibility is added.
- [x] No persistence or CLI wiring is added.
- [x] Focused tests pass without warnings.

## Architectural Result

Sprint 11.62 establishes the following protected seam:

```text
Normal CLI candidate results
        |
        v
Candidate regression result adapter
        |
        v
Regression comparison case contract
```

The regression workflow can now consume candidate evaluation outcomes without depending on the full internal `TestResult` structure.

## Recommended Next Step

A future sprint should define the baseline-result acquisition boundary.

That work should determine how a previously stored compatible evaluation run is loaded and transformed into:

```text
tuple[EvaluationRunCaseResult, ...]
```

It should remain separate from CLI orchestration, comparison execution, public-result construction, persistence, and enforcement.
