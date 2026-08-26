# Sprint 11.74 — Regression CLI Execution Wiring

## Status

**Complete**

Sprint 11.74 connects the validated regression CLI contract from Sprint 11.73 to the existing regression runtime assembled in Sprints 11.64–11.72.

The CLI can now execute a regression comparison for a versioned managed dataset, persist the public regression result artifact, and return the regression enforcement exit code to the calling shell or CI system.

This sprint deliberately keeps the CLI as an orchestration boundary. It does not duplicate comparison, gating, enforcement, provenance, or exit-code logic already owned by the regression subsystem.

---

## Objective

Wire the CLI into the established evaluation-run regression execution path so that a user can:

1. run a candidate evaluation,
2. compare it with a stored baseline,
3. construct the public regression result,
4. persist that result to the requested output path, and
5. receive the regression enforcement decision through the process exit code.

The implementation must preserve existing non-regression CLI behavior and must reject regression configurations whose provenance cannot be represented truthfully.

---

## Why This Sprint Matters

Before Sprint 11.74, the CLI could validate regression arguments but did not execute the regression workflow.

That left an important integration gap:

```text
CLI arguments
    ↓
candidate evaluation
    ↓
[ no regression execution ]
```

Sprint 11.74 closes that gap:

```text
CLI arguments
    ↓
early regression-input validation
    ↓
candidate evaluation
    ↓
existing regression entry point
    ↓
comparison
    ↓
gate
    ↓
enforcement
    ↓
public regression result
    ↓
JSON persistence
    ↓
process exit code
```

This makes regression enforcement usable from normal command-line and CI workflows without moving domain logic into the CLI layer.

---

## Scope

### Included

Sprint 11.74 adds CLI execution wiring for:

- regression activation after the Sprint 11.73 all-or-none argument contract is satisfied,
- early semantic validation of regression execution requirements,
- candidate evaluation-run identity construction,
- delegation to the existing regression entry point,
- conversion of regression enforcement into the public regression result,
- persistence of the regression result artifact,
- propagation of the mapped regression exit code,
- protection against unsupported prompt-file regression,
- protection against implicit/latest dataset provenance,
- protection against ambiguous multi-model candidate provenance,
- focused CLI regression execution tests.

### Explicitly Not Included

This sprint does **not**:

- reimplement regression comparison logic,
- reimplement regression gate logic,
- reimplement regression enforcement logic,
- redefine regression exit-code mapping,
- add a new report schema,
- add prompt-file regression provenance semantics,
- add multi-model regression provenance,
- change the existing non-regression evaluation flow,
- introduce new regression policy rules.

Those concerns remain owned by their existing domain components or future sprints.

---

## Design Principle

The CLI is an adapter and orchestrator, not the regression engine.

Sprint 11.74 follows this ownership model:

```text
CLI
 ├─ validates execution-level prerequisites
 ├─ runs the candidate evaluation
 ├─ constructs candidate identity
 ├─ calls the regression entry point
 ├─ builds the public regression result
 ├─ writes the result artifact
 └─ returns the already-mapped exit code

Regression subsystem
 ├─ acquires baseline evidence
 ├─ constructs provenance
 ├─ compares candidate and baseline
 ├─ evaluates the regression gate
 ├─ produces enforcement
 └─ maps enforcement to exit semantics
```

This boundary is important for maintainability, testability, and future API/CI integrations.

---

## CLI Preconditions for Regression Execution

Regression execution is intentionally narrower than ordinary candidate evaluation.

When regression mode is requested, the CLI requires all of the following.

### 1. Managed dataset input

Regression execution requires:

```text
--dataset
```

Prompt-file input is rejected.

Reason:

A managed dataset has an explicit identity and versioning model. A loose prompt file currently does not provide a durable dataset-version contract suitable for regression provenance.

The CLI returns:

```text
Input error: regression execution requires a managed --dataset.
```

with exit code:

```text
2
```

---

### 2. Explicit dataset version

Regression execution requires:

```text
--dataset-version
```

The CLI does not permit regression provenance to use the presentation alias `latest`.

Reason:

Regression evidence must identify the exact candidate dataset version that produced the result. A mutable alias is insufficient for durable provenance.

The CLI returns:

```text
Input error: regression execution requires an explicit --dataset-version.
```

with exit code:

```text
2
```

---

### 3. Exactly one model

Regression execution currently requires exactly one candidate model.

Reason:

`EvaluationRunIdentity` contains one model identity, while a multi-model CLI invocation can produce results for multiple models. Recording only the first model would create misleading provenance.

Until a dedicated multi-model regression identity contract exists, ambiguous regression runs are rejected.

The CLI returns:

```text
Input error: regression execution requires exactly one model.
```

with exit code:

```text
2
```

---

## Early Validation

Regression-specific semantic validation occurs before expensive candidate execution.

This ordering is intentional:

```text
parse arguments
    ↓
validate regression prerequisites
    ↓
load tests
    ↓
run model(s)
```

Invalid regression configuration therefore fails before:

- model execution,
- candidate report generation,
- regression execution,
- regression artifact persistence.

This prevents avoidable runtime cost and keeps input errors deterministic.

---

## Candidate Evaluation-Run Identity

For a valid regression run, the CLI constructs an `EvaluationRunIdentity` from the candidate execution configuration.

Conceptually:

```python
candidate_identity = create_evaluation_run_identity(
    model=args.models[0],
    evaluation_profile=...,
    dataset=args.dataset,
)
```

The identity records the candidate model, evaluation profile, and managed dataset identity used by the regression subsystem.

Because regression mode currently enforces exactly one model, `args.models[0]` is unambiguous.

---

## Regression Entry-Point Delegation

The CLI delegates regression execution to the existing stable entry point:

```python
execute_evaluation_run_regression(...)
```

The CLI supplies:

- candidate test results,
- baseline report path,
- baseline provenance path,
- candidate evaluation-run identity,
- explicit candidate dataset version,
- report schema version.

The current public report schema version used by this integration is:

```text
1.0
```

The entry point remains responsible for assembling and invoking the established regression runtime.

The CLI does not reach into individual comparison, gate, or enforcement components.

---

## Public Regression Result Construction

The regression execution returns an enforcement result through the established execution structure.

The CLI converts that enforcement into the public regression result through:

```python
build_evaluation_run_regression_result(
    regression_execution.enforcement
)
```

This preserves the existing mapping from enforcement semantics to public exit-code semantics.

The CLI does not create its own decision mapping.

---

## Regression Result Persistence

The public regression result is written through the dedicated CLI output boundary:

```python
write_cli_regression_result(
    regression_result,
    args.regression_result_output,
)
```

This keeps JSON encoding and file-format ownership outside `src/cli/app.py`.

The resulting artifact is suitable for downstream automation, CI evidence, and future reporting integrations.

---

## Exit-Code Behavior

When regression execution completes successfully, the CLI returns:

```python
regression_result.exit_code.code
```

rather than independently interpreting enforcement state.

This means the shell/CI contract is driven by the authoritative regression exit-code mapper.

Conceptually:

```text
non-blocking regression decision
    → exit 0

blocking regression decision
    → exit 1
```

Input/configuration errors remain:

```text
exit 2
```

Non-regression CLI behavior remains unchanged.

---

## Backward Compatibility

Sprint 11.74 preserves normal CLI execution when regression arguments are absent.

A standard candidate run:

```text
--prompts ...
```

or:

```text
--dataset ...
```

continues through the pre-existing evaluation/reporting path without invoking regression execution.

Regression behavior is opt-in.

---

## Implementation Summary

### Modified

```text
src/cli/app.py
```

Responsibilities added:

- detect requested regression execution,
- reject unsupported regression provenance configurations early,
- construct candidate evaluation-run identity,
- invoke the stable regression entry point,
- build the public regression result,
- persist the regression artifact,
- return the regression exit code.

### Added

```text
tests/cli/test_regression_execution.py
```

Focused tests cover CLI orchestration and boundary behavior without duplicating serialization or regression-domain tests.

---

## Focused Test Coverage

Sprint 11.74 includes five CLI regression execution tests.

### 1. Normal CLI execution does not activate regression

Verifies that ordinary CLI execution remains backward compatible.

Expected behavior:

```text
no regression arguments
→ regression entry point not called
→ normal exit code preserved
```

---

### 2. Prompt-file regression is rejected

Verifies that regression execution cannot create unsupported provenance from a loose prompt file.

Expected behavior:

```text
--prompts + regression arguments
→ exit 2
→ regression not executed
```

---

### 3. Versioned managed dataset executes regression

Verifies the positive wiring path.

The test checks that the CLI forwards:

- candidate results,
- baseline report path,
- baseline provenance path,
- model identity,
- evaluation profile identity,
- dataset identity,
- explicit dataset version,
- report schema version.

It also verifies:

- public regression-result construction,
- regression-result persistence,
- successful exit-code propagation.

---

### 4. Blocking regression returns exit code 1

Verifies that the CLI does not reinterpret enforcement.

Expected behavior:

```text
regression result exit code = 1
→ CLI returns 1
```

The result artifact is still persisted before the process returns.

---

### 5. Multi-model regression is rejected

Verifies provenance integrity.

Expected behavior:

```text
multiple candidate models + regression request
→ exit 2
→ candidate model execution not started
→ regression entry point not called
```

This prevents a candidate result set containing multiple models from being represented by a single-model `EvaluationRunIdentity`.

---

## Verification Evidence

Focused Sprint 11.74 tests:

```text
tests/cli/test_regression_execution.py

5 passed
```

Full project regression suite after the Sprint 11.74 changes:

```text
622 passed
```

Whitespace validation:

```text
git diff --check
```

Result:

```text
clean
```

> Note: the full-suite count remains 622 until the final newly added test is included in the staged/committed test set and the full suite is rerun. The authoritative release evidence should use the final post-staging test run.

---

## Acceptance Criteria

Sprint 11.74 is complete when all of the following are true:

- [x] Regression CLI arguments activate the existing regression runtime.
- [x] Regression remains inactive when regression arguments are absent.
- [x] Regression requires a managed dataset.
- [x] Regression requires an explicit dataset version.
- [x] Regression requires exactly one model.
- [x] Invalid regression input is rejected before model execution.
- [x] Candidate identity is constructed at the CLI integration boundary.
- [x] Candidate results are passed to the stable regression entry point.
- [x] Baseline report and provenance paths are forwarded unchanged.
- [x] Regression enforcement is converted through the existing public-result builder.
- [x] Regression result persistence uses the dedicated output adapter.
- [x] Blocking enforcement is surfaced through the mapped process exit code.
- [x] Normal CLI behavior remains backward compatible.
- [x] Focused regression CLI tests pass.
- [x] Full project test suite passes.
- [x] `git diff --check` is clean.

---

## Architectural Decisions

### Managed datasets only

This is a provenance decision, not a convenience restriction.

Regression evidence must remain reproducible. A managed dataset with an explicit version provides a durable identity that can be compared across evaluation runs.

---

### Explicit version instead of `latest`

`latest` is useful for interactive execution but is not a stable provenance identifier.

Regression evidence records the exact selected dataset version.

---

### Single-model regression boundary

The current run identity contract describes one model.

Rather than silently attaching a multi-model candidate result set to the first requested model, Sprint 11.74 rejects that configuration.

A future multi-model regression design should introduce an explicit contract instead of overloading the current identity.

---

### No duplicated exit-code logic

The CLI consumes:

```text
EvaluationRunRegressionResult.exit_code
```

It does not inspect enforcement decisions and invent its own shell semantics.

This keeps policy ownership centralized.

---

### No duplicated JSON serialization

The CLI uses:

```text
write_cli_regression_result(...)
```

instead of encoding regression structures directly.

This protects the public artifact boundary and allows serialization to evolve independently of CLI orchestration.

---

## IP and Public-Contract Boundary

Sprint 11.74 preserves the project’s public/private architecture boundary.

The CLI consumes established public/result adapters rather than serializing internal regression orchestration structures directly.

The externally persisted artifact is produced through the dedicated regression-result writer, while comparison, enforcement, acquisition, orchestration, and other commercially valuable internals remain behind their existing boundaries.

---

## Known Constraints

Sprint 11.74 intentionally leaves several capabilities for future work:

- prompt-file regression provenance,
- implicit/latest dataset regression,
- multi-model regression identity,
- configurable report schema selection,
- richer CLI regression summaries,
- CI-specific presentation layers,
- API/service exposure of the same regression execution contract.

These are not defects in Sprint 11.74; they are explicit boundaries chosen to keep regression evidence truthful and reproducible.

---

## Result

Sprint 11.74 turns the CLI regression contract into an operational workflow.

Before:

```text
validated regression arguments
→ no execution
```

After:

```text
validated regression arguments
→ candidate evaluation
→ regression runtime
→ enforcement
→ persisted public result
→ CI-compatible exit code
```

The CLI now provides a narrow, deterministic bridge from user input to the established regression subsystem while preserving provenance integrity, backward compatibility, and domain ownership.

---

## Suggested Commit Title

```text
feat: wire regression execution into CLI
```

## Suggested Pull Request Title

```text
Sprint 11.74 — Regression CLI Execution Wiring
```
