# Sprint 11.20 — Public Report Hardening

## Goal

Strengthen and verify the AI Test Lab public-report boundary so internal or proprietary runtime information cannot accidentally appear in public JSON reports.

Sprint 11.20 does not redesign the reporting architecture. Instead, it adds regression protection around the explicit public DTO and mapper boundary already established by the framework.

## Why This Sprint Matters

AI Test Lab contains internal evaluation state that may include implementation details, proprietary scoring information, governance logic, runtime configuration, or diagnostic information.

Public reports must expose only information deliberately approved by the public report contract.

The intended architecture is:

```text
Internal Evaluation Models
        |
        v
Explicit Report Mapper
        |
        v
Public Report DTO
        |
        v
JSON Schema Validation
        |
        v
Public JSON Report
```

Internal models must never be serialized directly into public artifacts.

## Existing Protection Boundary

The current reporting implementation already provides several layers of protection.

### Explicit field mapping

`src/report_mapper.py` maps internal runtime models into public report DTOs field by field.

This means newly added internal attributes do not automatically become public.

### Public DTO validation

Public report models inherit from `PublicReportModel`, which uses:

```python
ConfigDict(extra="forbid", frozen=True)
```

Unexpected fields are therefore rejected by the public model boundary.

### Runtime option allow-list

Metric runtime options can contain internal execution configuration.

Only explicitly approved runtime options are exposed publicly.

Currently:

```text
include_reason
```

is approved.

Private options such as governance weights, internal scoring strategies, or private evidence identifiers are discarded before serialization.

### Engine error sanitization

Raw evaluation-engine errors can reveal implementation details such as internal exception messages, file paths, service names, or proprietary components.

Internal engine errors are normalized to the public-safe message:

```text
Evaluation engine failed.
```

### Final JSON Schema validation

Before a report is written to disk, the final serialized payload is validated against the published public report schema.

This provides another contract boundary after DTO mapping.

## Sprint 11.20 Changes

### Reporter-level regression tests

`tests/test_json_reporter.py` now verifies that private runtime options cannot appear in the generated JSON report.

The test injects internal-style values such as:

```text
governance_weight
internal_scoring_strategy
private_evidence_id
```

and confirms that they do not survive public serialization.

The report retains only the explicitly approved option:

```json
{
  "include_reason": true
}
```

A second reporter test verifies that raw internal engine errors are not exposed in public JSON.

Internal diagnostic information is replaced by the public-safe engine failure message.

### Mapper-level regression tests

A new test module was added:

```text
tests/test_report_mapper.py
```

These tests verify the protection boundary directly at the mapper layer.

They confirm that:

* only approved metric runtime options cross the boundary;
* proprietary/internal runtime options are discarded;
* internal engine error details are replaced with the approved public message.

Testing both the mapper and final reporter provides defense in depth.

## Security Property

Sprint 11.20 establishes the following regression requirement:

> Adding a new internal field or runtime option must not automatically make that information part of the public report contract.

Public exposure must remain explicit and deliberate.

The framework therefore follows a default-private approach:

```text
New internal field
        |
        X
Does not become public automatically
```

A field must be intentionally added to the public DTO, mapper, and report contract before it can become part of a public artifact.

## Compatibility

Sprint 11.20 does not intentionally modify Report Contract v1.0.

Existing valid reports remain compatible.

No production serialization changes were required because the existing explicit mapper, DTO, sanitization, and schema-validation architecture already enforced the desired protection boundary.

The sprint freezes this behavior through regression tests.

## Verification

Targeted reporter tests:

```text
4 passed
```

Mapper and reporter boundary tests:

```text
6 passed
```

Full project test suite:

```text
249 passed in 12.02s
```

## Result

Sprint 11.20 confirms and hardens the AI Test Lab public-report protection boundary.

The framework now has explicit regression coverage proving that internal runtime configuration and diagnostic details cannot silently leak into public reports.

This preserves the architectural separation between:

```text
Public interoperability
```

and:

```text
Internal / proprietary implementation
```
