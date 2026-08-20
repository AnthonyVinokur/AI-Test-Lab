# Sprint 11.31 — Public Report Capability Consumption

## Objective

Sprint 11.31 adds a consumer-facing capability check for public reports.

Sprint 11.30 introduced public capability discovery by mapping supported report schema versions to a controlled set of public capabilities:

* `report`
* `summary`
* `decision`
* `assessment`

Sprint 11.31 builds on that foundation by allowing a consumer to ask whether a specific public report supports a specific capability.

The new behavior is intentionally thin and delegates to the existing Sprint 11.30 capability catalog so that AI Test Lab maintains one authoritative source of truth.

## Public API

The new consumer API is:

```python
supports_capability(report, capability)
```

Example:

```python
report = {
    "schema_version": "1.0",
}

supports_capability(report, "summary")
```

Result:

```python
True
```

The helper reads the public report's `schema_version` and delegates capability resolution to the existing capability-discovery layer.

Conceptually:

```text
Public report
    |
    +-- schema_version
            |
            v
supports_capability(report, capability)
            |
            v
report_supports_capability(schema_version, capability)
            |
            v
report_capabilities(schema_version)
            |
            v
_REPORT_CAPABILITIES
```

This avoids creating a second capability catalog and prevents public capability definitions from drifting between discovery and consumption behavior.

## Behavior

For a supported schema version and a known public capability, the function returns `True`.

For example:

```python
supports_capability(
    {"schema_version": "1.0"},
    "summary",
)
```

returns:

```python
True
```

An unsupported report schema version fails closed and returns `False` for capability checks.

For example:

```python
supports_capability(
    {"schema_version": "9.0"},
    "summary",
)
```

returns:

```python
False
```

An unknown or internal capability is not exposed and also returns `False`.

For example:

```python
supports_capability(
    {"schema_version": "1.0"},
    "internal_scoring_engine",
)
```

returns:

```python
False
```

Malformed consumer input is rejected explicitly.

A missing or non-string `schema_version` raises `ValueError`.

A non-string capability value also raises `ValueError`.

## IP Protection Boundary

Sprint 11.31 preserves the AI Test Lab public/private architecture boundary.

The public consumer may determine whether a report supports documented public concepts such as:

```text
report
summary
decision
assessment
```

The consumer does not receive information about proprietary implementation details such as:

```text
evaluation engines
scoring algorithms
governance logic
evidence-intelligence logic
orchestration
internal policy rules
commercial implementation metadata
```

Capability consumption therefore answers:

> What public behavior is available?

It does not answer:

> How does AI Test Lab internally implement that behavior?

This distinction protects proprietary framework behavior while still providing a stable and useful public contract.

## Implementation

Sprint 11.31 extends:

```text
src/report_capabilities.py
```

with the consumer helper:

```python
supports_capability(report, capability)
```

The helper does not inspect a report-provided capability list and does not define its own capability catalog.

Instead, it extracts `schema_version` and delegates to:

```python
report_supports_capability(...)
```

which already uses the authoritative `_REPORT_CAPABILITIES` mapping introduced in Sprint 11.30.

## Tests

Sprint 11.31 adds:

```text
tests/test_report_capability_consumption.py
```

The new test coverage verifies:

* all four public v1 capabilities can be consumed;
* unsupported schema versions expose no capability;
* unknown/internal capability names fail closed;
* missing `schema_version` is rejected;
* non-string `schema_version` is rejected;
* non-string capability input is rejected.

The parametrized public-capability test expands into four independent test cases.

Sprint 11.31 adds 9 test cases in total.

Existing Sprint 11.30 capability-discovery behavior remains unchanged.

## Validation Results

Focused Sprint 11.31 capability-consumption tests:

```text
9 passed
```

Sprint 11.30 capability-discovery regression tests:

```text
7 passed
```

Report-version capability tests:

```text
4 passed
```

Full project regression suite:

```text
297 passed
```

The pre-Sprint 11.31 baseline was:

```text
288 passed
```

Therefore Sprint 11.31 adds 9 tests without breaking the existing suite.

Patch validation also completed successfully:

```text
git diff --check
```

with no reported whitespace errors.

## Definition of Done

Sprint 11.31 is complete when:

* a consumer-facing capability API exists;
* capability consumption delegates to the Sprint 11.30 authoritative catalog;
* no duplicate public capability catalog is introduced;
* unsupported versions fail closed;
* unknown/internal capability names are not exposed;
* malformed consumer inputs are rejected;
* proprietary implementation details remain behind the IP Protection Boundary;
* focused tests pass;
* the full regression suite passes;
* sprint documentation records the public contract and architectural decision.

At implementation validation, all of these conditions are satisfied.
