# Sprint 11.69 — Stored Evaluation-Run Provenance Loading

## Status

**Completed**

## Executive summary

Sprint 11.69 adds a trusted boundary for loading evaluation-run provenance from a stored JSON sidecar file.

The sprint began as an investigation into CLI regression integration. That investigation exposed a prerequisite: the public evaluation report does not contain every field required to reconstruct `EvaluationRunProvenance`. Direct CLI wiring would therefore require fabricated values, hidden defaults, or duplicated provenance rules.

The completed solution is deliberately narrow:

```text
Stored provenance JSON
        ↓
load_stored_evaluation_run_provenance()
        ↓
EvaluationRunProvenance
```

This preserves reproducibility, keeps the public-report boundary stable, and prepares future CLI baseline selection without introducing new regression policy.

## Goal

Answer one architectural question:

> How can a future CLI regression operation load complete, validated baseline provenance without inventing metadata or expanding the public report contract?

The solution must:

- load provenance from a UTF-8 JSON artifact;
- require every approved provenance field;
- reject unknown fields;
- reuse the existing domain validation rules;
- return the immutable `EvaluationRunProvenance` contract;
- translate storage and parsing failures into one stable boundary error;
- leave CLI behavior and `ReportV1` unchanged.

## Background

| Sprint | Capability |
|---|---|
| 11.62 | Candidate evaluation-result adaptation |
| 11.63 | Baseline acquisition boundary |
| 11.64 | Stored public-report baseline acquisition |
| 11.65 | Regression orchestration |
| 11.66 | Case-level regression gate |
| 11.67 | Regression enforcement decision |
| 11.68 | Case-level regression execution composition |
| 11.69 | Stored provenance loading boundary |

Sprint 11.68 deliberately left CLI activation, persistence, presentation, and process exit behavior for later work. Sprint 11.69 inspected that seam before changing runtime behavior.

## Architectural discovery

`EvaluationRunProvenance` requires seven non-empty string fields:

```text
run_id
model
evaluation_profile
dataset
dataset_version
report_contract
report_contract_fingerprint
```

The public report contains evaluation results, summaries, timestamps, models, and schema information. It does not contain enough information to reconstruct all seven fields faithfully.

A baseline report path alone therefore cannot provide valid regression provenance. Missing values must be rejected, not guessed. Sprint 11.69 resolves the baseline half of this problem through an explicit provenance sidecar.

## Completed contract

### Loader

```python
def load_stored_evaluation_run_provenance(
    path: str | Path,
) -> EvaluationRunProvenance:
```

The loader accepts a string or `Path`, reads JSON, validates the storage boundary, and constructs the existing provenance domain object.

### Approved JSON shape

```json
{
  "run_id": "baseline-run-001",
  "model": "llama3.1:latest",
  "evaluation_profile": "fast-ci",
  "dataset": "regression-suite",
  "dataset_version": "1",
  "report_contract": "ai-test-lab.public-report",
  "report_contract_fingerprint": "sha256:..."
}
```

The document must be a JSON object containing exactly these seven fields.

## Validation model

Validation is separated into two layers.

### Storage-boundary validation

The loader owns:

- file readability;
- JSON decoding;
- JSON root type;
- required-field presence;
- unknown-field rejection.

Missing and unknown field names are sorted before errors are constructed, making diagnostics deterministic.

### Domain validation

After the JSON shape is approved, construction is delegated to:

```python
EvaluationRunProvenance(**payload)
```

The existing domain contract remains responsible for requiring each field to be a non-empty string. The loader does not duplicate those rules.

## Stable error boundary

Sprint 11.69 introduces:

```python
class StoredEvaluationRunProvenanceLoadError(ValueError):
    """Raised when stored evaluation-run provenance cannot be loaded."""
```

It represents:

- unreadable or missing files;
- malformed JSON;
- non-object JSON roots;
- missing required fields;
- unknown fields;
- invalid provenance values.

Lower-level exceptions remain available through exception chaining. Diagnostic messages include the artifact path where useful, helping local and CI users find the failing input.

## Determinism and immutability

The same JSON object produces the same immutable provenance value. The loader adds no randomness, timestamps, inferred metadata, environment defaults, mutable configuration, or fallback values.

Missing or invalid provenance is rejected rather than synthesized.

## Public and IP-protection boundary

Sprint 11.69 does not modify `ReportV1`. Operational provenance is not added to the public evaluation report merely for CLI convenience.

The loader accepts only the seven approved metadata fields and rejects unknown fields. It does not expose:

- prompts, model responses, or expected responses;
- metric scores or thresholds;
- provider runtime configuration;
- governance rules;
- proprietary scoring or evidence-intelligence logic;
- internal mutable orchestration state.

No internal object is automatically serialized, and no new public-report contract is introduced.

## Responsibility map

| Component | Responsibility |
|---|---|
| Public report reader | Load validated public evaluation reports |
| Stored baseline acquirer | Extract baseline case outcomes |
| Stored provenance loader | Load approved provenance metadata |
| Provenance contract | Validate field values and preserve immutability |
| Regression orchestrator | Acquire, adapt, and compare runs |
| Regression execution | Compose comparison, gate, and enforcement |
| CLI | Future activation, presentation, persistence, and exit behavior |

The loader does not compare runs, choose or approve baselines, enforce gates, write results, or control process exit codes.

## Files changed

### Production

`src/stored_evaluation_run_provenance_loader.py`

Added:

- `StoredEvaluationRunProvenanceLoadError`;
- `load_stored_evaluation_run_provenance()`;
- exact field allow-list;
- deterministic missing- and unknown-field validation;
- filesystem and JSON error translation;
- delegation to `EvaluationRunProvenance`.

### Tests

`tests/test_stored_evaluation_run_provenance_loader.py`

Added fourteen focused cases covering valid loading and every approved failure class.

### Documentation

`docs/sprints/sprint11.69.md`

Records the discovery, implementation boundary, verification evidence, exclusions, and handoff.

## Verification evidence

| Verification | Result |
|---|---:|
| Focused loader suite | 14 passed in 0.11s |
| Related provenance and baseline suite | 45 passed in 0.37s |
| Complete project suite | 590 passed in 11.26s |
| `git diff --check` before documentation | Clean |

The focused suite verifies valid loading, string-path support, unreadable files, malformed JSON, non-object roots, missing fields, unknown fields, and invalid values for all seven provenance fields.

## Explicitly out of scope

Sprint 11.69 does not add or change:

- CLI regression arguments or activation;
- candidate provenance construction;
- regression-result persistence;
- console presentation or process termination;
- exit-code semantics;
- comparison, gate, or enforcement policy;
- baseline approval or promotion;
- provenance writing or signing;
- remote or database provenance storage;
- public report schemas;
- metric-level regression policy;
- protected evaluation internals.

## Completion criteria

- [x] Load stored provenance from UTF-8 JSON.
- [x] Require a JSON object root.
- [x] Require all seven approved fields.
- [x] Reject unknown fields.
- [x] Produce deterministic missing- and unknown-field diagnostics.
- [x] Keep field-value validation in the domain contract.
- [x] Use a stable loading-boundary error.
- [x] Preserve lower-level causes through exception chaining.
- [x] Return immutable provenance.
- [x] Leave the public report contract unchanged.
- [x] Pass focused, related, and complete test suites.
- [x] Document the boundary and next slice.

## Recommended next slice

### Sprint 11.70 — Candidate Provenance Construction

The next narrow sprint should define how a current CLI evaluation run obtains complete candidate provenance:

```text
run_id
model
evaluation_profile
dataset
dataset_version
report_contract
report_contract_fingerprint
```

Construction should use explicit evaluation inputs plus existing identity and report-contract helpers. It must not fabricate values or duplicate domain validation.

After candidate provenance is stable, a later CLI integration can safely compose:

```text
baseline report + baseline provenance
candidate results + candidate provenance
                ↓
execute_evaluation_run_case_regression()
                ↓
build_evaluation_run_regression_result()
                ↓
optional persistence + existing exit code
```

## Final outcome

Sprint 11.69 closes a subtle but important architectural gap. Regression enforcement now has a trustworthy path for receiving stored baseline provenance without weakening reproducibility, enlarging the public report, or pushing domain coordination into the CLI.

The framework is ready for the next controlled step: constructing equally explicit provenance for the candidate run.
