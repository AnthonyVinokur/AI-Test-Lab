# Sprint 11.26 — Public Report Nested Exposure Boundary Hardening

## Overview

Sprint 11.26 strengthens the AI Test Lab public report contract by closing a nested exposure gap inside `runtime_options`.

The framework already protected the public reporting boundary in several ways:

* internal runtime models were mapped into explicit public DTOs;
* public Pydantic models rejected unknown top-level fields;
* the generated JSON Schema used `additionalProperties: false` for public objects;
* internal engine errors were sanitized;
* known proprietary runtime options were filtered before serialization;
* the final JSON report was validated before being written to disk.

However, one nested object remained more permissive than the rest of the public contract.

The `runtime_options` field was represented as:

```python
dict[str, Any]
```

and the published JSON Schema therefore allowed arbitrary nested keys:

```json
{
  "runtime_options": {
    "additionalProperties": true,
    "type": "object"
  }
}
```

This meant the producer correctly filtered private fields, but the published public contract itself would still accept arbitrary fields inside `runtime_options`.

Sprint 11.26 removes that inconsistency.

---

## Problem

Before this sprint, the internal-to-public flow looked like this:

```text
Internal MetricResult
        |
        v
map_runtime_options()
        |
        v
Approved runtime options
        |
        v
Public Metric DTO
        |
        v
JSON Schema
```

The mapper allowed only approved keys such as:

```text
include_reason
```

and removed internal options such as:

```text
governance_weight
internal_scoring_strategy
private_evidence_id
```

This was good producer-side protection.

However, the JSON Schema still declared `runtime_options` as an unrestricted object.

As a result, an externally constructed report could theoretically contain:

```json
{
  "runtime_options": {
    "include_reason": true,
    "internal_scoring_strategy": "proprietary-v5",
    "private_evidence_id": "EV-123"
  }
}
```

and the schema validator would accept it.

The public contract was therefore weaker than the reporter that produced the contract.

---

## Sprint Goal

The goal of Sprint 11.26 is to make the public contract enforce the same exposure boundary as the producer.

The new rule is:

```text
runtime_options
    |
    +-- include_reason        ALLOWED
    |
    +-- anything else        REJECTED
```

Public nested objects must use explicit allowlists just like top-level public report structures.

---

## Implementation

### 1. Introduced a Dedicated Public Runtime Options DTO

A new public model was added:

```python
class ReportMetricRuntimeOptionsV1(PublicReportModel):
    include_reason: bool | None = None
```

Because the model inherits from `PublicReportModel`, it also inherits:

```python
ConfigDict(
    extra="forbid",
    frozen=True,
)
```

This means unknown runtime-option fields cannot silently enter the public contract.

---

## 2. Updated the Public Metric DTO

Previously:

```python
runtime_options: dict[str, Any]
```

The field now uses the dedicated public DTO:

```python
runtime_options: ReportMetricRuntimeOptionsV1
```

This makes the runtime-options boundary explicit and typed.

The structure is now:

```text
ReportMetricResultV1
        |
        +-- engine
        +-- metric_name
        +-- score
        +-- threshold
        +-- passed
        +-- reason
        |
        +-- runtime_options
                |
                +-- include_reason
```

No arbitrary nested properties are part of the public v1.0 contract.

---

## 3. Updated the Runtime Option Mapper

The mapper now produces the public runtime-options DTO directly.

Conceptually:

```text
Internal runtime options
        |
        v
Explicit public mapping
        |
        v
ReportMetricRuntimeOptionsV1
        |
        v
Public JSON
```

Internal fields remain outside the public reporting boundary.

For example:

```text
include_reason              -> public
governance_weight           -> removed
internal_scoring_strategy   -> removed
private_evidence_id         -> removed
```

---

## 4. Hardened the Published JSON Schema

The generated schema previously contained:

```json
"runtime_options": {
  "additionalProperties": true,
  "type": "object"
}
```

It now references:

```json
"$ref": "#/$defs/ReportMetricRuntimeOptionsV1"
```

The new schema definition rejects unknown fields using:

```json
"additionalProperties": false
```

This is important because the public JSON Schema is part of the external contract.

The contract now protects itself even if a report was not produced by `JsonReporter`.

---

## 5. Added a Regression Test

Sprint 11.26 added a validator regression test that deliberately injects an internal field:

```python
report["results"][0]["evaluation_results"][0][
    "runtime_options"
]["internal_scoring_strategy"] = "proprietary-v5"
```

The validator must reject the report with an `additionalProperties` contract violation.

The test was first run before the schema change and failed with:

```text
Failed: DID NOT RAISE ReportContractValidationError
```

This demonstrated that the weakness was real.

After the contract was hardened, the same test passed.

This provided a clear red-to-green TDD cycle.

---

## 6. Updated Existing Mapper Tests

Existing tests expected `runtime_options` to behave like a plain dictionary.

Because it is now a typed public DTO, the tests were updated to verify both:

```python
public_metric.runtime_options.include_reason is True
```

and the serialized public representation:

```python
public_metric.runtime_options.model_dump(
    mode="json",
    exclude_none=True,
)
```

produces:

```python
{
    "include_reason": True,
}
```

This verifies both the Python API and JSON-facing representation.

---

## Security and IP Protection Impact

Sprint 11.26 strengthens the AI Test Lab IP Protection Boundary.

The reporting architecture now follows this rule:

```text
Internal models
      |
      v
Explicit mapper
      |
      v
Public DTO
      |
      v
Published JSON Schema
      |
      v
Contract validation
      |
      v
Public report
```

At each boundary, public exposure is intentional.

The framework does not depend on developers remembering individual private fields.

Instead, the public contract defines what is allowed.

Anything outside that public contract is rejected.

This provides stronger protection for future internal capabilities such as:

* proprietary scoring strategies;
* governance logic;
* evidence intelligence;
* private evaluator metadata;
* commercial evaluation features;
* compliance algorithms;
* internal orchestration details;
* implementation-specific debugging state.

These capabilities can evolve internally without automatically becoming part of the public report format.

---

## Why This Matters

A secure public contract should not operate like this:

```text
Everything is public
except fields we remember to remove.
```

It should operate like this:

```text
Nothing is public
unless explicitly approved.
```

Sprint 11.26 moves the nested runtime-options contract fully into that second model.

This reduces accidental information exposure and makes future framework evolution safer.

---

## Test Results

Focused public-report boundary tests:

```text
24 passed
```

Full AI Test Lab regression suite:

```text
269 passed
```

No functional regressions remained after the contract change.

---

## Files Modified

Sprint 11.26 modified:

```text
schemas/report-v1.0.schema.json
src/report_mapper.py
src/report_schema.py
tests/test_report_contract_validator.py
tests/test_report_mapper.py
tests/test_report_schema.py
docs/sprints/sprint11.26.md
```

---

## Final Result

Sprint 11.26 closes the nested public exposure gap in `runtime_options`.

Before:

```text
Mapper                 strict
Public DTO             mostly strict
JSON Schema            permissive inside runtime_options
```

After:

```text
Mapper                 strict
Public DTO             strict
JSON Schema            strict
Contract validator     strict
```

The producer and the published public contract now enforce the same exposure policy.

Sprint 11.26 therefore strengthens the AI Test Lab public reporting boundary without introducing a new reporting abstraction or changing the overall report architecture.
