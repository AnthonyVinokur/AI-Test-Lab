# Sprint 11.76 — Regression CLI Result-Output Contract

## Objective

Sprint 11.76 hardens the command-line regression result-output boundary.

The regression CLI integration already had the correct production architecture:

```text
Regression execution
        ↓
Regression enforcement
        ↓
EvaluationRunRegressionResult
        ↓
CLI output adapter
        ↓
Dedicated JSON writer
        ↓
regression-result.json
```

The CLI already:

- builds the approved public regression result,
- passes that result directly to the CLI regression-output adapter,
- writes the result to the user-requested output path,
- avoids reconstructing regression policy inside the CLI,
- preserves the regression subsystem as the owner of regression semantics.

Sprint 11.76 therefore does **not** introduce new production behavior.

Instead, it strengthens the automated contract that defines **when regression output may be produced**.

The new verification explicitly proves that a normal, non-regression CLI execution must never invoke the regression-result writer.

---

## Why This Sprint Exists

Sprint 11.74 completed the end-to-end regression CLI execution path:

```text
CLI
→ candidate evaluation
→ regression execution
→ enforcement
→ public regression result
→ regression artifact
→ process exit code
```

Sprint 11.75 hardened the process-level exit-code contract:

```text
Regression mode active
        ↓
EvaluationRunRegressionResult
        ↓
mapped regression exit code
        ↓
final process exit code
```

Sprint 11.76 protects the second externally visible regression interface:

```text
regression-result.json
```

This artifact is important because future consumers may include:

- CI/CD pipelines,
- automated quality gates,
- reporting systems,
- deployment workflows,
- audit tooling,
- external integrations.

Before building those consumers, the framework needs an explicit boundary between:

```text
normal evaluation output
```

and:

```text
regression-specific output
```

Sprint 11.76 makes that boundary durable.

---

## Core Contract

The CLI has two execution modes.

### Normal Evaluation Mode

When regression execution is not requested:

```text
CLI evaluation
        ↓
JSON evaluation report
        ↓
HTML evaluation report
```

The CLI must **not**:

```text
execute regression
```

and must **not**:

```text
write a regression-result artifact
```

The contract is therefore:

```text
regression not requested
        ↓
execute_evaluation_run_regression()
is not called
        ↓
write_cli_regression_result()
is not called
```

---

### Regression Mode

When regression execution is explicitly requested:

```text
versioned managed dataset
        +
single candidate model
        +
baseline report
        +
baseline provenance
        +
regression-result output path
        ↓
regression execution
        ↓
approved public regression result
        ↓
CLI regression-output adapter
        ↓
dedicated regression-result writer
```

The CLI does not construct its own regression JSON schema.

It delegates the approved result to the existing writer boundary.

---

## Result-Output Ownership

The production architecture remains intentionally layered.

### Regression Domain

The regression subsystem owns:

```text
comparison
→ gate
→ enforcement
→ public regression result
→ exit-code mapping
```

### Regression Result Writer

The dedicated regression-result writer owns:

```text
public result
→ serialized regression artifact
```

### CLI Regression Output Adapter

The CLI adapter owns only:

```text
approved public result
+
requested destination
        ↓
delegate to writer
```

### CLI Application

The CLI application owns:

```text
execution orchestration
```

It does not own regression serialization semantics.

---

## Approved Output Boundary

The intended data flow is:

```text
Protected regression internals
        ↓
Approved EvaluationRunRegressionResult
        ↓
write_cli_regression_result(...)
        ↓
write_evaluation_run_regression_result_json(...)
        ↓
Public JSON artifact
```

The CLI must not introduce an alternate path such as:

```text
CLI
↓
inspect internal enforcement state
↓
reconstruct output dictionary
↓
serialize independently
```

That would create duplicate contract ownership and increase compatibility risk.

Sprint 11.76 preserves the existing single-writer architecture.

---

## Existing Output Contract

The existing regression-output tests already verify exact serialized results.

### ALLOW

```json
{"enforcement":"allow","exit_code":0}
```

### BLOCK

```json
{"enforcement":"block","exit_code":1}
```

They also verify that:

- the approved result is delegated unchanged,
- the requested output path is delegated unchanged,
- nested output directories are supported,
- serialization remains owned by the dedicated result writer.

Sprint 11.76 does not modify these schemas.

---

## Sprint 11.76 Test Change

Sprint 11.76 strengthens the existing test:

```text
test_cli_does_not_execute_regression_without_regression_arguments
```

Before this sprint, the test explicitly proved:

```text
normal CLI invocation
        ↓
regression execution is not called
```

Sprint 11.76 adds the corresponding output-side assertion:

```text
normal CLI invocation
        ↓
regression output writer is not called
```

The new verification is:

```python
write_regression_result.assert_not_called()
```

Together, the test now protects both sides of the regression-mode boundary:

```text
No regression request
        ↓
No regression execution
        +
No regression artifact
```

---

## Why the Existing Test Was Extended

No new test case was required.

The existing test already represented the exact behavioral scenario:

```text
ordinary CLI execution without regression arguments
```

Adding the writer assertion to that test keeps the suite focused and avoids duplicate setup.

This is intentionally a contract-strengthening change rather than test proliferation.

As a result:

```text
Test count before Sprint 11.76: 624
Test count after Sprint 11.76:  624
```

The behavioral coverage increased even though the total number of test functions did not.

---

## Production Code Changes

None.

This is intentional.

The existing production implementation already follows the desired architecture.

The CLI currently:

```text
builds approved regression result
        ↓
passes result directly to output adapter
        ↓
passes requested output path directly
```

The output adapter already delegates to the dedicated regression-result writer.

Changing production code during this sprint would therefore add unnecessary risk without improving the contract.

Sprint 11.76 follows an important engineering principle:

> When production behavior is already correct, protect it with verification instead of rewriting it.

---

## Behavioral Matrix

| Execution mode | Regression requested | Regression execution | Regression artifact writer |
|---|---:|---:|---:|
| Normal evaluation | No | Not called | Not called |
| Regression evaluation | Yes | Called | Called |
| Invalid regression input | Requested but invalid | Not called | Not called |

This preserves an explicit mode boundary.

---

## Verification Results

Focused regression CLI verification:

```text
9 passed in 0.63s
```

Full project verification:

```text
624 passed in 5.86s
```

No production regression was introduced.

---

## Acceptance Criteria

Sprint 11.76 is complete when:

- [x] Normal CLI execution does not invoke regression execution.
- [x] Normal CLI execution does not invoke the regression-result writer.
- [x] Regression output remains explicitly opt-in.
- [x] Regression mode continues to write the approved public regression result.
- [x] The requested regression-output path continues to be preserved.
- [x] Exact `ALLOW` serialization remains unchanged.
- [x] Exact `BLOCK` serialization remains unchanged.
- [x] The CLI does not duplicate regression serialization logic.
- [x] The dedicated regression writer remains the serialization owner.
- [x] No new regression policy is introduced.
- [x] No production-code modification is required.
- [x] Focused regression CLI tests pass.
- [x] Full project test suite passes.

---

## Out of Scope

Sprint 11.76 deliberately does not add:

- baseline promotion,
- baseline approval,
- regression history,
- regression dashboards,
- new regression result fields,
- configurable regression serialization,
- additional exit codes,
- new comparison logic,
- new regression gate logic,
- new enforcement logic,
- GitHub Actions integration,
- CI/CD workflow configuration,
- deployment blocking,
- REST APIs,
- governance workflows,
- compliance logic,
- proprietary scoring or evidence logic.

Those capabilities remain separate future increments.

---

## Compatibility

### Existing CLI Evaluation

Normal evaluation behavior remains unchanged.

```text
evaluation
→ JSON report
→ HTML report
→ normal evaluation exit policy
```

No regression artifact is created unless regression execution is explicitly requested.

### Existing Regression CLI

Regression behavior remains unchanged.

```text
candidate evaluation
→ regression execution
→ approved public result
→ regression JSON artifact
→ regression exit code
```

No command-line interface changes were introduced.

No public schema changes were introduced.

---

## Architectural Significance

Sprint 11.76 establishes a durable separation between:

```text
ordinary evaluation artifacts
```

and:

```text
regression-specific artifacts
```

This matters because future automation should be able to reason safely about artifact presence.

For example:

```text
regression-result.json exists
```

should eventually be meaningful to a CI consumer because regression output is not accidentally emitted during ordinary evaluation.

That gives future integrations a cleaner contract:

```text
Regression requested
        ↓
Regression artifact produced
```

rather than:

```text
Artifact may exist for unrelated CLI execution
```

---

## CI/CD Readiness

Sprint 11.76 does not implement CI/CD integration.

It prepares for it.

A future CI quality gate should depend only on stable external contracts such as:

```text
process exit code
+
public regression-result artifact
```

It should not need access to:

```text
internal comparison objects
internal gate objects
internal enforcement implementation
protected scoring internals
```

Sprint 11.75 stabilized the first contract.

Sprint 11.76 stabilizes the second.

Together:

```text
Regression CLI
        ├── stable process signal
        │      └── exit code
        │
        └── stable machine-readable signal
               └── regression-result.json
```

This provides a clean foundation for later CI quality-gate integration.

---

## IP and Boundary Preservation

Sprint 11.76 does not expose additional proprietary implementation details.

External consumers continue to receive only the approved public regression result.

The CLI does not expose:

- internal comparison algorithms,
- scoring internals,
- evidence-processing logic,
- gate-construction logic,
- enforcement implementation details,
- proprietary orchestration logic,
- future governance mechanisms.

The public artifact remains intentionally narrow:

```text
enforcement decision
+
mapped exit code
```

This preserves the separation between:

```text
public integration contract
```

and:

```text
protected regression implementation
```

---

## Result

Before Sprint 11.76:

```text
Normal CLI execution did not write regression output.
```

After Sprint 11.76:

```text
Normal CLI execution does not write regression output
        +
the behavior is explicitly tested
        +
the output boundary is documented
        +
the contract is protected from accidental refactoring
```

The final Sprint 11.76 contract is:

```text
Regression output is opt-in.

No regression request
        ↓
no regression execution
        ↓
no regression artifact
```

Combined with Sprint 11.75:

```text
Regression requested
        ↓
approved regression result
        ├── owns the process exit code
        └── owns the machine-readable regression artifact
```

AI Test Lab now has two stable regression CLI interfaces ready for future CI/CD consumption without exposing or duplicating protected regression internals.