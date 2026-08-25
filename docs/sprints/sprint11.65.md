# Sprint 11.65 — Regression Run Orchestration

## Status

Completed

## Date

August 24, 2026

## Goal

Implement the first narrow orchestration boundary that combines stored baseline acquisition with current candidate-result adaptation and performs an eligible, deterministic case-level regression comparison.

## Executive Summary

Sprint 11.65 connects three regression capabilities that were already implemented and tested independently:

1. Stored baseline acquisition
2. Current candidate-result adaptation
3. Baseline-versus-candidate case comparison

The new `EvaluationRunRegressionOrchestrator` coordinates these existing contracts without duplicating their rules or exposing protected evaluation internals.

The orchestrator deliberately stops after producing an `EvaluationRunRegressionComparison`. It does not invent a conversion from case-level changes to metric-level gate decisions, and it does not connect regression behavior to the CLI prematurely.

## Background

The preceding sprints established the required input boundaries:

- Sprint 11.62 introduced `adapt_candidate_regression_results()`.
- Sprint 11.63 defined `BaselineRegressionResultAcquirer` and `AcquiredBaselineRegressionResult`.
- Sprint 11.64 implemented `StoredBaselineRegressionResultAcquirer` for validated public reports.

Before Sprint 11.65, these components existed independently. No single component coordinated them into an actual baseline-versus-candidate comparison.

## Problem

A regression comparison requires two compatible runs:

- a previously identified baseline run;
- a current candidate run.

Each run must provide:

- explicit `EvaluationRunProvenance`;
- immutable case identities;
- final Boolean pass/fail outcomes.

The project needed a small coordination layer that could prepare these inputs and invoke the established comparison boundary without assuming responsibility for acquisition rules, adaptation rules, eligibility policy, comparison logic, metric gates, enforcement, or CLI behavior.

## Implemented Design

Sprint 11.65 added:

```text
src/evaluation_run_regression_orchestrator.py
```

The module provides:

```python
EvaluationRunRegressionOrchestrator
```

The orchestrator is constructed with:

```python
baseline_acquirer: BaselineRegressionResultAcquirer
candidate_provenance: EvaluationRunProvenance
```

Its public operation is:

```python
compare(
    candidate_results: list[TestResult],
) -> EvaluationRunRegressionComparison
```

## Processing Sequence

The `compare()` method performs four operations:

1. Calls the supplied baseline acquirer exactly once.
2. Adapts the current candidate `TestResult` objects through the existing candidate adapter.
3. Supplies both explicit provenance records and both immutable result tuples to the existing comparison function.
4. Returns the resulting immutable `EvaluationRunRegressionComparison`.

## Data Flow

```text
Stored public baseline report
            |
            v
BaselineRegressionResultAcquirer.acquire()
            |
            v
AcquiredBaselineRegressionResult
  - explicit baseline provenance
  - immutable baseline case results
            |
            +-------------------------------+
                                            |
Current list[TestResult]                    |
            |                               |
            v                               |
adapt_candidate_regression_results()        |
            |                               |
            v                               v
immutable candidate case results + explicit candidate provenance
                            |
                            v
compare_evaluation_runs_for_regression()
                            |
                            v
EvaluationRunRegressionComparison
```

## Responsibility Boundary

The orchestrator coordinates existing components only.

It does not implement:

- baseline reading or validation;
- baseline selection or approval;
- candidate evaluation;
- candidate-result conversion rules;
- provenance inference;
- provenance compatibility policy;
- case-set validation;
- duplicate detection;
- regression classification rules;
- metric scoring;
- gate policy;
- enforcement policy;
- serialization or persistence;
- CLI output or process exit behavior.

Every established responsibility remains with its existing component.

## Existing Contracts Reused

### Baseline acquisition

```python
BaselineRegressionResultAcquirer.acquire()
```

The acquirer returns:

```python
AcquiredBaselineRegressionResult(
    provenance=...,
    case_results=...,
)
```

The orchestrator does not know whether the baseline came from a local public report, remote artifact service, database, or another future implementation.

### Candidate adaptation

```python
adapt_candidate_regression_results(candidate_results)
```

The adapter converts only:

| Candidate field | Regression field |
|---|---|
| `test_id` | `case_id` |
| `passed` | `passed` |

### Eligibility and comparison

```python
compare_evaluation_runs_for_regression(...)
```

The existing comparison boundary remains responsible for:

- provenance eligibility;
- exact case-set matching;
- duplicate case rejection;
- deterministic case ordering;
- unchanged classification;
- improved classification;
- regressed classification;
- aggregate comparison counts.

## Provenance Decision

Baseline provenance comes from the baseline acquirer.

Candidate provenance must be supplied explicitly when the orchestrator is constructed.

The orchestrator does not infer, reconstruct, or fabricate provenance from:

- candidate results;
- report fields;
- model configuration;
- dataset configuration;
- file paths or file names;
- environment variables;
- runtime state.

This preserves deterministic eligibility checking and prevents unrelated runs from being silently paired.

Invalid candidate provenance is rejected during orchestrator construction.

## Empty Run Behavior

The baseline acquirer and candidate adapter preserve empty result collections as empty tuples.

The established comparison contract allows two empty case sets to be compared deterministically. The resulting comparison contains:

```python
compared_count == 0
case_comparisons == ()
```

Sprint 11.65 preserves this existing behavior instead of introducing a new empty-run policy.

If only one side contains cases, the existing comparison boundary rejects the mismatched case sets.

## Failure Behavior

The orchestrator deliberately allows established domain failures to propagate.

This includes:

- baseline acquisition failures;
- report-reading or report-validation failures;
- candidate adaptation failures;
- invalid candidate objects;
- invalid case identifiers;
- ineligible provenance;
- mismatched case sets;
- duplicate case identities.

The orchestrator does not catch, hide, reclassify, or replace these failures. This keeps failures visible and preserves the behavior of the owning boundary.

## Case Comparison Versus Metric Gate

The repository currently contains two distinct regression concepts:

### Case-level run comparison

The run-comparison boundary produces:

```python
EvaluationRunRegressionComparison
```

This object describes whether individual test cases are unchanged, improved, or regressed.

### Metric-level regression gate

The run-gate boundary consumes:

```python
tuple[MetricRegressionGateDecision, ...]
```

This object aggregates already-established metric decisions into a run-level gate outcome.

There is currently no approved public transformation from case-level comparisons to metric-level decisions.

Sprint 11.65 therefore stops at `EvaluationRunRegressionComparison`. Connecting the two boundaries in this sprint would require inventing new scoring or policy behavior without an established contract.

## Immutability

The new orchestrator is a frozen dataclass.

The coordinated regression flow also relies on immutable domain structures:

- `EvaluationRunProvenance`
- `AcquiredBaselineRegressionResult`
- `tuple[EvaluationRunCaseResult, ...]`
- `EvaluationRunRegressionComparison`
- `tuple[EvaluationRunCaseComparison, ...]`

This prevents run identity, case outcomes, and comparison evidence from being mutated during orchestration.

## IP Protection Boundary

Sprint 11.65 preserves the established public-versus-private architecture boundary.

Only the minimum data required for deterministic case-level regression comparison crosses the orchestration boundary:

- explicit baseline provenance;
- explicit candidate provenance;
- case identity;
- final pass/fail outcome.

The orchestrator does not expose or transport:

- prompts;
- actual model responses;
- expected responses;
- metric scores or reasons;
- engine configuration;
- runtime options;
- token usage;
- latency or cost details;
- governance logic;
- evidence intelligence;
- proprietary scoring logic;
- internal evaluation orchestration state.

The component coordinates stable contracts without turning protected implementation details into public regression inputs.

## Files Added

```text
src/evaluation_run_regression_orchestrator.py
tests/test_evaluation_run_regression_orchestrator.py
docs/sprints/sprint11.65.md
```

## Existing Components Reused

```text
src/baseline_regression_result_acquirer.py
src/candidate_regression_result_adapter.py
src/evaluation_run_provenance.py
src/evaluation_run_regression_comparison.py
src/models.py
```

## Test Coverage

The focused Sprint 11.65 tests verify that:

1. The baseline is acquired exactly once.
2. Candidate results are adapted and compared.
3. Baseline provenance reaches the comparison boundary.
4. Candidate provenance reaches the comparison boundary.
5. A pass-to-fail change is classified as regressed.
6. Empty baseline and candidate runs remain comparable.
7. Baseline acquisition failures propagate unchanged.
8. Ineligible provenance failures propagate unchanged.
9. Candidate adaptation failures propagate unchanged.
10. Invalid candidate provenance is rejected.

## Verification Results

Focused Sprint 11.65 tests:

```text
6 passed in 0.09s
```

Related regression-boundary tests:

```text
32 passed in 0.40s
```

Complete test suite:

```text
558 passed in 12.45s
```

No warnings were produced during the final verification runs.

## Acceptance Criteria

| Acceptance criterion | Result |
|---|---|
| Baseline acquisition uses the established protocol | Passed |
| Candidate adaptation uses the established adapter | Passed |
| Baseline is acquired exactly once | Passed |
| Baseline and candidate provenance remain explicit | Passed |
| Existing eligibility rules are reused | Passed |
| Existing comparison rules are reused | Passed |
| Empty runs preserve established behavior | Passed |
| Dependency and domain failures remain visible | Passed |
| No case-to-metric policy is invented | Passed |
| Protected internal data remains excluded | Passed |
| Focused tests pass | Passed |
| Related regression tests pass | Passed |
| Complete test suite passes | Passed |

## Out of Scope

Sprint 11.65 does not implement:

- CLI regression execution;
- CLI regression output;
- CLI exit-code integration;
- regression-result persistence;
- baseline selection;
- baseline approval or promotion;
- automatic provenance construction;
- case-to-metric transformation;
- new metric regression decisions;
- new gate or enforcement policy;
- remote artifact retrieval;
- database persistence;
- multi-baseline comparison.

## Result

AI Test Lab now has its first focused regression-run orchestration boundary.

A previously stored baseline and a current candidate evaluation can be prepared and compared through existing deterministic contracts without duplicating policy, inferring provenance, exposing protected internals, or coupling the comparison prematurely to metric gates or the CLI.

This completes the missing connection between baseline acquisition, candidate adaptation, and case-level regression comparison while preserving the project’s quality, reproducibility, and IP-protection boundaries.
