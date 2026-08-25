# Sprint 11.66 - Case-Level Regression Decision Boundary

## Status

Completed

## Date

August 24, 2026

## Executive Summary

Sprint 11.66 introduces a dedicated decision boundary for case-level evaluation-run regression evidence.

Sprint 11.65 completed the first regression-run orchestrator. That orchestrator acquires a stored baseline, adapts the current candidate results, verifies that the two runs are eligible for comparison, and produces an immutable `EvaluationRunRegressionComparison`.

The repository already had a run-level regression gate for metric decisions, but case outcomes and metric decisions are different contracts. Sending case-level results through the metric gate would require an invented case-to-metric transformation and would blur the ownership of regression policy.

Sprint 11.66 resolves that gap with a separate case-level gate:

```text
EvaluationRunRegressionComparison
                 |
                 v
evaluate_run_case_regression_gate(...)
                 |
                 v
EvaluationRunCaseRegressionGate
```

The decision is deterministic:

- no compared cases produces `NOT_APPLICABLE`;
- one or more compared cases with no regressions produces `PASS`;
- any regressed case produces `FAIL`.

This sprint does not connect regression processing to the CLI, invent metric evidence, apply enforcement, write public regression JSON, or change process exit codes.

## Goal

Create the smallest explicit boundary that converts an established case-level run comparison into a deterministic, immutable case-level gate result.

The boundary must:

- consume the existing `EvaluationRunRegressionComparison` contract;
- preserve its aggregate case evidence;
- distinguish pass, fail, and not-applicable outcomes;
- remain separate from metric-level regression gating;
- reject invalid input types clearly;
- avoid exposing protected evaluation internals;
- leave all existing CLI behavior unchanged.

## Starting Point

The preceding regression sprints established a staged architecture:

| Sprint | Capability |
|---|---|
| 11.62 | Adapt current `list[TestResult]` into immutable case-level regression inputs |
| 11.63 | Define the baseline regression-result acquisition protocol |
| 11.64 | Acquire baseline case outcomes from a validated stored public report |
| 11.65 | Coordinate baseline acquisition, candidate adaptation, eligibility checking, and case comparison |

After Sprint 11.65, the flow ended here:

```text
Stored baseline report
        |
        v
StoredBaselineRegressionResultAcquirer
        |
        v
AcquiredBaselineRegressionResult
        |
        +------------------------------+
                                       |
Current list[TestResult]               |
        |                              |
        v                              |
adapt_candidate_regression_results()   |
        |                              |
        +------------------------------+
                       |
                       v
EvaluationRunRegressionOrchestrator
                       |
                       v
EvaluationRunRegressionComparison
```

The comparison already contained public-safe aggregate evidence:

```python
baseline_run_id
candidate_run_id
compared_count
unchanged_count
improved_count
regressed_count
case_comparisons
has_regressions
```

What it did not contain was an explicit gate decision.

## Problem Statement

AI Test Lab currently has two distinct regression concepts.

### Metric-level regression

Metric regression evaluates changes in numeric metric values. Its established run-level gate consumes:

```python
tuple[MetricRegressionGateDecision, ...]
```

and returns an `EvaluationRunRegressionGate`.

### Case-level regression

Case-level regression evaluates changes in final Boolean test outcomes:

| Baseline | Candidate | Classification |
|---|---|---|
| Pass | Fail | Regressed |
| Fail | Pass | Improved |
| Pass | Pass | Unchanged |
| Fail | Fail | Unchanged |

This evidence is represented by `EvaluationRunRegressionComparison`.

Metric decisions and case comparisons are not interchangeable. A test changing from pass to fail does not automatically define a numeric metric regression, threshold breach, severity score, or proprietary quality policy.

Without a separate case-level boundary, a future CLI integration would be forced either to invent policy inside `src/cli/app.py` or to disguise case evidence as metric evidence. Both approaches would violate the existing separation of responsibilities.

## Implemented Design

Sprint 11.66 adds:

```text
src/evaluation_run_case_regression_gate.py
```

The module defines three public names:

```python
EvaluationRunCaseRegressionGateDecision
EvaluationRunCaseRegressionGate
evaluate_run_case_regression_gate(...)
```

### Decision enumeration

```python
class EvaluationRunCaseRegressionGateDecision(str, Enum):
    NOT_APPLICABLE = "not_applicable"
    PASS = "pass"
    FAIL = "fail"
```

The string-valued enumeration keeps the decision deterministic and suitable for later explicit serialization without exposing internal policy state.

### Immutable gate result

```python
@dataclass(frozen=True)
class EvaluationRunCaseRegressionGate:
    decision: EvaluationRunCaseRegressionGateDecision
    compared_count: int
    unchanged_count: int
    improved_count: int
    regressed_count: int
```

The gate preserves the aggregate evidence that supports its decision. A caller can determine not only the outcome but also the exact counts on which that outcome was based.

### Evaluation function

```python
def evaluate_run_case_regression_gate(
    comparison: EvaluationRunRegressionComparison,
) -> EvaluationRunCaseRegressionGate:
    ...
```

The function accepts one completed case-level comparison and returns one immutable gate.

## Decision Rules

The decision table is intentionally small:

| Compared cases | Regressed cases | Decision | Meaning |
|---:|---:|---|---|
| `0` | `0` | `NOT_APPLICABLE` | No case evidence exists to evaluate |
| `> 0` | `0` | `PASS` | Compared cases contain no regressions |
| `> 0` | `> 0` | `FAIL` | At least one case regressed |

The implementation applies the rules in this order:

1. If `compared_count == 0`, return `NOT_APPLICABLE`.
2. Otherwise, if `comparison.has_regressions` is true, return `FAIL`.
3. Otherwise, return `PASS`.

## Empty-Comparison Semantics

Sprint 11.65 intentionally preserved the existing ability to compare two empty runs. Two empty case sets are structurally compatible and produce a deterministic comparison with zero counts.

However, a valid empty comparison is not evidence that regression testing passed. No candidate cases were actually evaluated against baseline cases.

Sprint 11.66 therefore classifies an empty comparison as:

```python
NOT_APPLICABLE
```

This avoids a false-positive success claim and aligns with the established metric-gate convention that an empty set of applicable decisions is not applicable.

## Evidence Preservation

The gate copies these aggregate values directly from the established comparison:

- `compared_count`
- `unchanged_count`
- `improved_count`
- `regressed_count`

It does not recalculate the comparison, reclassify cases, modify counts, or inspect individual prompts and responses.

This keeps responsibility with the component that already owns comparison logic:

```python
compare_evaluation_runs_for_regression(...)
```

## Input Validation

The gate accepts only an `EvaluationRunRegressionComparison` instance.

Supplying another object raises:

```python
TypeError(
    "comparison must be an EvaluationRunRegressionComparison"
)
```

The validation provides a clear failure at the boundary instead of allowing an unrelated object to fail later through incidental attribute access.

## Determinism

The same immutable comparison always produces the same immutable gate.

The decision does not depend on:

- current time;
- environment variables;
- file or directory names;
- external services;
- model execution;
- mutable global state;
- hidden configuration;
- implicit baseline selection;
- inferred provenance.

This supports reproducible local runs and future CI/CD quality-gate behavior.

## Immutability

`EvaluationRunCaseRegressionGate` is a frozen dataclass.

After construction, callers cannot change its decision or supporting counts. This prevents a gate from being evaluated under one set of evidence and later presented with altered evidence.

## Responsibility Boundary

The new component owns only:

- interpreting an empty comparison as not applicable;
- interpreting any regression as failure;
- interpreting a non-empty comparison without regressions as pass;
- preserving the established aggregate comparison counts;
- validating the input contract type.

It does not own:

- candidate evaluation;
- candidate-result adaptation;
- baseline discovery, selection, approval, or promotion;
- baseline report loading or validation;
- provenance construction or inference;
- provenance eligibility rules;
- case-set validation;
- duplicate-case detection;
- case-change classification;
- metric comparison;
- tolerance or severity policy;
- enforcement;
- exit-code mapping;
- serialization or persistence;
- CLI orchestration.

## Separation From Metric-Level Gating

The existing metric-level module remains unchanged:

```text
src/evaluation_run_regression_gate.py
```

It continues to aggregate `MetricRegressionGateDecision` values.

The new case-level module is separate:

```text
src/evaluation_run_case_regression_gate.py
```

It consumes only `EvaluationRunRegressionComparison`.

```text
MetricRegressionGateDecision(s)       Case comparison
              |                              |
              v                              v
EvaluationRunRegressionGate     EvaluationRunCaseRegressionGate
```

Neither boundary converts its evidence into the other type. This prevents case outcomes from being falsely represented as metric threshold decisions.

## Public and IP-Protection Boundary

Sprint 11.66 maintains the project's explicit public-versus-private boundary.

The gate uses only the minimum evidence needed for its deterministic decision:

- whether any cases were compared;
- whether any compared case regressed;
- aggregate unchanged, improved, and regressed counts.

It does not expose or process:

- prompts;
- actual model responses;
- expected responses;
- metric scores or explanations;
- evaluator reasoning;
- engine configuration;
- runtime options;
- token usage;
- latency or cost information;
- governance or compliance logic;
- evidence-intelligence logic;
- proprietary scoring;
- internal evaluation orchestration state.

The rule implemented here is a narrow deterministic contract, not a general-purpose commercial scoring or governance system.

## Files Added

```text
src/evaluation_run_case_regression_gate.py
tests/test_evaluation_run_case_regression_gate.py
docs/sprints/sprint11.66.md
```

No existing production files were modified.

## Test Strategy

Sprint 11.66 follows a test-first implementation sequence.

The initial focused test failed during collection with:

```text
ModuleNotFoundError:
No module named 'src.evaluation_run_case_regression_gate'
```

This confirmed that the tests demanded a boundary that did not already exist.

After the smallest production implementation was added, the focused tests verified:

1. A non-empty comparison without regressions produces `PASS`.
2. Any regressed case produces `FAIL`.
3. An empty comparison produces `NOT_APPLICABLE`.
4. Aggregate counts are preserved.
5. The same comparison produces the same gate.
6. The gate result is immutable.
7. A non-comparison input is rejected clearly.

## Verification Results

Focused Sprint 11.66 tests:

```text
6 passed in 0.07s
```

Related regression-boundary tests:

```text
36 passed in 0.23s
```

Complete test suite:

```text
564 passed in 11.32s
```

The complete suite increased from 558 to 564 tests. All six new tests passed, and no existing test regressed.

## Acceptance Criteria

| Acceptance criterion | Result |
|---|---|
| Case-level comparison has a dedicated gate boundary | Passed |
| Metric and case regression concepts remain separate | Passed |
| Empty comparison is not falsely reported as passing | Passed |
| Any regressed case produces `FAIL` | Passed |
| Non-empty comparison without regressions produces `PASS` | Passed |
| Empty comparison produces `NOT_APPLICABLE` | Passed |
| Aggregate evidence is preserved | Passed |
| Invalid input types are rejected clearly | Passed |
| The gate result is immutable | Passed |
| Evaluation is deterministic | Passed |
| Existing metric-gate behavior remains unchanged | Passed |
| Existing CLI behavior remains unchanged | Passed |
| No case-to-metric policy is invented | Passed |
| Protected evaluation internals remain excluded | Passed |
| Focused tests pass | Passed |
| Related regression tests pass | Passed |
| Complete test suite passes | Passed |

## Explicitly Out of Scope

Sprint 11.66 does not implement:

- CLI regression execution;
- CLI provenance arguments;
- automatic provenance construction;
- baseline selection, approval, or promotion;
- case-to-metric conversion;
- new metric regression decisions;
- configurable tolerance;
- regression severity scoring;
- enforcement mapping;
- process exit-code integration;
- regression-result serialization;
- regression-result persistence;
- remote artifact retrieval;
- database storage;
- multi-baseline comparison;
- proprietary governance or scoring policy.

## Architectural Result

The regression path now has an explicit case-level decision stage:

```text
Stored baseline acquisition
          +
Current candidate adaptation
          |
          v
EvaluationRunRegressionOrchestrator
          |
          v
EvaluationRunRegressionComparison
          |
          v
evaluate_run_case_regression_gate(...)
          |
          v
EvaluationRunCaseRegressionGate
```

The next integration layer can consume this approved case-level gate without manufacturing decisions inside the CLI and without routing case evidence through the metric-level gate.

## Result

AI Test Lab now has a clear, deterministic, and immutable decision boundary for case-level regression evidence.

A completed evaluation-run comparison can be classified as `PASS`, `FAIL`, or `NOT_APPLICABLE` while preserving its supporting aggregate counts. Case outcomes remain separate from metric decisions, empty comparisons are represented honestly, and protected evaluation internals remain outside the public decision boundary.

Sprint 11.66 closes the immediate architectural gap after regression-run orchestration and prepares the project for a later, deliberately scoped enforcement or CLI-integration increment.
