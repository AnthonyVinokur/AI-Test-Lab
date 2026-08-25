# Sprint 11.68 — Case-Level Regression Execution Composition

## Status

Completed

## Goal

Sprint 11.68 composes the existing case-level regression runtime layers
into one stable application-level operation.

The sprint answers one question:

```text
How can a caller execute the complete approved case-level regression
decision chain without coordinating each domain operation itself?
```

The new composition is:

```text
EvaluationRunRegressionOrchestrator.compare()
        ↓
evaluate_run_case_regression_gate()
        ↓
enforce_evaluation_run_case_regression_gate()
```

The operation returns the existing immutable comparison, gate, and
enforcement contracts.

## Background

Sprint 11.62 introduced candidate evaluation-result adaptation.

Sprint 11.63 defined the baseline acquisition boundary.

Sprint 11.64 implemented baseline acquisition from a stored, validated
public report.

Sprint 11.65 introduced regression orchestration.

Sprint 11.66 converted case-level comparison evidence into a
deterministic regression gate.

Sprint 11.67 mapped the case-level gate to the existing enforcement
contract.

Sprint 11.68 composes those approved layers into one application-level
execution operation.

## Architectural Flow

The completed case-level regression application flow is:

```text
Stored public baseline report
        ↓
StoredBaselineRegressionResultAcquirer
        ↓
EvaluationRunRegressionOrchestrator.compare()
        ↓
EvaluationRunRegressionComparison
        ↓
evaluate_run_case_regression_gate()
        ↓
EvaluationRunCaseRegressionGate
        ↓
enforce_evaluation_run_case_regression_gate()
        ↓
EvaluationRunRegressionEnforcement
```

A caller no longer needs to coordinate the comparison, gate, and
enforcement operations independently.

## New Execution Contract

Sprint 11.68 introduces:

```python
@dataclass(frozen=True)
class EvaluationRunCaseRegressionExecution:
    comparison: EvaluationRunRegressionComparison
    gate: EvaluationRunCaseRegressionGate
    enforcement: EvaluationRunRegressionEnforcement
```

The contract preserves all three approved outputs:

```text
comparison evidence
gate decision
enforcement decision
```

It does not flatten or transform the evidence.

## New Execution Function

Sprint 11.68 introduces:

```python
def execute_evaluation_run_case_regression(
    orchestrator: EvaluationRunRegressionOrchestrator,
    candidate_results: list[TestResult],
) -> EvaluationRunCaseRegressionExecution:
```

The function performs these steps:

1. Validate the supplied orchestrator.
2. Ask the orchestrator to compare the baseline and candidate runs.
3. Evaluate the case-level regression gate.
4. Enforce the gate.
5. Return one immutable execution result containing all three contracts.

## Decision Behavior

The composed behavior remains deterministic:

| Comparison outcome | Gate | Enforcement |
|---|---|---|
| No regressed cases | `PASS` | `ALLOW` |
| One or more regressed cases | `FAIL` | `BLOCK` |
| No compared cases | `NOT_APPLICABLE` | `ALLOW` |

Sprint 11.68 does not introduce new decision semantics.

It only composes the decisions established in earlier sprints.

## Evidence Preservation

The execution result preserves the original case-level comparison.

This allows downstream consumers to access:

```text
baseline run ID
candidate run ID
compared count
unchanged count
improved count
regressed count
case comparisons
gate decision
enforcement decision
```

The execution boundary does not convert case-level evidence into
metric-level evidence.

## Type Validation

The execution function explicitly requires an:

```text
EvaluationRunRegressionOrchestrator
```

Invalid input raises:

```text
TypeError
```

with the stable message:

```text
orchestrator must be an EvaluationRunRegressionOrchestrator
```

Candidate-result validation remains owned by the existing candidate
adapter reached through the orchestrator.

The composition layer does not duplicate that validation.

## Error Propagation

Existing failures propagate unchanged through the composition boundary.

Examples include:

```text
baseline acquisition failure
candidate adaptation failure
ineligible provenance
mismatched case sets
duplicate case identifiers
```

Sprint 11.68 does not hide, translate, or replace those errors.

This preserves the established responsibilities of the underlying
components.

## Determinism

The same:

```text
baseline
candidate provenance
candidate results
```

produces the same:

```text
comparison
gate
enforcement
```

The composition adds no randomness, time dependency, environment
dependency, or mutable configuration.

## Immutability

`EvaluationRunCaseRegressionExecution` is a frozen dataclass.

The returned:

```text
comparison
gate
enforcement
```

references cannot be replaced after construction.

The contained contracts are also existing immutable dataclasses.

## Separation of Responsibilities

Each layer continues to own one responsibility:

| Layer | Responsibility |
|---|---|
| Baseline acquirer | Load approved baseline inputs |
| Candidate adapter | Convert candidate CLI results |
| Orchestrator | Acquire, adapt, and compare |
| Case-level gate | Convert comparison evidence into `PASS`, `FAIL`, or `NOT_APPLICABLE` |
| Enforcement | Convert the gate into `ALLOW` or `BLOCK` |
| Execution composition | Invoke the approved layers in order |

The composition layer contains no comparison or policy logic of its own.

## CLI Boundary

Sprint 11.68 does not modify the CLI.

Instead, it gives a future CLI integration one stable operation:

```text
CLI
 ↓
execute_evaluation_run_case_regression(...)
```

This prevents the CLI presentation layer from coordinating several
domain services directly.

Process exit codes, console presentation, persistence, and command-line
activation remain later integration work.

## Public and IP Protection Boundary

The composition uses only previously approved contracts.

It does not expose:

```text
prompts
model responses
expected responses
metric scores
metric thresholds
runtime provider configuration
governance rules
proprietary scoring logic
evidence-intelligence logic
internal mutable orchestration state
```

No new public serialization contract is introduced.

No internal model is automatically serialized.

The established AI Test Lab IP-protection boundary remains intact.

## Files Changed

### Production

```text
src/evaluation_run_case_regression_execution.py
```

Added:

```text
EvaluationRunCaseRegressionExecution
execute_evaluation_run_case_regression()
orchestrator type validation
comparison → gate → enforcement composition
```

### Tests

```text
tests/test_evaluation_run_case_regression_execution.py
```

Added six focused tests.

### Documentation

```text
docs/sprints/sprint11.68.md
```

Documents the application-level composition boundary.

## Test Coverage

Sprint 11.68 verifies:

1. A passing comparison produces `PASS` and `ALLOW`.
2. A regression produces `FAIL` and `BLOCK`.
3. An empty comparison produces `NOT_APPLICABLE` and `ALLOW`.
4. The execution result is immutable.
5. An invalid orchestrator is rejected.
6. Existing orchestration failures propagate unchanged.

## Verification

Focused execution tests:

```text
6 passed
```

Related case-level regression chain:

```text
63 passed
```

Complete project suite:

```text
576 passed
```

Diff validation:

```text
git diff --check
```

Result:

```text
clean
```

## Explicitly Out of Scope

Sprint 11.68 does not add or change:

- CLI regression execution
- CLI arguments
- console presentation
- process termination
- runtime exit-code integration
- regression-result construction
- JSON serialization
- report persistence
- baseline selection
- baseline approval
- baseline promotion
- remote or database baseline storage
- multi-baseline comparison
- tolerance policy
- severity policy
- metric-level regression policy
- case-to-metric transformation
- protected evaluation internals

## Completion Criteria

Sprint 11.68 is complete when:

- orchestration, gating, and enforcement are composed;
- comparison evidence is preserved;
- gate evidence is preserved;
- enforcement evidence is preserved;
- invalid orchestrator input is rejected;
- underlying errors propagate unchanged;
- the result is immutable;
- existing regression behavior remains compatible;
- focused, related, and complete test suites pass;
- documentation records the boundary.

All completion criteria are satisfied.

## Recommended Next Slice

The next narrow sprint should connect the new application-level
execution operation to the previously identified CLI anchor.

That later integration may compose:

```text
execute_evaluation_run_case_regression(...)
        ↓
existing regression-result construction
        ↓
existing exit-code mapping
```

The next sprint should first inspect the current CLI activation and
baseline-selection inputs before changing runtime behavior.

It should not broaden regression policy, comparison semantics, or public
report exposure.