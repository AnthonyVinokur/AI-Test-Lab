## Sprint 11.71 — Regression Runtime Assembly

### Summary

Adds a dedicated runtime assembly boundary for evaluation-run regression.

The new `assemble_evaluation_run_regression_runtime()` function converts explicit baseline and candidate runtime inputs into a configured `EvaluationRunRegressionOrchestrator` by reusing the existing provenance, baseline-acquisition, and orchestration boundaries.

### What changed

* Added `src/evaluation_run_regression_runtime.py`.
* Added `tests/test_evaluation_run_regression_runtime.py`.
* Loads stored baseline provenance through the existing provenance loader.
* Constructs `StoredBaselineRegressionResultAcquirer` using the supplied baseline report path.
* Constructs candidate provenance through the existing Sprint 11.70 boundary.
* Returns a configured `EvaluationRunRegressionOrchestrator`.
* Preserves lazy baseline report acquisition.
* Introduces no new CLI behavior, regression policy, comparison logic, gating logic, or enforcement logic.

### Architecture

```text
baseline report path
baseline provenance path
candidate identity
candidate dataset version
report schema version
        ↓
Regression Runtime Assembly
        ↓
EvaluationRunRegressionOrchestrator
        ↓
existing regression execution chain
```

The key design rule is:

> **Assembly, not discovery.**

The runtime assembler does not select baselines, infer dataset versions, generate run IDs, scan storage, or execute the comparison.

### Verification

Focused Sprint 11.71 suite:

```text
7 passed in 0.22s
```

Coverage includes:

* orchestrator assembly;
* baseline report-path preservation;
* baseline provenance loading;
* candidate provenance construction;
* candidate identity preservation;
* invalid baseline provenance handling;
* unsupported report-schema handling;
* verification that assembly does not eagerly load the baseline report.

### Files

```text
src/evaluation_run_regression_runtime.py
tests/test_evaluation_run_regression_runtime.py
docs/sprints/sprint11.71.md
```

### Result

Sprint 11.71 closes the manual regression-wiring gap and gives future CLI, CI/CD, API, and evaluation-run integration layers one stable boundary for constructing the regression runtime.
