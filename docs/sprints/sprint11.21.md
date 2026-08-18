# Sprint 11.21 — Public Report Consumer Facade

## Goal

Add a small public consumer facade that gives downstream applications one safe entry point for loading and interpreting an AI Test Lab public report.

The facade must compose the existing public report capabilities without recreating evaluation, metric, quality-gate, governance, scoring, engine, or orchestration logic.

## Architecture

The public consumer flow is:

```text
Public JSON Report
        |
        v
load_report()
        |
        v
Validated Public Report
        |
        v
summarize_report()
        |
        v
ReportSummary
        |
        +----------------+
        |                |
        v                v
decide_report()      assess_report()
        |                |
        v                v
ReportDecision     ReportAssessment
        \                /
         \              /
          v            v
          ReportConsumption
```

`ReportConsumption` is a convenience facade only.

It does not become a new evaluation or decision engine.

## Implementation

Added:

* `src/report_consumer.py`
* `tests/test_report_consumer.py`
* `docs/sprints/sprint11.21.md`

### ReportConsumption

`ReportConsumption` is an immutable public container that exposes:

* validated public report
* public report summary
* public report decision
* public report assessment

It is implemented as a frozen, slotted dataclass.

### consume_report()

`consume_report()` accepts a report file path and performs the approved public consumption sequence:

1. load and validate the public report;
2. convert the validated public DTO to public JSON-compatible data;
3. build the existing `ReportSummary`;
4. derive the existing `ReportDecision`;
5. derive the existing `ReportAssessment`;
6. return all approved public outputs in one `ReportConsumption` object.

The function does not independently calculate verdicts, metrics, thresholds, quality gates, or assessment findings.

## Composition Invariant

Sprint 11.21 preserves the following architectural rule:

> The consumer facade composes existing public contracts; it does not recreate private runtime behavior.

The existing modules remain authoritative:

* `report_reader.py` — report loading and contract validation
* `report_summary.py` — public summary construction
* `report_decision.py` — public decision semantics
* `report_assessment.py` — public explanation semantics

The facade only orchestrates those approved capabilities.

## IP Protection Boundary

The consumer facade is restricted to the public-report side of the framework.

It does not import or depend on:

* evaluation pipeline internals
* evaluation engines
* evaluation profiles
* evaluation configuration
* proprietary scoring
* quality-gate computation
* governance rules
* compliance reasoning
* orchestration state
* internal runtime models

A regression test inspects the module imports and prevents private runtime modules from being introduced into the public facade accidentally.

This preserves the default-private architecture established by the earlier report-boundary sprints.

## Error Handling

The facade reuses existing public report errors rather than introducing an unrelated error system.

Malformed JSON is rejected through `ReportReadError`.

Reports that violate the published public schema are rejected through `ReportContractValidationError`.

The facade does not suppress or replace those established public validation boundaries.

## Tests

Focused coverage verifies:

1. valid report consumption;
2. public output consistency;
3. immutable `ReportConsumption`;
4. malformed JSON rejection;
5. invalid public contract rejection;
6. protection against private runtime imports.

Focused Sprint 11.21 tests:

```text
6 passed
```

Full project regression suite:

```text
255 passed in 10.11s
```

## Acceptance Criteria

Sprint 11.21 is complete when:

* one public high-level report-consumption entry point exists;
* the facade reuses existing reader, summary, decision, and assessment behavior;
* no duplicate decision algorithm is introduced;
* no duplicate assessment algorithm is introduced;
* public contract validation remains authoritative;
* malformed reports fail safely;
* the consumption object is immutable;
* private runtime modules are excluded from the facade;
* focused consumer tests pass;
* the complete project regression suite remains green.

## Result

AI Test Lab now provides a stable public integration seam:

```text
Public Report
     |
     v
consume_report()
     |
     v
ReportConsumption
     |
     +--> Report
     +--> Summary
     +--> Decision
     +--> Assessment
```

Downstream applications can consume validated AI Test Lab evidence through one small public interface without needing knowledge of the framework's proprietary evaluation internals.
