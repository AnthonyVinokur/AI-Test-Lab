# Sprint 11.14 — Version-Aware Report Contract Validation

## Goal

Sprint 11.14 makes the AI Test Lab public report validation layer version-aware.

Sprint 11.13 introduced runtime validation against the canonical `report-v1.0.schema.json` contract. Sprint 11.14 extends that design so report validation is no longer permanently hard-wired to schema version `1.0`.

The objective is:

> AI Test Lab should validate a public report against the contract version declared by that report.

---

## Why This Sprint Matters

The current public report contract is:

```text
schema_version: 1.0
```

However, future versions may introduce contracts such as:

```text
report-v1.1.schema.json
report-v2.0.schema.json
```

Without a version-aware validation boundary, every future report version would require the reporter itself to know which schema file to validate against.

Sprint 11.14 separates those responsibilities.

The reporting path is now:

```text
Internal runtime result
        ↓
Explicit public mapper
        ↓
Report DTO
        ↓
Serialized public payload
        ↓
schema_version
        ↓
Version-aware contract validator
        ↓
Published JSON Schema
        ↓
JSON artifact
```

---

## Implementation

### Version-Aware Contract Registry

Updated:

```text
src/report_contract_validator.py
```

A report schema registry now maps supported public versions to their canonical schema files.

Current mapping:

```text
1.0 → report-v1.0.schema.json
```

The runtime can now determine which validator to use from the report's declared `schema_version`.

---

## Generic Validation API

Added:

```python
validate_report_payload(payload)
```

This function:

1. Reads `schema_version` from the serialized public payload
2. Verifies that the version is supported
3. Selects the corresponding canonical schema
4. Validates the payload against that schema
5. Raises `ReportContractValidationError` when validation fails

This removes report-version knowledge from `JsonReporter`.

---

## Backward Compatibility

The existing public validator remains available:

```python
validate_report_v1_payload(payload)
```

This preserves compatibility for existing callers that explicitly validate version `1.0`.

The new generic API does not replace the explicit v1 API. It adds a version-dispatch layer above it.

Architecture:

```text
validate_report_payload()
        ↓
schema_version
        ↓
version registry
        ↓
appropriate validator

validate_report_v1_payload()
        ↓
explicit v1.0 validation
```

---

## Reporter Integration

Updated:

```text
src/json_reporter.py
```

Before Sprint 11.14:

```text
JsonReporter
    ↓
validate_report_v1_payload()
    ↓
report-v1.0.schema.json
```

After Sprint 11.14:

```text
JsonReporter
    ↓
validate_report_payload()
    ↓
schema_version
    ↓
contract registry
    ↓
report-v1.0.schema.json
```

`JsonReporter` now depends on the generic contract boundary rather than a specific report version.

---

## Supported Version Discovery

Added:

```python
supported_report_schema_versions()
```

This exposes the report contract versions understood by the current runtime.

Current result:

```text
("1.0",)
```

This provides a clean foundation for future schema negotiation, compatibility tooling, CLI inspection, or downstream integrations.

---

## Validation Behavior

The generic validator rejects:

* Missing `schema_version`
* Unsupported schema versions
* Invalid payloads for the selected schema
* Unknown public fields
* Invalid field types
* Missing required public fields

Unsupported versions fail explicitly rather than being silently interpreted as another contract.

Example:

```text
schema_version: 2.0
        ↓
No registered schema
        ↓
ReportContractValidationError
```

---

## IP Protection Boundary

Sprint 11.14 preserves the existing AI Test Lab IP Protection Boundary.

Validation still operates only on the sanitized public representation.

```text
Proprietary / Internal Runtime State
              ↓
        Explicit Mapper
              ↓
────────────────────────────────
      IP PROTECTION BOUNDARY
────────────────────────────────
              ↓
        Public Report DTO
              ↓
      Serialized Public Data
              ↓
      Version-Aware Validator
              ↓
       Public JSON Contract
```

Internal runtime models, governance logic, evidence intelligence, scoring logic, and orchestration details remain outside the published schema layer.

---

## Tests Added

Updated:

```text
tests/test_report_contract_validator.py
```

Coverage now includes:

* Existing v1 fixture remains valid
* Existing explicit v1 validator remains compatible
* Supported schema versions expose `1.0`
* Generic validator accepts a valid v1 report
* Generic validator rejects unsupported versions
* Generic validator rejects missing schema versions

Updated:

```text
tests/test_json_reporter.py
```

The reporter integration test now patches the generic runtime validator used by `JsonReporter`.

---

## Verification

Focused validator tests:

```text
9 passed
```

JSON reporter tests:

```text
2 passed
```

Full framework regression suite:

```text
210 passed in 4.68s
```

Whitespace verification:

```text
git diff --check
```

completed without errors.

---

## Files Changed

```text
src/json_reporter.py
src/report_contract_validator.py
tests/test_json_reporter.py
tests/test_report_contract_validator.py
docs/sprints/sprint11.14.md
```

---

## Definition of Done

* [x] Generic `validate_report_payload()` exists
* [x] Validation dispatches using `schema_version`
* [x] Version `1.0` maps to `report-v1.0.schema.json`
* [x] Unsupported versions fail explicitly
* [x] Missing schema versions fail explicitly
* [x] Existing `validate_report_v1_payload()` remains compatible
* [x] `JsonReporter` uses the generic validator
* [x] Supported schema versions can be queried
* [x] Existing contract validation remains intact
* [x] Public DTO/IP boundary remains unchanged
* [x] Focused tests pass
* [x] Full AI Test Lab regression suite passes
* [x] `git diff --check` passes

---

## Result

Sprint 11.14 evolves AI Test Lab's public report validation architecture from a single-version implementation into a version-aware contract system.

The framework still publishes only report contract `1.0`, but the validation layer is now ready to support future report schemas without coupling `JsonReporter` to a specific version.

This establishes a cleaner long-term compatibility boundary for downstream consumers, integrations, dashboards, APIs, and future report contract evolution.
