# Sprint 11.18 — Public Report Decision

## Goal

Add a small public decision layer that converts a `ReportSummary` into a stable,
machine-readable consumer decision.

The decision layer must consume only the public summary contract and must not
recalculate evaluation, metric, engine, quality-gate, governance, or other
internal runtime logic.

## Motivation

Sprint 11.15 added version-aware public report consumption.

Sprint 11.16 added public report inspection.

Sprint 11.17 added a stable public report summary.

Sprint 11.18 completes the next consumer boundary by allowing downstream
systems to answer:

> What decision can be made from this report summary?

This enables future consumers such as CI/CD systems, APIs, websites, and CLI
tools to react to evaluation results without depending on proprietary internal
runtime models.

## Public Decision States

The decision layer maps public summary states as follows:

- `passed` → `pass`
- `failed` → `fail`
- `error` → `error`
- `empty` → `no_data`

The decision layer deliberately trusts `ReportSummary.overall_status`.

It does not independently recalculate the report verdict.

## Implementation

Added:

- `src/report_decision.py`
- `tests/test_report_decision.py`

### DecisionStatus

`DecisionStatus` provides four stable public states:

- `PASS`
- `FAIL`
- `ERROR`
- `NO_DATA`

### ReportDecision

`ReportDecision` exposes a small immutable consumer model containing:

- decision status
- schema version
- report generation timestamp
- total tests
- passed tests
- failed tests
- errors

It also provides `to_dict()` for JSON-compatible serialization.

### decide_report()

`decide_report()` accepts a `ReportSummary` and translates its
`overall_status` into a public `DecisionStatus`.

Unknown summary states are rejected with `ValueError`.

## IP Protection Boundary

Sprint 11.18 preserves the public/private architecture boundary.

The decision module does not import or expose:

- evaluation engines
- evaluation pipeline internals
- metric configuration
- metric thresholds
- evaluation profiles
- governance logic
- proprietary scoring logic
- quality-gate computation

The public dependency remains:

`Public Report → ReportSummary → ReportDecision`

This allows downstream systems to consume AI Test Lab decisions without
learning how those decisions were internally produced.

## Engine Failure Semantics

An observable engine failure does not automatically override a public
`passed` summary.

The decision layer trusts the upstream public summary contract rather than
inventing additional decision policy.

This behavior is explicitly covered by tests.

## Tests

Sprint 11.18 adds seven focused tests covering:

1. Passed summary → PASS
2. Failed summary → FAIL
3. Error summary → ERROR
4. Empty summary → NO_DATA
5. Unknown status rejection
6. Engine failure does not override a passed summary
7. JSON-compatible decision serialization

Validation results:

- Report summary + decision tests: 13 passed
- Full test suite: 236 passed

## Result

AI Test Lab now provides a stable public path from evaluation evidence to a
machine-readable consumer decision:

`Report → Inspection → Summary → Decision`

Downstream systems can consume that decision without importing or reproducing
AI Test Lab's proprietary evaluation runtime.