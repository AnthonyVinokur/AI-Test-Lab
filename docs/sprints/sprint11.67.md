# Sprint 11.67 — Case-Level Regression Enforcement

## Status

Completed

## Goal

Sprint 11.67 connects the case-level regression gate introduced in
Sprint 11.66 to the existing evaluation-run regression enforcement
contract.

The sprint answers one question:

```text
Should execution be allowed or blocked based on the case-level gate?
```

The sprint reuses the established enforcement decisions:

```text
ALLOW
BLOCK
```

It does not create a second enforcement model.

## Background

Sprint 11.62 introduced the candidate regression-result adapter.

Sprint 11.63 defined the baseline regression-result acquisition
boundary.

Sprint 11.64 implemented acquisition from a stored, validated public
report.

Sprint 11.65 introduced orchestration for:

```text
baseline acquisition
        ↓
candidate adaptation
        ↓
regression eligibility
        ↓
case-level comparison
```

Sprint 11.66 converted the comparison into a deterministic case-level
gate:

```text
EvaluationRunRegressionComparison
        ↓
EvaluationRunCaseRegressionGate
```

The gate produces one of three decisions:

```text
PASS
FAIL
NOT_APPLICABLE
```

Sprint 11.67 adds the next policy boundary:

```text
EvaluationRunCaseRegressionGate
        ↓
EvaluationRunRegressionEnforcement
```

## Enforcement Mapping

The mapping is deterministic:

| Case-level gate decision | Enforcement decision |
|---|---|
| `PASS` | `ALLOW` |
| `FAIL` | `BLOCK` |
| `NOT_APPLICABLE` | `ALLOW` |

A failed regression gate blocks execution.

A passing gate allows execution.

A gate that is not applicable also allows execution because no
regression failure was established.

## Existing Enforcement Contract

The project already had an immutable enforcement contract from the
earlier metric-level regression path:

```python
class EvaluationRunRegressionEnforcementDecision(str, Enum):
    ALLOW = "allow"
    BLOCK = "block"


@dataclass(frozen=True)
class EvaluationRunRegressionEnforcement:
    decision: EvaluationRunRegressionEnforcementDecision
```

Sprint 11.67 deliberately reuses this contract.

This preserves one authoritative representation for downstream
enforcement consumers such as:

```text
exit-code mapping
result construction
serialization
CLI output
CI/CD quality gates
```

## New Enforcement Function

Sprint 11.67 introduces:

```python
enforce_evaluation_run_case_regression_gate(...)
```

Contract:

```python
def enforce_evaluation_run_case_regression_gate(
    gate: EvaluationRunCaseRegressionGate,
) -> EvaluationRunRegressionEnforcement:
```

The function accepts only an:

```text
EvaluationRunCaseRegressionGate
```

and returns the existing:

```text
EvaluationRunRegressionEnforcement
```

## Type Validation

The new enforcement boundary performs explicit runtime validation.

A value that is not an `EvaluationRunCaseRegressionGate` raises:

```text
TypeError
```

with the stable message:

```text
gate must be an EvaluationRunCaseRegressionGate
```

This prevents unrelated objects from silently crossing the enforcement
boundary.

## Architectural Flow

After Sprint 11.67, the case-level regression path is:

```text
Stored public baseline report
        ↓
StoredBaselineRegressionResultAcquirer
        ↓
EvaluationRunRegressionOrchestrator
        ↓
EvaluationRunRegressionComparison
        ↓
EvaluationRunCaseRegressionGate
        ↓
EvaluationRunRegressionEnforcement
```

The new path stops at the enforcement decision.

It does not yet invoke process exit-code behavior or CLI behavior.

## Metric-Level Compatibility

The project already contains a separate metric-level regression path:

```text
Metric regression decisions
        ↓
EvaluationRunRegressionGate
        ↓
EvaluationRunRegressionEnforcement
```

Sprint 11.67 does not replace or modify that path.

The existing function remains unchanged:

```python
enforce_evaluation_run_regression_gate(...)
```

The two paths now share the same final enforcement contract:

```text
Case-level gate ────┐
                    ├── EvaluationRunRegressionEnforcement
Metric-level gate ──┘
```

They do not share or convert their underlying evidence.

Case-level evidence remains case-level.

Metric-level evidence remains metric-level.

## Public and IP Protection Boundary

Only minimal public-safe regression information crosses this boundary:

```text
gate decision
enforcement decision
```

The enforcement layer does not expose:

```text
prompts
model responses
expected responses
metric scores
metric thresholds
runtime configuration
provider details
governance rules
proprietary scoring logic
internal orchestration state
```

The change therefore preserves the established AI Test Lab IP
protection boundary.

## Determinism

The same case-level gate always produces the same enforcement result.

Examples:

```text
FAIL → BLOCK
FAIL → BLOCK
```

and:

```text
PASS → ALLOW
PASS → ALLOW
```

No time, randomness, external service, environment state, or mutable
configuration affects the mapping.

## Immutability

The returned enforcement contract remains a frozen dataclass.

Downstream consumers cannot change:

```text
ALLOW → BLOCK
```

or:

```text
BLOCK → ALLOW
```

after the decision has been created.

## Files Changed

### Production

```text
src/evaluation_run_regression_enforcement.py
```

Added:

```text
case-level gate imports
enforce_evaluation_run_case_regression_gate()
explicit case-gate type validation
```

The existing metric-level enforcement function remains unchanged.

### Tests

```text
tests/test_evaluation_run_case_regression_enforcement.py
```

Added six focused tests.

## Test Coverage

Sprint 11.67 verifies:

1. `PASS` produces `ALLOW`.
2. `FAIL` produces `BLOCK`.
3. `NOT_APPLICABLE` produces `ALLOW`.
4. Identical gates produce identical enforcement results.
5. The enforcement result is immutable.
6. Invalid input is rejected with `TypeError`.

## Verification

Focused case-level enforcement tests:

```text
6 passed
```

Existing metric-level enforcement tests:

```text
5 passed
```

Related case-level regression-chain tests:

```text
38 passed
```

Complete project suite:

```text
570 passed
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

Sprint 11.67 does not add or change:

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

Sprint 11.67 is complete when:

- the case-level gate maps to the existing enforcement contract;
- `PASS` maps to `ALLOW`;
- `FAIL` maps to `BLOCK`;
- `NOT_APPLICABLE` maps to `ALLOW`;
- invalid gate input is rejected;
- existing metric enforcement remains compatible;
- the focused and complete test suites pass;
- documentation records the boundary.

All completion criteria are satisfied.

## Recommended Next Slice

The next narrow integration should compose the already-approved runtime
layers:

```text
EvaluationRunRegressionOrchestrator.compare()
        ↓
evaluate_run_case_regression_gate()
        ↓
enforce_evaluation_run_case_regression_gate()
```

That composition should return existing immutable contracts without yet
changing CLI output, persistence, or process exit behavior.

This would give the CLI one stable application-level operation to invoke
in a later integration sprint.