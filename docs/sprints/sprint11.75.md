# Sprint 11.75 — Regression CLI Exit-Code Precedence Contract

## Objective

Sprint 11.75 hardens and documents the command-line exit-code precedence established by Sprint 11.74.

The production behavior already exists:

```python
if regression_result is not None:
    return regression_result.exit_code.code

if unexpected_failures > 0 or errors > 0:
    return 1

return 0
```

This sprint does **not** introduce new regression behavior.

Instead, it adds an explicit automated contract proving that when regression mode is active, the authoritative regression result owns the final process exit code.

The sprint therefore focuses on verification, compatibility, and architectural clarity.

---

## Why This Sprint Exists

Sprint 11.74 completed the end-to-end regression CLI integration:

```text
CLI
→ candidate evaluation
→ regression execution
→ enforcement
→ public regression result
→ process exit code
```

During review of that integration, an important precedence rule became visible.

The CLI has two possible sources of failure state:

```text
ordinary evaluation failures/errors
```

and:

```text
regression enforcement exit code
```

When regression mode is active, Sprint 11.74 already gives precedence to:

```text
regression_result.exit_code.code
```

Sprint 11.75 makes that behavior explicit and permanently regression-tested.

---

## Core Contract

The final CLI process result depends on whether regression mode is active.

### Normal Mode

When no regression result exists:

```text
unexpected failures > 0
OR
errors > 0
        ↓
exit code 1
```

Otherwise:

```text
exit code 0
```

---

### Regression Mode

When a regression result exists:

```text
regression_result.exit_code.code
        ↓
final CLI exit code
```

The ordinary evaluation failure counters do not override that result.

This means the regression result acts as the authoritative process-level contract for regression execution.

---

## Exit-Code Precedence

The effective precedence is:

```text
Regression result available?
        │
        ├─ YES
        │    ↓
        │  return regression_result.exit_code.code
        │
        └─ NO
             ↓
          evaluate ordinary failures/errors
```

The CLI therefore does not combine two independent exit policies.

It selects the policy appropriate to the active execution mode.

---

## Behavioral Matrix

| Execution mode | Regression result | Ordinary evaluation state | Final exit code |
|---|---|---|---:|
| Normal | none | clean | `0` |
| Normal | none | unexpected failure/error | `1` |
| Regression | `ALLOW` | clean | `0` |
| Regression | `BLOCK` | clean | `1` |
| Regression | `ALLOW` | unexpected failure/error | `0` |
| Regression | `BLOCK` | unexpected failure/error | `1` |

The critical Sprint 11.75 contract is:

```text
Regression mode
+
regression exit code 0
+
ordinary unexpected failure
        ↓
final CLI exit code 0
```

This proves that regression mode owns the process outcome.

---

## Why This Is Intentional

The regression subsystem already contains its own deterministic enforcement path:

```text
Regression Evidence
        ↓
Regression Gate
        ↓
Enforcement
        ↓
ALLOW / BLOCK
        ↓
Exit-Code Mapping
        ↓
0 / 1
```

The CLI should not reinterpret or merge that result with separate local policy.

Doing so would risk creating competing process semantics inside:

```text
src/cli/app.py
```

Sprint 11.75 therefore preserves the existing ownership model:

```text
Regression subsystem
    owns regression process semantics

CLI
    propagates the approved result
```

---

## Architectural Boundary

The CLI remains an adapter and orchestration layer.

It does not:

- recalculate regression decisions,
- inspect regression evidence directly,
- reconstruct enforcement policy,
- remap `ALLOW` or `BLOCK`,
- combine regression policy with new CLI-local policy,
- change exit-code semantics,
- introduce CI-specific rules.

The CLI consumes:

```python
regression_result.exit_code.code
```

as an already-approved downstream contract.

---

## Existing Domain Ownership

The exit-code mapping remains owned by:

```text
src/evaluation_run_regression_exit_code.py
```

The mapping contract remains:

| Enforcement | Exit code |
|---|---:|
| `ALLOW` | `0` |
| `BLOCK` | `1` |

The regression result contract remains owned by:

```text
src/evaluation_run_regression_result.py
```

Sprint 11.75 does not modify either component.

---

## Production Code Changes

None.

This is intentional.

The required runtime behavior already existed after Sprint 11.74.

Sprint 11.75 adds explicit verification so future refactoring cannot accidentally alter the precedence contract.

---

## Test Change

Sprint 11.75 adds one focused CLI test:

```text
test_cli_regression_exit_code_takes_precedence_over_normal_failures
```

The test creates this situation:

```text
regression exit code = 0
unexpected_failures = 1
errors = 0
```

and verifies:

```text
CLI exit code = 0
```

This locks down the established precedence behavior.

---

## Verified Execution Path

The new test exercises the actual CLI control flow:

```text
managed dataset regression invocation
        ↓
candidate evaluation
        ↓
regression execution
        ↓
public regression result
        ↓
ordinary result summary
        ↓
regression result detected
        ↓
regression exit code returned
```

The test specifically ensures that the subsequent ordinary failure counters do not become authoritative in regression mode.

---

## Verification Results

Focused regression CLI suite:

```text
6 passed in 0.68s
```

Full project suite:

```text
624 passed in 12.08s
```

No production regression was introduced.

---

## Acceptance Criteria

Sprint 11.75 is complete when:

- [x] Regression CLI exit-code precedence is explicitly documented.
- [x] Regression mode remains governed by the public regression result.
- [x] `ALLOW` continues to map to exit code `0`.
- [x] `BLOCK` continues to map to exit code `1`.
- [x] Ordinary evaluation failures do not override a regression result.
- [x] Non-regression CLI behavior remains unchanged.
- [x] No duplicate exit-code policy is introduced in the CLI.
- [x] No production-code change is required.
- [x] Focused regression CLI tests pass.
- [x] Full project test suite passes.

---

## Out of Scope

Sprint 11.75 deliberately does not add:

- new regression comparison logic,
- new gate logic,
- new enforcement logic,
- new exit-code mapping,
- combined CLI failure policies,
- configurable exit-code precedence,
- GitHub Actions rules,
- CI/CD workflow changes,
- deployment blocking logic,
- baseline promotion,
- baseline approval,
- regression history,
- dashboards,
- APIs,
- governance rules.

Those concerns remain separate future work.

---

## Compatibility

### Non-Regression Mode

Existing behavior remains:

```text
unexpected failure/error
→ exit 1

clean evaluation
→ exit 0
```

### Regression Mode

Existing behavior remains:

```text
ALLOW
→ exit 0

BLOCK
→ exit 1
```

No externally visible behavior changes were introduced.

---

## IP and Boundary Preservation

Sprint 11.75 does not expose any new internal regression implementation.

The CLI continues to depend on the approved public regression result rather than protected internals.

No new details are surfaced about:

- regression comparison internals,
- scoring logic,
- evidence evaluation,
- gate construction,
- enforcement implementation,
- proprietary decision logic,
- future governance logic.

This keeps operational integration separate from commercially valuable internal mechanisms.

---

## Result

Sprint 11.75 turns an implicit integration behavior into an explicit tested contract.

Before this sprint:

```text
Regression precedence existed in production code.
```

After this sprint:

```text
Regression precedence exists
+
is documented
+
is regression-tested
+
is protected from accidental refactoring
```

The final contract is:

```text
Regression mode active
        ↓
EvaluationRunRegressionResult exists
        ↓
its mapped exit code owns the process outcome
```

This gives AI Test Lab a stable and durable command-line contract for future CI/CD integration without adding duplicate policy or unnecessary production complexity.