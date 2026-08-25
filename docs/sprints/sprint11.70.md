# Sprint 11.70 — Candidate Provenance Construction

## Status

**Completed**

## Executive Summary

Sprint 11.70 introduces a dedicated construction boundary for **candidate evaluation-run provenance**.

Sprint 11.69 established how stored baseline provenance is loaded from a validated JSON sidecar. Sprint 11.70 completes the other half of that regression boundary by defining how the current candidate run obtains complete, validated provenance from authoritative runtime inputs.

The completed flow is:

```text
EvaluationRunIdentity
        +
dataset_version
        +
report_schema_version
        ↓
construct_candidate_evaluation_run_provenance()
        ↓
EvaluationRunProvenance
```

The constructor is intentionally narrow. It does not generate run identifiers, inspect CLI state, infer dataset versions, hard-code report-contract metadata, or duplicate domain validation.

This preserves reproducibility, keeps responsibilities explicit, and prepares the regression subsystem for later runtime assembly.

---

## Goal

Define one stable construction boundary that answers:

> How does the current candidate evaluation run obtain complete provenance suitable for trustworthy regression comparison?

The implementation must:

- preserve an already-created evaluation-run identity;
- accept dataset version explicitly;
- accept report schema version explicitly;
- derive the public report contract through the existing contract helper;
- derive the deterministic report-contract fingerprint through the existing fingerprint helper;
- construct the existing immutable `EvaluationRunProvenance` domain object;
- reuse existing validation instead of duplicating it;
- reject unsupported report schema versions;
- avoid hidden defaults, runtime guesses, or fabricated metadata;
- leave CLI behavior, regression policy, and public report schemas unchanged.

---

## Background

The regression architecture had already accumulated the following boundaries before Sprint 11.70:

| Sprint | Capability |
|---|---|
| 11.62 | Candidate evaluation-result adaptation |
| 11.63 | Baseline acquisition boundary |
| 11.64 | Stored public-report baseline acquisition |
| 11.65 | Regression orchestration |
| 11.66 | Case-level regression gate |
| 11.67 | Regression enforcement decision |
| 11.68 | Case-level regression execution composition |
| 11.69 | Stored evaluation-run provenance loading |
| 11.70 | Candidate provenance construction |

By Sprint 11.69, baseline provenance could be loaded safely from storage, but the candidate side still depended on callers supplying a complete `EvaluationRunProvenance` directly.

That left an architectural seam:

```text
candidate runtime metadata
        ↓
???
        ↓
EvaluationRunProvenance
```

Sprint 11.70 closes that seam.

---

## Provenance Contract

`EvaluationRunProvenance` requires seven fields:

```text
run_id
model
evaluation_profile
dataset
dataset_version
report_contract
report_contract_fingerprint
```

The candidate constructor obtains those values from three authoritative sources.

### 1. Existing Evaluation-Run Identity

`EvaluationRunIdentity` supplies:

```text
run_id
model
evaluation_profile
dataset
```

The constructor does not generate or replace these values.

### 2. Explicit Dataset Version

The caller supplies:

```text
dataset_version
```

The constructor does not inspect storage, infer active versions, or substitute defaults.

### 3. Existing Public Report-Contract Helpers

The caller supplies:

```text
report_schema_version
```

The constructor then derives:

```text
report_contract
report_contract_fingerprint
```

through the framework’s existing report-contract helpers.

---

## Completed API

Sprint 11.70 introduces:

```python
def construct_candidate_evaluation_run_provenance(
    *,
    identity: EvaluationRunIdentity,
    dataset_version: str,
    report_schema_version: str,
) -> EvaluationRunProvenance:
```

Its responsibility is composition only.

Conceptually:

```python
contract = public_report_contract_identity(
    report_schema_version
)

fingerprint = public_report_contract_fingerprint(
    report_schema_version
)

return EvaluationRunProvenance(
    run_id=identity.run_id,
    model=identity.model,
    evaluation_profile=identity.evaluation_profile,
    dataset=identity.dataset,
    dataset_version=dataset_version,
    report_contract=contract.name,
    report_contract_fingerprint=fingerprint,
)
```

---

## Validation Model

Sprint 11.70 keeps validation responsibilities separated.

### Identity Boundary

The constructor explicitly requires an `EvaluationRunIdentity`.

Passing another object type raises `TypeError`.

This prevents loose construction from dictionaries, CLI namespaces, or unrelated runtime objects.

### Provenance Value Validation

The constructor delegates provenance value validation to the existing `EvaluationRunProvenance` domain object.

That contract remains responsible for requiring non-empty string values.

Examples rejected by the domain contract include:

```text
dataset_version = ""
dataset_version = "   "
dataset_version = None
```

The constructor does not duplicate those checks.

### Report Schema Validation

Unsupported report schema versions are rejected by the existing public report-contract helpers.

The constructor does not maintain its own report-version allow-list.

This preserves one source of truth for report compatibility.

---

## Determinism and Reproducibility

Candidate provenance construction is deterministic.

Given identical:

```text
EvaluationRunIdentity
dataset_version
report_schema_version
```

the constructor produces the same `EvaluationRunProvenance`.

It introduces no:

- timestamps;
- random identifiers;
- environment-derived metadata;
- inferred dataset versions;
- fallback values;
- mutable state;
- configuration discovery.

Run-ID generation remains a separate responsibility outside this boundary.

This distinction is important:

```text
identity creation
    may create a new run ID

candidate provenance construction
    must preserve that run ID
```

---

## Report-Contract Integrity

Sprint 11.70 deliberately reuses the framework’s existing public report-contract infrastructure.

The constructor does not hard-code:

```text
ai-test-lab.public-report
```

and does not calculate schema fingerprints independently.

Instead, it uses:

```python
public_report_contract_identity(report_schema_version)
```

and:

```python
public_report_contract_fingerprint(report_schema_version)
```

This prevents drift between candidate provenance and the actual report contract understood by the runtime.

The result is a stronger provenance chain:

```text
candidate run
    ↓
declared report schema version
    ↓
approved report-contract identity
    ↓
deterministic schema fingerprint
```

---

## Responsibility Map

| Component | Responsibility |
|---|---|
| `EvaluationRunIdentity` | Own run ID, model, evaluation profile, and dataset identity |
| Candidate provenance constructor | Compose approved runtime metadata into candidate provenance |
| Public report-contract identity helper | Resolve the supported public report contract |
| Public report-contract fingerprint helper | Produce the deterministic schema fingerprint |
| `EvaluationRunProvenance` | Validate and preserve immutable provenance |
| Baseline provenance loader | Load stored baseline provenance |
| Regression orchestrator | Coordinate baseline and candidate comparison |
| Regression execution | Compose comparison, gate, and enforcement |
| CLI | Future activation, presentation, persistence, and exit behavior |

The candidate provenance constructor does not compare runs, load reports, create datasets, load evaluation profiles, enforce gates, write artifacts, or terminate processes.

---

## Architecture After Sprint 11.70

The regression pipeline now has symmetrical provenance inputs.

```text
BASELINE
Stored public report
        +
Stored provenance sidecar
        ↓
BaselineRegressionResultAcquirer
        ↓
baseline case results
        +
EvaluationRunProvenance


CANDIDATE
Current TestResult values
        +
EvaluationRunIdentity
dataset_version
report_schema_version
        ↓
candidate result adapter
        +
candidate provenance constructor
        ↓
candidate case results
        +
EvaluationRunProvenance
```

These can feed the existing regression orchestrator:

```text
baseline provenance + baseline results
candidate provenance + candidate results
                ↓
EvaluationRunRegressionOrchestrator
                ↓
comparison
                ↓
case-level regression gate
                ↓
enforcement decision
```

The architecture is now ready for controlled runtime assembly without requiring provenance fabrication.

---

## Public and IP-Protection Boundary

Sprint 11.70 preserves the established IP protection boundary.

The constructor works only with approved provenance metadata:

```text
run_id
model
evaluation_profile
dataset
dataset_version
report_contract
report_contract_fingerprint
```

It does not expose, serialize, or derive:

- prompts;
- model responses;
- expected responses;
- metric scores;
- metric thresholds;
- judge prompts;
- provider credentials;
- provider runtime configuration;
- governance rules;
- proprietary scoring logic;
- evidence-intelligence logic;
- compliance logic;
- internal orchestration state.

No internal object graph is serialized.

No new public report field is introduced.

No public schema is expanded for implementation convenience.

---

## Files Changed

### Production

`src/candidate_evaluation_run_provenance.py`

Added:

- `construct_candidate_evaluation_run_provenance()`;
- explicit `EvaluationRunIdentity` type validation;
- public report-contract identity resolution;
- deterministic report-contract fingerprint resolution;
- construction of `EvaluationRunProvenance`;
- reuse of existing domain validation.

### Tests

`tests/test_candidate_evaluation_run_provenance.py`

Focused coverage includes:

- successful provenance construction;
- preservation of run ID;
- preservation of model;
- preservation of evaluation profile;
- preservation of dataset;
- preservation of explicit dataset version;
- report-contract identity derivation;
- report-contract fingerprint derivation;
- deterministic construction;
- rejection of incorrect identity type;
- rejection of empty dataset version;
- rejection of whitespace-only dataset version;
- rejection of non-string dataset version;
- rejection of unsupported report schema versions.

---

## Verification Evidence

| Verification | Result |
|---|---:|
| Focused Sprint 11.70 suite | **9 passed in 0.12s** |
| Complete project suite | **599 passed in 10.92s** |
| `git diff --check` | **Clean** |

The complete suite confirms that candidate provenance construction did not regress existing evaluation, reporting, provenance, compatibility, or regression behavior.

---

## Explicitly Out of Scope

Sprint 11.70 does not add or change:

- CLI regression arguments;
- CLI regression activation;
- baseline selection;
- run identity creation;
- dataset loading;
- dataset-version selection;
- evaluation-profile loading;
- model execution;
- report generation;
- report persistence;
- provenance persistence;
- regression-result persistence;
- console presentation;
- process exit behavior;
- exit-code semantics;
- comparison policy;
- case-level regression policy;
- metric-level regression policy;
- regression enforcement policy;
- baseline approval or promotion;
- provenance signing;
- remote provenance storage;
- database provenance storage;
- public report schemas;
- proprietary evaluation internals.

---

## Completion Criteria

- [x] Accept an existing `EvaluationRunIdentity`.
- [x] Preserve run ID exactly.
- [x] Preserve model exactly.
- [x] Preserve evaluation profile exactly.
- [x] Preserve dataset exactly.
- [x] Accept dataset version explicitly.
- [x] Accept report schema version explicitly.
- [x] Resolve report contract through the existing helper.
- [x] Resolve report-contract fingerprint through the existing helper.
- [x] Construct `EvaluationRunProvenance`.
- [x] Reuse existing provenance validation.
- [x] Reject incorrect identity types.
- [x] Reject invalid provenance values through the domain contract.
- [x] Reject unsupported report schema versions.
- [x] Produce deterministic output.
- [x] Avoid hidden defaults and inferred metadata.
- [x] Preserve the public report contract.
- [x] Preserve the IP-protection boundary.
- [x] Pass focused tests.
- [x] Pass the complete project suite.

---

## Design Decision

The most important design decision in Sprint 11.70 is that **candidate provenance construction is composition, not discovery**.

The constructor receives authoritative values.

It does not search for them.

This prevents a seemingly convenient helper from becoming a hidden runtime policy layer.

That distinction keeps the architecture testable and durable:

```text
Discovery / selection
        ↓
explicit values
        ↓
construction
        ↓
validated immutable provenance
```

Future CLI or runtime orchestration may decide where the inputs come from, but this construction boundary remains stable.

---

## Recommended Next Slice

### Sprint 11.71 — Regression Runtime Assembly

The next narrow sprint should assemble the already-completed boundaries into one runtime coordination layer.

A likely flow is:

```text
stored baseline report path
stored baseline provenance path
candidate results
candidate identity
dataset version
report schema version
        ↓
stored baseline acquisition
stored provenance loading
candidate provenance construction
        ↓
EvaluationRunRegressionOrchestrator
        ↓
execute_evaluation_run_case_regression()
```

The goal should be **assembly only**.

Sprint 11.71 should avoid introducing new policy unless assembly reveals a prerequisite boundary that must be solved first.

Recommended exclusions for that sprint:

- CLI UX;
- baseline promotion;
- persistence policy;
- exit-code policy changes;
- metric-level regression rules;
- new public report fields;
- proprietary governance or evidence logic.

---

## Final Outcome

Sprint 11.70 completes the provenance symmetry required for trustworthy regression execution.

Before this sprint:

```text
baseline → validated stored provenance
candidate → caller-supplied provenance with no dedicated construction boundary
```

After this sprint:

```text
baseline → validated stored provenance
candidate → validated constructed provenance
```

The framework no longer needs candidate provenance to be assembled ad hoc by future callers.

That reduces duplication, prevents fabricated metadata, preserves report-contract integrity, and creates a clean handoff into regression runtime assembly.
