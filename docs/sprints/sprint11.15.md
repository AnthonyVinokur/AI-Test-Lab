# Sprint 11.15 — Version-Aware Report Consumption

## Objective

Sprint 11.15 introduces a controlled, version-aware boundary for consuming AI Test Lab public reports.

Previous Sprint 11 work established the report-production side of the architecture, including:

* public report DTOs
* versioned serialization
* JSON Schema contracts
* runtime contract validation
* version-aware schema validation
* IP protection boundaries

Sprint 11.15 completes the opposite side of that contract by adding a safe way for downstream Python consumers to load, validate, and use versioned public reports.

The key architectural rule is:

> Consumers depend on the published public report contract, not on internal evaluation runtime models.

---

## Problem

AI Test Lab can already generate validated public reports, but downstream components still need a reliable way to consume them.

Without a dedicated reader, consumers could begin implementing their own logic such as:

```python
payload["summary"]["total"]
payload["results"][0]["test_id"]
```

This creates several risks:

* duplicated JSON parsing logic
* inconsistent schema-version handling
* direct dependence on raw report structure
* weaker validation guarantees
* difficulty introducing future report versions
* accidental coupling to internal implementation details

Sprint 11.15 creates a single consumption entry point.

---

## Architecture

The public report flow is now:

```text
Internal evaluation runtime
        ↓
Report mapper
        ↓
Public report model
        ↓
JSON serialization
        ↓
Versioned JSON Schema validation
        ↓
Public report file
        ↓
Report reader
        ↓
Contract validation
        ↓
Version-specific public model
        ↓
Safe downstream consumer
```

The report reader operates only on the published public contract.

It does not require internal evaluation runtime objects.

---

## Implementation

### New module

Added:

```text
src/report_reader.py
```

The reader exposes:

```python
load_report(path)
```

The operation performs the following sequence:

```text
Read UTF-8 file
    ↓
Parse JSON
    ↓
Require object root
    ↓
Validate declared public schema version
    ↓
Validate against published JSON Schema
    ↓
Select version-specific public Pydantic model
    ↓
Return frozen public report object
```

---

## Version-Aware Consumption

The reader maps supported public report versions to their corresponding Python consumer models.

Current supported version:

```text
1.0 → ReportV1
```

Future report versions can introduce additional consumer models without changing the behavior of existing v1.0 reports.

Example future direction:

```text
1.0 → ReportV1
1.1 → ReportV11
2.0 → ReportV2
```

No new report version was introduced in this sprint.

---

## Contract Validation

The reader reuses the existing:

```python
validate_report_payload()
```

function from:

```text
src/report_contract_validator.py
```

The existing JSON Schema remains the authoritative public interoperability contract.

The reader does not duplicate schema-validation logic.

---

## Public Python Model

After JSON Schema validation succeeds, the payload is converted into:

```python
ReportV1
```

from:

```text
src/report_schema.py
```

This provides downstream Python consumers with strongly structured access such as:

```python
report.schema_version
report.summary.total
report.results[0].test_id
```

instead of manually indexing raw JSON dictionaries.

---

## Dual Validation Boundary

Sprint 11.15 intentionally uses both JSON Schema and Pydantic validation.

### JSON Schema

JSON Schema protects the public interoperability boundary.

It is suitable for consumers such as:

```text
Website
API
CLI
External tools
Other programming languages
Future SDKs
```

### Pydantic

Pydantic provides the typed Python consumption model.

It supplies:

* structured field access
* immutable public models
* extra-field rejection
* Python runtime validation

These two mechanisms serve different architectural responsibilities.

---

## Error Handling

The reader introduces:

```python
ReportReadError
```

for failures related to reading or parsing the report itself.

Covered failure modes include:

* invalid JSON
* unreadable report file
* non-object JSON root
* inability to construct the public consumer model

Existing contract errors continue to use:

```python
ReportContractValidationError
```

This includes:

* missing schema version
* unsupported schema version
* JSON Schema contract violations

---

## IP Protection Boundary

Sprint 11.15 preserves the AI Test Lab IP protection architecture.

The reader consumes only public contract data.

Examples of valid public information include:

* schema version
* run metadata
* test results
* metric results
* engine execution results
* model summaries
* quality results
* public evidence fields

The reader does not depend on proprietary runtime implementation details such as:

* internal scoring algorithms
* orchestration state
* governance logic
* compliance reasoning
* commercial evidence intelligence
* proprietary evaluation strategy
* internal policy execution

The public report remains an explicit allow-list.

Unknown fields are rejected by the public Pydantic models.

---

## Tests

Added:

```text
tests/test_report_reader.py
```

The new test suite verifies:

1. valid report-v1.0 fixture loads successfully
2. invalid JSON is rejected
3. non-object JSON is rejected
4. missing schema version is rejected
5. unsupported schema version is rejected
6. contract violations are rejected

Focused test result:

```text
6 passed
```

Full regression result:

```text
216 passed
```

This confirms that report consumption was added without changing existing framework behavior.

---

## Files Added

```text
src/report_reader.py
tests/test_report_reader.py
docs/sprints/sprint11.15.md
```

Existing report-generation and validation modules remain unchanged.

---

## Acceptance Criteria

Sprint 11.15 is complete when:

* a valid report-v1.0 document can be loaded
* schema version is detected from the document
* unsupported versions are rejected
* published JSON Schema validation occurs before consumption
* malformed JSON is rejected predictably
* non-object JSON documents are rejected
* valid reports become typed public Python models
* internal runtime models are not required by the reader
* existing report-generation behavior is unchanged
* all focused reader tests pass
* the complete AI Test Lab test suite remains green

Status:

```text
Focused tests: 6 passed
Full suite: 216 passed
Regression: clean
```

---

## Result

Sprint 11.15 establishes the public report consumption boundary.

AI Test Lab now has both sides of the versioned report contract:

```text
Producer
   ↓
Published contract
   ↓
Consumer
```

This creates a durable foundation for future consumers such as the AI Test Lab website, CLI inspection tools, APIs, SDKs, evidence systems, and future report-version evolution without coupling those systems to proprietary evaluation internals.
