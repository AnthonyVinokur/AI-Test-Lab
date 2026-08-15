# Sprint 11.13 — Runtime Report Contract Validation

## Goal

Sprint 11.13 makes the public AI Test Lab report contract enforceable at runtime.

Sprint 11.12 introduced the versioned public report schema and compatibility tests. Sprint 11.13 extends that boundary so a generated report must conform to the published `report-v1.0.schema.json` contract before it can be written to disk.

The objective is simple:

> AI Test Lab should never publish a report artifact that violates its declared public contract.

---

## Why This Sprint Matters

A JSON Schema is useful only if the system actually enforces it.

Before Sprint 11.13, AI Test Lab already used explicit public report DTOs and mapper functions to prevent internal runtime models from being serialized directly.

However, the final serialized payload was not independently validated against the canonical public JSON Schema during report generation.

Sprint 11.13 closes that gap.

The reporting path is now:

```text
Internal TestResult
        ↓
Explicit public mapper
        ↓
ReportV1 DTO
        ↓
Serialized public payload
        ↓
report-v1.0.schema.json validation
        ↓
JSON artifact written
```

If validation fails, the artifact is not written.

---

## Implementation

### Runtime Contract Validator

Added:

```text
src/report_contract_validator.py
```

The validator:

* Loads the canonical `schemas/report-v1.0.schema.json`
* Uses JSON Schema Draft 2020-12 validation
* Validates the final public serialized payload
* Caches the validator for reuse
* Rejects invalid reports before persistence
* Raises a dedicated `ReportContractValidationError`
* Reports the contract location and failed validation rule
* Avoids exposing rejected payload values in error messages

This keeps validation errors useful without leaking internal or potentially sensitive data.

---

## Reporter Integration

Updated:

```text
src/json_reporter.py
```

`JsonReporter` now performs these steps:

1. Receives internal test results
2. Calculates summaries and highlights
3. Maps internal runtime models to public DTOs
4. Builds `ReportV1`
5. Serializes the public DTO into a plain JSON-compatible payload
6. Validates that payload against `report-v1.0.schema.json`
7. Writes the JSON artifact only if validation succeeds

The runtime validator operates only on the already sanitized public representation.

Internal runtime models are never passed directly into the public JSON Schema validator.

---

## IP Protection Boundary

Sprint 11.13 reinforces the AI Test Lab IP Protection Boundary.

The public reporting system follows an explicit allow-list architecture:

```text
Proprietary / Internal Runtime State
              ↓
        Explicit Mapper
              ↓
        Public Report DTO
              ↓
      Public JSON Contract
              ↓
       External Consumer
```

This prevents commercially valuable internal implementation details from silently crossing the reporting boundary.

The JSON Schema is therefore a validation boundary, not a serialization mechanism for internal objects.

---

## Validation Behavior

The runtime validator rejects reports with contract violations such as:

* Missing required fields
* Incorrect field types
* Unsupported schema versions
* Unknown public fields
* Other JSON Schema violations

A failed validation raises:

```text
ReportContractValidationError
```

and prevents the output file from being created.

---

## Tests Added

Added:

```text
tests/test_report_contract_validator.py
```

Coverage includes:

* Canonical report fixture is accepted
* Missing required fields are rejected
* Incorrect schema versions are rejected
* Unknown public fields are rejected
* Incorrect field types are rejected

Updated:

```text
tests/test_json_reporter.py
```

A reporter integration test verifies that when runtime contract validation fails:

```text
invalid payload
      ↓
contract validation failure
      ↓
NO report artifact written
```

This proves that validation occurs before persistence.

---

## Dependency

Added the explicit dependency:

```text
jsonschema==4.26.0
```

The project now directly declares the JSON Schema validator it depends on instead of relying on a transitive dependency.

---

## Compatibility

Sprint 11.13 does not introduce a new report format.

The public contract remains:

```text
schema_version: 1.0
```

Sprint 11.12 compatibility tests remain in place to ensure the stored canonical schema and the `ReportV1` model stay synchronized.

Sprint 11.13 adds runtime enforcement on top of that existing contract.

---

## Verification

Focused report-contract verification:

```text
18 passed
```

Full framework regression suite:

```text
206 passed in 11.92s
```

`git diff --check` also completed without errors.

---

## Files Changed

```text
requirements.txt
src/json_reporter.py
src/report_contract_validator.py
tests/test_json_reporter.py
tests/test_report_contract_validator.py
docs/sprints/sprint11.13.md
```

---

## Definition of Done

Sprint 11.13 is complete when:

* [x] Generated public reports are validated against `report-v1.0.schema.json`
* [x] Invalid reports fail deterministically
* [x] Invalid reports are not written to disk
* [x] Validation errors identify the failed contract rule
* [x] Internal runtime models remain behind the public DTO boundary
* [x] Unknown public fields are rejected
* [x] Unsupported schema versions are rejected
* [x] The canonical Sprint 11.12 fixture remains valid
* [x] Existing reporter behavior remains compatible
* [x] Focused reporting tests pass
* [x] Full AI Test Lab regression suite passes

---

## Result

Sprint 11.13 converts the AI Test Lab report schema from a documented compatibility contract into an enforced runtime boundary.

The framework can now guarantee that a report written to disk conforms to its declared public `v1.0` contract.

This strengthens API stability, downstream consumer reliability, and protection against accidental exposure of internal implementation details.
