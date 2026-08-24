# Sprint 11.63 — Define the Baseline Regression Result Acquisition Boundary

**Status:** Implemented  
**Date:** August 24, 2026

## Summary

Sprint 11.63 defines the boundary through which future regression orchestration
can acquire the inputs belonging to one previously identified baseline
evaluation run.

The boundary groups:

```text
EvaluationRunProvenance
+
tuple[EvaluationRunCaseResult, ...]
```

into one immutable acquisition result.

The sprint also defines a storage-neutral protocol that future baseline
implementations can satisfy.

No baseline storage implementation or CLI integration is added.

## Starting Point

Sprint 11.61 discovered the future regression integration point in:

```text
src/cli/app.py
```

Sprint 11.62 added the candidate-result adapter:

```text
list[TestResult]
        |
        v
tuple[EvaluationRunCaseResult, ...]
```

The remaining baseline-side requirement was a clear boundary for acquiring:

```python
baseline: EvaluationRunProvenance
baseline_results: tuple[EvaluationRunCaseResult, ...]
```

## Problem

The regression comparator requires both baseline provenance and baseline case
results.

Passing these as unrelated values from a storage implementation could allow
them to become separated or incorrectly combined.

Regression orchestration must also remain independent of whether a future
baseline comes from:

- A local file
- A CI artifact
- Object storage
- A database
- Another approved evaluation-run repository

## Implemented Acquisition Result

The sprint adds:

```python
@dataclass(frozen=True)
class AcquiredBaselineRegressionResult:
    provenance: EvaluationRunProvenance
    case_results: tuple[EvaluationRunCaseResult, ...]
```

This immutable object keeps baseline identity and baseline outcomes together.

## Implemented Protocol

The sprint also adds:

```python
class BaselineRegressionResultAcquirer(Protocol):
    def acquire(self) -> AcquiredBaselineRegressionResult:
        ...
```

Future implementations can configure their source during construction while
presenting the same acquisition method to regression orchestration.

Examples of possible future implementations include:

```python
JsonBaselineRegressionResultAcquirer(path)
DatabaseBaselineRegressionResultAcquirer(run_id)
```

These implementations are not part of Sprint 11.63.

## Boundary Flow

```text
Previously identified baseline source
        |
        v
Concrete acquirer — future
        |
        v
BaselineRegressionResultAcquirer.acquire()
        |
        v
AcquiredBaselineRegressionResult
        |
        +-- provenance
        |
        +-- case_results
        |
        v
Future regression orchestration
```

## Validation

`AcquiredBaselineRegressionResult` verifies that:

1. `provenance` is an `EvaluationRunProvenance`.
2. `case_results` is an immutable tuple.
3. Every tuple member is an `EvaluationRunCaseResult`.

The existing nested contracts remain responsible for validating their own
fields.

## Validation Ownership

This acquisition boundary validates structural integrity only.

It does not determine:

- Whether the baseline is approved
- Whether the baseline is compatible with a candidate
- Whether case identifiers match candidate case identifiers
- Whether case identifiers are duplicated
- Whether an empty run should be accepted by a workflow
- Whether a regression occurred
- Whether execution should be allowed or blocked

Those responsibilities remain with selection, comparison, eligibility, gate,
and enforcement layers.

## Empty Baseline Behavior

The acquisition result permits an empty case-result tuple.

The acquisition boundary does not introduce a policy requiring a minimum
number of cases. A future orchestration or policy layer may establish that
requirement if necessary.

## Source-Neutral Design

The protocol does not accept a path, database identifier, or storage URI.

Storage-specific information belongs to concrete acquirer construction rather
than the core acquisition method.

This prevents the regression orchestration boundary from becoming coupled to
one storage technology.

## IP-Protection Boundary

The acquisition contract exposes only the minimum baseline information
required by the existing regression comparator:

- Reproducibility provenance
- Stable case identifiers
- Final pass/fail outcomes

It does not expose:

- Prompt text
- Model responses
- Assertion internals
- Metric configuration
- Metric results
- Engine details
- Timing or token measurements
- Cost information
- Baseline selection rules
- Approval logic
- Governance policy
- Proprietary scoring or orchestration logic

Baseline selection and approval remain protected future capabilities.

## Files Added

```text
src/baseline_regression_result_acquirer.py
tests/test_baseline_regression_result_acquirer.py
docs/sprints/sprint11.63.md
```

## Test Coverage

Focused tests verify:

1. Provenance and case results are grouped correctly.
2. The acquisition result is immutable.
3. Empty case results are preserved.
4. Invalid provenance is rejected.
5. Non-tuple case results are rejected.
6. Invalid tuple members are rejected.
7. A structural acquirer satisfies the protocol contract.

Focused verification:

```text
7 passed in 0.07s
```

Full regression verification:

```text
545 passed in 11.12s
```

## Explicitly Out of Scope

Sprint 11.63 does not:

- Read a baseline JSON file.
- Define a baseline JSON schema.
- Deserialize stored results.
- Add a baseline CLI argument.
- Select or approve a baseline.
- Construct candidate provenance.
- Compare evaluation runs.
- Build a regression gate.
- Build an enforcement decision.
- Build an `EvaluationRunRegressionResult`.
- Write a regression output artifact.
- Change CLI exit codes.
- Wire regression execution into `src/cli/app.py`.
- Introduce CI/CD enforcement.

## Acceptance Criteria

- [x] Baseline provenance and case results are grouped.
- [x] The acquisition result is immutable.
- [x] The acquisition boundary is storage-neutral.
- [x] Structural validation is explicit.
- [x] Existing nested validation remains authoritative.
- [x] Selection and approval policies remain outside the boundary.
- [x] Comparison and enforcement remain outside the boundary.
- [x] No CLI behavior changes.
- [x] Focused tests pass.
- [x] The complete test suite passes.

## Architectural Result

Sprint 11.63 establishes the baseline-side seam:

```text
Future baseline implementation
        |
        v
Baseline regression result acquisition boundary
        |
        v
Provenance + immutable case results
        |
        v
Future protected regression orchestration
```

The regression workflow can now depend on a stable baseline acquisition
contract without depending on filesystem, database, CI, or cloud-storage
details.

## Recommended Next Step

The next sprint should define the first concrete baseline acquisition
implementation.

A suitable narrow slice is:

```text
stored baseline evaluation artifact
        |
        v
strict deserialization and validation
        |
        v
AcquiredBaselineRegressionResult
```

That implementation should remain separate from baseline selection, CLI
wiring, comparison orchestration, gating, and enforcement.
