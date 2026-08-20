# Sprint 11.28 — Public Report Release Readiness

## Objective

Sprint 11.28 establishes a final release-readiness boundary for the AI Test Lab Public Report v1.0.

The goal is to ensure that a report is not considered safe for external release unless it can successfully pass the existing public report consumer and contract validation layers.

## Problem

Before this sprint, AI Test Lab already had:

* Public Report v1.0 schema validation
* Supported schema version enforcement
* Consumer validation
* Protection against unknown public fields
* Protection against non-public runtime options
* Rejection of malformed report data

However, these protections existed as separate lower-level behaviors.

There was no single release-level API that answered:

> Is this report safe and valid to release?

## Solution

Sprint 11.28 introduces:

```text
src/report_release_validator.py
```

with the release boundary:

```python
validate_report_for_release(report_path)
```

The release validator delegates validation to the existing report consumer rather than duplicating schema or parsing logic.

This keeps the architecture simple and prevents validation rules from diverging.

## Release-Level Exception

The sprint introduces:

```python
ReportReleaseValidationError
```

Lower-level validation errors are translated into this release-level exception.

For example:

```text
ReportReadError
        │
        ├──► ReportReleaseValidationError

ReportContractValidationError
        │
        └──► ReportReleaseValidationError
```

This gives callers one stable release-level failure contract.

The original lower-level exception remains available through Python exception chaining using:

```python
exception.__cause__
```

This preserves internal debugging information without exposing implementation-specific failure handling to release consumers.

## Release Readiness Rules

A report is release ready only if all existing public contract checks succeed.

The following cases are verified.

### Valid Public Report

A valid Public Report v1.0 is accepted.

```text
Valid report
    ↓
Release validator
    ↓
PASS
```

### Unsupported Schema Version

A report declaring an unsupported schema version is rejected.

```text
schema_version = "9.0"
    ↓
BLOCK
```

### Unexpected Root-Level Fields

Internal or unknown root-level fields are rejected.

Example:

```json
{
  "secret_internal_score": 99
}
```

Result:

```text
BLOCK
```

### Unexpected Nested Fields

Internal fields inserted inside public result objects are rejected.

Example:

```text
results[0].internal_evidence_trace
```

Result:

```text
BLOCK
```

### Private Runtime Options

Only runtime options explicitly permitted by the public schema may be released.

An internal option such as:

```text
internal_scoring_strategy
```

is rejected.

This protects the public report boundary from leaking proprietary evaluation behavior.

### Invalid JSON

Malformed or unreadable JSON is rejected.

The release validator fails closed.

A report that cannot be validated is not considered release ready.

## IP Protection Boundary

Sprint 11.28 reinforces the AI Test Lab IP Protection Boundary.

The release path is now:

```text
Internal Evaluation
        ↓
Public DTO Transformation
        ↓
Public Report
        ↓
Schema Validation
        ↓
Consumer Validation
        ↓
Release Readiness Gate
        ↓
External Release
```

Unknown, private, proprietary, or malformed information cannot pass through the release boundary simply because a report file exists.

## Architectural Principle

The release validator does not recreate schema validation logic.

Instead:

```text
Release Validator
        ↓
Report Consumer
        ↓
Report Reader
        ↓
Contract Validator
        ↓
JSON Schema
```

Each layer retains one responsibility.

This reduces duplication and lowers the risk of contract drift.

## Tests Added

Sprint 11.28 adds:

```text
tests/test_report_release_readiness.py
```

Coverage includes:

* valid Public Report v1.0
* unsupported schema version
* unexpected root-level fields
* unexpected nested fields
* private runtime options
* malformed JSON
* preservation of the underlying validation cause

## Regression Result

Full AI Test Lab test suite:

```text
281 passed in 10.82s
```

No regressions were detected.

## Definition of Done

Sprint 11.28 is complete when:

* a release-readiness validator exists
* valid Public Report v1.0 artifacts are accepted
* malformed reports are rejected
* unsupported schema versions are rejected
* internal fields are rejected
* nested internal fields are rejected
* private runtime options are rejected
* failures are exposed through a stable release-level exception
* underlying failure causes remain available for debugging
* the complete regression suite remains green

## Result

AI Test Lab now has an explicit controlled release boundary for Public Report v1.0.

A public report is no longer merely generated and assumed to be safe.

It must prove that it is safe to release.
