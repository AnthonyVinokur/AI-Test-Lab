# Sprint 11.17 — Public Report Summary Boundary

## Goal

Add a small, stable consumer-facing summary derived only from the versioned
public report contract.

Sprint 11.17 does not create another evaluation path. It consumes the report
that the framework already publishes.

## Architecture

Evaluation runtime -> explicit public transformation -> report-v1.0
-> report inspection -> public summary -> CLI / website / CI / future API

The summary layer must not import or serialize internal evaluation-pipeline,
engine, governance, scoring, evidence-intelligence, or orchestration models.

## Implementation

`src/report_summary.py` introduces:

- `ReportSummary`
- `MetricFailureSummary`
- `EngineFailureSummary`
- `summarize_report()`

The summary exposes only public contract information required by downstream
consumers:

- schema version and generation time
- aggregate pass/fail/error state
- test counts and pass rate
- public evaluation profile names
- failed public test identifiers
- failed metric results
- public engine execution failures

## IP protection boundary

The report remains the contract.

Consumers do not receive references to runtime objects and do not need to know
how internal scoring, orchestration, governance, evidence intelligence, or
commercial logic works.

## Out of scope

- dashboard implementation
- persistence/database work
- website wiring
- new CLI commands
- APIs
- new evaluation engines
- governance or compliance scoring
- proprietary evidence intelligence

## Verification

Run:

```powershell
pytest .\tests\test_report_summary.py -v
pytest -q
```

## Definition of done

Sprint 11.17 is complete when a valid public report can be reduced to a small
stable consumer summary, failed tests/metrics and engine failures are visible,
the output is JSON serializable, and the existing test suite remains green.
