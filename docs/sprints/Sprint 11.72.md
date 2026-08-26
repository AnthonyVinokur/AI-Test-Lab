# Sprint 11.72 — Regression Entry-Point Integration

## Summary

Sprint 11.72 introduces a dedicated execution entry point for evaluation-run regression.

The sprint connects explicit regression runtime inputs to the regression runtime assembly boundary created in Sprint 11.71 and then delegates execution to the existing case-level regression execution chain established earlier in Sprint 11.

The new entry point gives future CLI, CI/CD, API, and evaluation-run integration layers a single stable function for invoking regression behavior without reconstructing regression dependencies or duplicating comparison, gating, or enforcement logic.

The central design principle is:

> **Integration, not reimplementation.**

Sprint 11.72 does not create new regression policy. It composes already-verified boundaries into one application-facing execution path.

---

## Objective

Provide one narrow function that can execute an evaluation-run regression using explicit runtime inputs:

- candidate evaluation results;
- baseline public report path;
- baseline provenance path;
- candidate evaluation-run identity;
- candidate dataset version;
- public report schema version.

The entry point must:

1. assemble the regression runtime through the Sprint 11.71 assembly boundary;
2. execute the existing case-level regression chain;
3. return the existing regression execution result unchanged;
4. preserve all established compatibility, loading, gating, and enforcement behavior.

---

## Problem Before Sprint 11.72

By the end of Sprint 11.71, AI Test Lab already had the major regression components required for a full comparison:

```text
stored baseline report
        ↓
baseline acquisition
        ↓
stored baseline provenance
        ↓
candidate provenance
        ↓
regression runtime assembly
        ↓
EvaluationRunRegressionOrchestrator
```

However, callers still needed to understand how to connect runtime assembly to the existing case-level regression execution chain.

That left an integration gap.

A future caller could potentially have been forced to do something similar to:

```text
load provenance
construct baseline acquirer
construct candidate provenance
construct orchestrator
run comparison
evaluate gate
apply enforcement
```

That would create several architectural problems:

- duplicated orchestration;
- inconsistent error handling;
- tighter coupling to internal regression components;
- multiple possible execution paths;
- increased risk that CLI, API, and CI/CD integrations evolve differently;
- greater exposure of internal implementation details.

Sprint 11.72 closes that gap.

---

## Solution

Sprint 11.72 adds:

```text
src/evaluation_run_regression_entry_point.py
```

with a dedicated function:

```python
execute_evaluation_run_regression(...)
```

The function accepts explicit runtime inputs, delegates runtime construction to:

```python
assemble_evaluation_run_regression_runtime(...)
```

and then delegates execution to:

```python
execute_evaluation_run_case_regression(...)
```

Conceptually:

```text
explicit runtime inputs
        ↓
execute_evaluation_run_regression()
        ↓
assemble_evaluation_run_regression_runtime()
        ↓
EvaluationRunRegressionOrchestrator
        ↓
execute_evaluation_run_case_regression()
        ↓
comparison
        ↓
case-level gate
        ↓
enforcement
        ↓
EvaluationRunCaseRegressionExecution
```

The entry point contains no new regression decision logic.

---

## Architecture

### Full execution flow

```text
Candidate Evaluation Results
        +
Baseline Report Path
        +
Baseline Provenance Path
        +
Candidate EvaluationRunIdentity
        +
Candidate Dataset Version
        +
Public Report Schema Version
        │
        ▼
execute_evaluation_run_regression()
        │
        ▼
assemble_evaluation_run_regression_runtime()
        │
        ├── load stored baseline provenance
        ├── construct StoredBaselineRegressionResultAcquirer
        ├── construct candidate provenance
        └── construct EvaluationRunRegressionOrchestrator
        │
        ▼
execute_evaluation_run_case_regression()
        │
        ▼
EvaluationRunRegressionOrchestrator.compare()
        │
        ├── acquire baseline public report
        ├── adapt candidate results
        ├── verify regression eligibility
        └── compare baseline and candidate
        │
        ▼
evaluate_run_case_regression_gate()
        │
        ▼
enforce_evaluation_run_case_regression_gate()
        │
        ▼
EvaluationRunCaseRegressionExecution
```

---

## New Entry-Point Contract

The entry point receives:

```python
candidate_results
baseline_report_path
baseline_provenance_path
candidate_identity
candidate_dataset_version
report_schema_version
```

These inputs remain explicit.

The entry point does not:

- discover baselines;
- choose baseline versions;
- infer dataset versions;
- generate run IDs;
- scan result directories;
- locate provenance automatically;
- alter candidate results;
- define compatibility rules;
- define comparison rules;
- define gating policy;
- define enforcement policy;
- serialize regression output;
- modify CLI exit codes.

Those responsibilities remain outside this boundary.

---

## Why Explicit Inputs Matter

Sprint 11.72 deliberately avoids hidden discovery.

A regression execution should be reproducible.

Given:

```text
candidate results
baseline report
baseline provenance
candidate provenance inputs
schema version
```

the same regression execution path should be reconstructable later.

This supports the broader AI Test Lab goals of:

- reproducibility;
- traceability;
- deterministic integration behavior;
- auditability;
- CI/CD compatibility;
- future evidence generation.

The system does not silently decide which baseline a candidate should use.

That decision belongs to a higher-level workflow.

---

## Runtime Assembly Reuse

Sprint 11.72 does not construct regression dependencies itself.

Instead, it calls the Sprint 11.71 boundary:

```python
assemble_evaluation_run_regression_runtime(...)
```

That function already owns:

```text
baseline provenance loading
        +
baseline result acquirer construction
        +
candidate provenance construction
        +
orchestrator construction
```

This keeps dependency assembly centralized.

The architectural relationship is:

```text
Sprint 11.72
Entry Point
     ↓
Sprint 11.71
Runtime Assembly
     ↓
Existing Regression Internals
```

This prevents future application layers from depending directly on the internal construction sequence.

---

## Existing Execution Chain Reuse

Sprint 11.72 also reuses:

```python
execute_evaluation_run_case_regression(...)
```

That existing boundary already owns:

```text
comparison
    ↓
case-level gate
    ↓
enforcement
```

Therefore Sprint 11.72 does not call the individual gate or enforcement functions itself.

This preserves one authoritative execution chain.

---

## Regression Eligibility Is Preserved

During implementation, the integration tests initially reached the regression eligibility boundary and correctly rejected incompatible baseline and candidate provenance.

The mismatch included:

```text
dataset_version
report_contract
report_contract_fingerprint
```

This was not a production-code defect.

It demonstrated that the existing compatibility boundary was still active through the new entry point.

The test fixture was corrected so baseline and candidate provenance represented compatible evaluation runs.

This was an important integration result because it proved that Sprint 11.72 does not bypass regression eligibility rules.

---

## Public Report Contract Is Preserved

The stored baseline regression acquirer reads a versioned public AI Test Lab report.

The integration tests initially used an invalid simplified baseline structure:

```json
[
  {
    "test_id": "case-001",
    "passed": true
  }
]
```

The report reader correctly rejected this because the public report contract requires a JSON object with the complete report structure.

The Sprint 11.72 tests were therefore updated to reuse the existing authoritative fixture:

```text
tests/fixtures/report-v1.0.json
```

The test modifies only the fields needed for the regression scenario while preserving the validated public report contract.

This is preferable to constructing a partial imitation of the report schema.

---

## Contract Identity and Fingerprint Preservation

Candidate provenance is constructed from the public report contract identity and fingerprint.

The integration tests therefore derive the baseline contract metadata through the same established helpers:

```python
public_report_contract_identity("1.0")
public_report_contract_fingerprint("1.0")
```

rather than hard-coding values.

This ensures the integration test remains aligned with the public contract boundary if internal constants change while the public contract API remains valid.

---

## Error Propagation

The Sprint 11.72 entry point does not translate existing lower-level exceptions into new generic errors.

Existing error contracts remain visible.

### Missing baseline report

A missing baseline report continues to raise:

```python
ReportReadError
```

with a message identifying that the report could not be read.

The entry point does not convert this into a generic runtime exception.

---

### Invalid stored baseline provenance

Malformed stored provenance continues to raise:

```python
StoredEvaluationRunProvenanceLoadError
```

The entry point preserves that error contract.

---

### Unsupported report schema

An unsupported candidate public report schema version continues to raise:

```python
ValueError
```

with the existing public report schema validation message.

---

## Test Coverage

Sprint 11.72 adds:

```text
tests/test_evaluation_run_regression_entry_point.py
```

The focused suite verifies five scenarios.

### 1. Successful regression execution

Baseline:

```text
case-001 = PASS
```

Candidate:

```text
case-001 = PASS
```

Expected:

```text
compared_count = 1
regressed_count = 0
gate = PASS
enforcement = ALLOW
```

This proves that the complete integration path executes successfully.

---

### 2. Blocking regression execution

Baseline:

```text
case-001 = PASS
```

Candidate:

```text
case-001 = FAIL
```

Expected:

```text
regressed_count = 1
gate = FAIL
enforcement = BLOCK
```

This proves that the entry point preserves regression enforcement behavior.

---

### 3. Missing baseline report propagation

The baseline report path points to a nonexistent file.

Expected:

```python
ReportReadError
```

This verifies that the entry point does not hide baseline report acquisition failures.

---

### 4. Invalid baseline provenance propagation

The baseline provenance file contains invalid JSON.

Expected:

```python
StoredEvaluationRunProvenanceLoadError
```

This verifies that stored provenance validation remains intact.

---

### 5. Unsupported report schema rejection

The candidate uses:

```text
report_schema_version = "999.0"
```

Expected:

```text
ValueError
```

with:

```text
Unsupported public report schema version
```

This confirms that the new entry point continues to respect the public report contract registry.

---

## Verification Results

### Focused Sprint 11.72 test suite

```text
5 passed in 0.21s
```

Command:

```powershell
pytest .\tests\test_evaluation_run_regression_entry_point.py -v
```

---

### Full AI Test Lab regression suite

```text
611 passed in 10.76s
```

Command:

```powershell
pytest -q
```

The full suite passing confirms that the new regression entry point does not break existing behavior across the framework.

---

## Files Added

```text
src/evaluation_run_regression_entry_point.py
tests/test_evaluation_run_regression_entry_point.py
docs/sprints/sprint11.72.md
```

---

## Files Intentionally Not Changed

Sprint 11.72 does not require changes to:

```text
src/cli/app.py
src/cli/arguments.py
src/evaluation_run_regression_orchestrator.py
src/evaluation_run_case_regression_execution.py
src/evaluation_run_regression_runtime.py
```

This is intentional.

The sprint integrates existing components rather than altering their contracts.

---

## CLI Status

Sprint 11.72 does not activate regression through the CLI.

Although the CLI already contains:

```text
--regression-result-output
```

the CLI does not yet expose the complete baseline and provenance inputs required to invoke the new regression entry point.

CLI integration remains a separate concern.

This separation prevents Sprint 11.72 from mixing:

```text
runtime integration
+
argument design
+
CLI validation
+
output serialization
+
exit-code policy
```

into one oversized change.

---

## CI/CD Status

Sprint 11.72 does not yet define CI-specific behavior.

It does not decide:

- where CI obtains the baseline;
- how the baseline is promoted;
- whether `BLOCK` maps to process exit code `1`;
- whether regression output becomes an artifact;
- how CI identifies candidate run provenance;
- whether regression is mandatory or optional.

The new entry point makes those integrations possible without requiring CI/CD code to understand regression internals.

---

## API Status

No API endpoint is introduced in this sprint.

A future API layer can call the same regression entry point rather than reconstructing the regression runtime itself.

This helps preserve a consistent execution model across:

```text
CLI
CI/CD
API
future application services
```

---

## IP Protection Boundary

Sprint 11.72 remains on the orchestration side of the architecture.

The entry point exposes only the inputs required to execute the established regression workflow.

It does not expose:

- proprietary scoring algorithms;
- future governance logic;
- evidence-intelligence internals;
- compliance policy internals;
- proprietary baseline-selection strategy;
- commercial orchestration policy.

The entry point therefore remains compatible with the AI Test Lab public/private architectural boundary.

---

## Architectural Principle

The most important architectural rule introduced by this sprint is:

> **Application layers should invoke regression through the entry point rather than reconstructing the regression system.**

Future integration should prefer:

```python
execute_evaluation_run_regression(...)
```

instead of directly coordinating:

```text
provenance loader
baseline acquirer
candidate provenance builder
orchestrator
comparison
gate
enforcement
```

That keeps application code shallow and regression architecture centralized.

---

## Sprint Progression

The relevant regression architecture now progresses as follows:

```text
Regression contracts
        ↓
Baseline acquisition boundary
        ↓
Concrete stored baseline acquisition
        ↓
Regression orchestration
        ↓
Case-level regression gate
        ↓
Regression enforcement
        ↓
Case-level execution composition
        ↓
Stored baseline provenance loading
        ↓
Candidate provenance construction
        ↓
Regression runtime assembly
        ↓
Regression entry-point integration
        ↓
Future CLI / CI/CD / API wiring
```

Sprint 11.72 therefore represents the transition from:

```text
internally assembled regression capability
```

to:

```text
application-invokable regression capability
```

---

## Before Sprint 11.72

```text
Caller
  │
  ├── understand runtime assembly
  ├── construct dependencies
  ├── obtain orchestrator
  └── understand execution composition
```

---

## After Sprint 11.72

```text
Caller
  │
  └── execute_evaluation_run_regression(...)
                ↓
        complete existing regression chain
```

This is a meaningful reduction in coupling.

---

## Non-Goals

Sprint 11.72 intentionally does not implement:

- automatic baseline discovery;
- latest-baseline selection;
- baseline promotion;
- baseline storage policy;
- regression-history persistence;
- CLI regression activation;
- CI-specific exit codes;
- regression result serialization;
- API endpoints;
- regression dashboards;
- statistical regression thresholds;
- metric-level regression policy changes;
- model drift monitoring;
- production monitoring;
- governance workflows.

Those belong to later architectural layers.

---

## Quality Characteristics Preserved

Sprint 11.72 preserves the following project properties:

### Reproducibility

All required regression runtime inputs remain explicit.

### Traceability

Baseline and candidate provenance continue to flow through established provenance contracts.

### Compatibility Safety

Regression eligibility remains enforced before comparison.

### Contract Safety

Stored baseline reports continue to pass through the versioned public report reader.

### Single Responsibility

The new module integrates existing behavior rather than redefining it.

### Testability

The entry point can be exercised independently through focused integration tests.

### Extensibility

Future application layers can depend on one stable entry point.

---

## Result

Sprint 11.72 establishes the first stable application-facing execution boundary for evaluation-run regression.

AI Test Lab can now accept:

```text
candidate results
+
baseline report
+
baseline provenance
+
candidate identity
+
dataset version
+
report schema version
```

and execute the complete existing regression chain through one function.

The sprint does not add new regression intelligence.

Instead, it makes the intelligence and contracts already built across previous sprints safely reachable.

That distinction is important.

The system has progressed from:

```text
regression components exist
```

to:

```text
regression runtime can be assembled
```

and now to:

```text
regression can be invoked through one stable entry point
```

This provides a clean foundation for the next application-layer integration step while preserving reproducibility, compatibility enforcement, public-contract safety, and architectural separation.