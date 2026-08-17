# Sprint 11.19 — Public Report Assessment

## Goal

Add a deterministic public assessment layer that explains an existing
`ReportDecision` using only information already exposed by `ReportSummary`.

The assessment layer must not recalculate evaluation, quality-gate, metric,
engine, governance, compliance, or proprietary scoring logic.

## Architecture

The public consumer chain is:

`Public Report → ReportSummary → ReportDecision → ReportAssessment`

`ReportDecision` remains authoritative for the overall verdict.

`ReportAssessment` explains that verdict with stable public findings.

## Implementation

Added:

- `src/report_assessment.py`
- `tests/test_report_assessment.py`
- `docs/sprints/sprint11.19.md`

### FindingLevel

Public finding levels:

- `info`
- `warning`
- `failure`
- `error`

Finding severity is explanatory and does not replace `DecisionStatus`.

### AssessmentFinding

Each finding can expose only public consumer information such as:

- stable finding code
- severity
- human-readable message
- test ID
- engine name
- metric name
- metric score
- metric threshold

### ReportAssessment

The assessment exposes:

- existing public decision status
- report schema version
- generation timestamp
- total / passed / failed / error counts
- human-readable assessment summary
- deterministic public findings

### assess_report()

`assess_report()` accepts a `ReportSummary`.

It first calls `decide_report()` and therefore reuses Sprint 11.18 decision
semantics instead of creating a second verdict algorithm.

It then derives explanations from public summary evidence:

- overall pass/fail/error/no-data context
- failed public test IDs
- failed public metric results
- observable engine failures
- unexpected public passes

## Decision Invariant

An assessment finding never overrides the public decision.

For example, an observable engine failure may produce a warning finding while
the overall public decision remains `PASS` if that is the decision produced by
Sprint 11.18.

This preserves the existing architectural rule:

> Public consumers explain published decisions; they do not recreate private
> evaluation policy.

## Determinism

Failed test, metric, and engine findings are sorted before construction.

The same public summary therefore produces findings in the same order,
independent of incidental input ordering.

## IP Protection Boundary

The assessment module imports only:

- `ReportSummary`
- `ReportDecision`
- public summary evidence models

It does not import or expose:

- evaluation pipeline internals
- engine implementations
- metric configuration logic
- quality-gate computation
- evaluation profiles
- governance rules
- compliance reasoning
- proprietary weighting or scoring
- orchestration state
- commercial evidence intelligence

The assessment is therefore a public consumer capability, not an internal
runtime capability.

## Tests

Focused coverage verifies:

1. passing assessment
2. failed-test explanation
3. failed-metric explanation
4. engine failure warning without verdict override
5. error assessment
6. no-data assessment
7. deterministic finding order
8. JSON-compatible, allow-listed public output
9. unknown decision state rejection

## Acceptance Criteria

Sprint 11.19 is complete when:

- assessment reuses `decide_report()`
- no second verdict algorithm is introduced
- public findings explain observable report evidence
- engine warnings do not override published decisions
- finding order is deterministic
- output is JSON serializable
- only allow-listed public assessment fields are exposed
- internal runtime models are not imported
- focused assessment tests pass
- the complete regression suite remains green

## Result

AI Test Lab now has a stable public path from evidence to explanation:

`Report → Inspection → Summary → Decision → Assessment`

Downstream systems can consume both a machine-readable decision and a
human-readable public explanation without reproducing AI Test Lab's
proprietary evaluation internals.
