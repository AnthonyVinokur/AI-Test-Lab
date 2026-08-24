# Sprint 11.64 — Stored Baseline Artifact Acquisition

## Status

Completed

## Date

August 24, 2026

## Goal

Implement the first concrete baseline regression result acquirer.

The component reads a previously stored, versioned public evaluation report and converts its final case outcomes into the narrow regression comparison contract introduced in Sprint 11.63.

## Problem

Sprint 11.63 defined the baseline acquisition boundary:

- `BaselineRegressionResultAcquirer`
- `AcquiredBaselineRegressionResult`

That sprint deliberately did not decide where a baseline came from.

Regression comparison now needed a concrete way to acquire baseline case outcomes from an existing stored artifact without coupling the regression layer to internal evaluation models or proprietary runtime state.

Two existing artifact types were considered:

1. The regression enforcement artifact
2. The versioned public evaluation report

The enforcement artifact contains only:

```json
{
  "enforcement": "allow",
  "exit_code": 0
}
```

It cannot serve as a regression baseline because it does not contain individual case identities or outcomes.

The public evaluation report contains validated test identifiers and final pass/fail outcomes. It is therefore the correct existing source for baseline case results.

However, the public report does not contain the complete `EvaluationRunProvenance`. Provenance must therefore be provided explicitly rather than inferred from incomplete report data.

## Implemented Design

Sprint 11.64 added:

```text
StoredBaselineRegressionResultAcquirer
```

The acquirer receives:

- A path to a stored public report
- An explicit `EvaluationRunProvenance`

Its `acquire()` method:

1. Loads the report through the existing `load_report()` boundary.
2. Validates the artifact against the published public JSON Schema.
3. Converts every public report result into an `EvaluationRunCaseResult`.
4. Stores those results in an immutable tuple.
5. Returns an `AcquiredBaselineRegressionResult`.
6. Preserves the supplied provenance object unchanged.

## Data Flow

```text
Stored public evaluation report
            |
            v
       load_report()
            |
            v
Published JSON Schema validation
            |
            v
Validated ReportV1 consumer model
            |
            v
Extract only test_id and passed
            |
            v
tuple[EvaluationRunCaseResult, ...]
            |
            v
AcquiredBaselineRegressionResult
```

## Public-Report Mapping

Only two public fields cross into the regression comparison layer:

| Public report field | Regression field |
|---|---|
| `test_id` | `case_id` |
| `passed` | `passed` |

The acquirer does not copy:

- Prompts
- Actual model responses
- Expected responses
- Metric scores
- Metric reasons
- Runtime options
- Engine details
- Token usage
- Timing information
- Cost information
- Internal orchestration state

## Provenance Decision

`EvaluationRunProvenance` requires:

- `run_id`
- `model`
- `evaluation_profile`
- `dataset`
- `dataset_version`
- `report_contract`
- `report_contract_fingerprint`

The existing public report does not reliably contain all these values.

Sprint 11.64 therefore requires provenance to be supplied explicitly.

The acquirer does not guess, reconstruct, or fabricate provenance from partial report fields.

This preserves deterministic regression eligibility and prevents a stored artifact from being paired with inferred identity information.

## Validation and Error Behavior

The implementation reuses the existing public report reader.

This means the acquirer intentionally inherits established behavior for:

- Missing files
- Unreadable files
- Invalid JSON
- Non-object JSON roots
- Missing schema versions
- Unsupported schema versions
- Public-contract violations

No duplicate file reader, JSON parser, schema, or report DTO was added.

Invalid provenance is rejected when the acquirer is constructed.

## Immutability

The acquired result uses:

```python
tuple[EvaluationRunCaseResult, ...]
```

The returned `AcquiredBaselineRegressionResult` is a frozen dataclass.

The supplied `EvaluationRunProvenance` is also a frozen dataclass.

This prevents baseline identity and case outcomes from being mutated after acquisition.

## Empty Baseline Behavior

A structurally valid public report containing no case results produces:

```python
case_results == ()
```

Empty results are preserved rather than treated as an acquisition failure.

Whether an empty baseline may participate in later regression enforcement remains the responsibility of downstream comparison and policy layers.

## Files Added

```text
src/stored_baseline_regression_result_acquirer.py
tests/test_stored_baseline_regression_result_acquirer.py
docs/sprints/sprint11.64.md
```

## Existing Components Reused

```text
src/report_reader.py
src/report_schema.py
src/report_contract_validator.py
src/baseline_regression_result_acquirer.py
src/evaluation_run_provenance.py
src/evaluation_run_regression_comparison.py
```

## Test Coverage

Focused tests verify:

1. Valid stored public reports are acquired.
2. Supplied provenance is preserved.
3. Public test IDs become regression case IDs.
4. Public pass/fail outcomes are preserved.
5. Case results are returned as an immutable tuple.
6. Missing reports are rejected.
7. Invalid JSON is rejected.
8. Invalid provenance is rejected.
9. Empty report result collections remain valid.
10. Structurally invalid reports are rejected.

## Verification Results

Focused Sprint 11.64 tests:

```text
7 passed in 0.19s
```

Related boundary tests:

```text
31 passed
```

Complete regression suite:

```text
552 passed in 10.79s
```

## IP Protection Boundary

This sprint preserves the established public-versus-private architecture boundary.

The stored baseline acquirer consumes the stable public report contract rather than serializing or reading internal evaluation objects directly.

Only the minimum regression information crosses the boundary:

- Case identity
- Final pass/fail outcome
- Explicit run provenance

Commercially valuable evaluation internals, governance logic, evidence intelligence, scoring implementation, and orchestration details remain outside the baseline acquisition contract.

## Out of Scope

Sprint 11.64 does not implement:

- Baseline selection
- Baseline approval
- Baseline promotion
- Candidate acquisition changes
- Baseline-versus-candidate orchestration
- Regression gate CLI wiring
- Regression enforcement changes
- Exit-code changes
- Remote artifact storage
- Cloud artifact retrieval
- Database persistence
- Provenance inference
- Multi-artifact baseline discovery

## Acceptance Criteria Result

| Acceptance criterion | Result |
|---|---|
| Valid stored artifact can be acquired | Passed |
| Provenance remains paired with results | Passed |
| Case results are immutable | Passed |
| Empty result collections remain valid | Passed |
| Invalid JSON is rejected | Passed |
| Structurally invalid reports are rejected | Passed |
| Missing files produce intentional errors | Passed |
| Existing behavior remains unchanged | Passed |
| Complete test suite passes | Passed |

## Result

AI Test Lab can now acquire regression baseline case outcomes from a stored, strictly validated public evaluation artifact.

The acquisition remains narrow, deterministic, immutable, reusable, and protected by the existing public contract boundary.
