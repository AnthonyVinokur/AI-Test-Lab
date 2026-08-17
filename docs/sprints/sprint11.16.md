# Sprint 11.16 — Public Report Inspection

## Objective

Sprint 11.16 adds a read-only inspection layer for validated AI Test Lab public reports.

Sprint 11.15 established the version-aware report consumption boundary. Sprint 11.16 builds on that boundary by allowing downstream consumers to inspect report evidence without depending on internal runtime models or manually traversing raw JSON.

The architectural rule is:

> Public report consumers inspect validated public contract objects, not internal evaluation state.

---

## Problem

AI Test Lab can now load a validated public report through:

```python
load_report(path)
```

The returned `ReportV1` object contains test results, evaluation metrics, engine execution results, model information, and summary data.

Without a dedicated inspection layer, downstream consumers would need to repeatedly implement filtering logic such as:

```python
[
    result
    for result in report.results
    if not result.passed
]
```

or nested traversal such as:

```python
for result in report.results:
    for metric in result.evaluation_results:
        ...
```

That creates duplicated consumer logic and increases the risk of inconsistent interpretation.

Sprint 11.16 introduces a small, stable inspection API over the public report contract.

---

## Architecture

The consumption path is now:

```text
Versioned JSON Report
        ↓
report_reader.py
        ↓
Contract Validation
        ↓
ReportV1
        ↓
report_inspector.py
        ↓
Read-Only Public Queries
        ↓
CLI / Website / API / Future SDK
```

The inspection layer does not convert public report data back into internal `TestResult` models.

---

## Implementation

Added:

```text
src/report_inspector.py
```

The module provides read-only helper functions for common evidence inspection operations.

### Passing results

```python
get_passing_results(report)
```

Returns public test results whose `passed` field is `True`.

### Failed results

```python
get_failed_results(report)
```

Returns public test results whose `passed` field is `False`.

### Results for a model

```python
get_results_for_model(report, model)
```

Returns test results associated with a specific model.

Unknown model names return an empty list.

### Engine failures

```python
get_engine_failures(report)
```

Returns failed engine execution records together with the parent test result.

The parent test result is preserved so the engine failure retains provenance.

### Metric results

```python
get_metric_results(report, metric_name)
```

Returns metric results matching a requested public metric name together with the parent test result.

Unknown metric names return an empty list.

---

## Provenance Preservation

Nested evidence is returned together with its parent test result.

For example:

```text
Test Result
    ↓
Metric Result
```

and:

```text
Test Result
    ↓
Engine Execution Result
```

This prevents downstream consumers from receiving detached evidence with no information about which test produced it.

A metric score by itself is incomplete evidence.

Sprint 11.16 therefore preserves the relationship between the evidence and its originating test.

---

## Separation From Producer Analytics

Existing:

```text
src/report_analytics.py
```

operates on internal `TestResult` models and calculates producer-side model summaries.

Sprint 11.16 does not reuse or modify that module.

The architecture intentionally remains separated:

```text
INTERNAL PRODUCER SIDE

TestResult
    ↓
report_analytics.py
    ↓
Report generation
    ↓
Public contract

---------------- PUBLIC BOUNDARY ----------------

ReportV1
    ↓
report_inspector.py
    ↓
Downstream consumers
```

The public report is not converted back into internal runtime models.

---

## Existing Data Is Not Recalculated

The public report already contains fields such as:

```python
report.summary
report.models
report.model_comparison
report.highlights
```

Sprint 11.16 does not add wrappers for these fields and does not recalculate those values.

The inspection layer only adds operations that simplify evidence filtering and traversal.

This keeps the API surface small.

---

## IP Protection Boundary

The inspection layer depends only on public report contract models.

It does not import or depend on:

* internal `TestResult`
* internal `ModelSummary`
* evaluation orchestration state
* proprietary scoring algorithms
* governance logic
* compliance reasoning
* proprietary evidence intelligence
* internal policy execution

This preserves the AI Test Lab public/private architecture boundary.

---

## Tests

Added:

```text
tests/test_report_inspector.py
```

The focused test suite verifies:

1. passing results are returned
2. failed-results query returns empty for a passing fixture
3. model-specific results are returned
4. unknown models return an empty list
5. failed engine executions are returned with parent provenance
6. metric results are returned with parent provenance
7. unknown metrics return an empty list

Focused result:

```text
7 passed
```

Expected full regression result:

```text
223 passed
```

---

## Files Added

```text
src/report_inspector.py
tests/test_report_inspector.py
docs/sprints/sprint11.16.md
```

---

## Acceptance Criteria

Sprint 11.16 is complete when:

* validated public reports can be inspected without raw dictionary traversal
* passing results can be queried
* failed results can be queried
* results can be filtered by model
* engine failures can be inspected
* metric results can be inspected
* nested evidence retains parent-test provenance
* unknown model and metric queries return empty results
* producer-side analytics remain unchanged
* internal runtime models are not required
* all focused tests pass
* the complete regression suite remains green

---

## Result

Sprint 11.16 establishes a stable public report inspection layer.

AI Test Lab now supports the following consumer flow:

```text
Load
  ↓
Validate
  ↓
Inspect
  ↓
Consume
```

This creates a clean foundation for future CLI inspection commands, website evidence views, APIs, and SDK consumers without exposing or coupling those systems to AI Test Lab's proprietary runtime internals.
