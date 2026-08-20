# Sprint 11.30 — Public Report Capability Discovery

## Goal

Sprint 11.30 adds a safe public capability-discovery layer for AI Test Lab reports.

The purpose is to let consumers determine which public report features are available for a given schema version without inspecting internal implementation details.

This continues the public-report hardening work from the previous sprints:

* Sprint 11.27 — schema enforcement
* Sprint 11.28 — release readiness
* Sprint 11.29 — public report v1 contract documentation
* Sprint 11.30 — capability discovery

## Problem

Before this sprint, AI Test Lab already knew which public report schema versions were supported.

For example, schema version `1.0` was registered in the report contract validator.

However, consumers did not have a dedicated public API for discovering what functionality was available for that version.

A consumer should not have to guess whether a report supports summary generation, report decisions, assessments, or other public behavior.

At the same time, capability discovery must not expose proprietary or internal implementation details.

## Design

Sprint 11.30 introduces:

```text
src/report_capabilities.py
```

This module defines the approved public capabilities for each supported report schema version.

For public report version `1.0`, the capability set is:

```python
(
    "report",
    "summary",
    "decision",
    "assessment",
)
```

These names correspond to existing public consumer-facing functionality.

They intentionally describe what a consumer can use, not how AI Test Lab implements that functionality internally.

## Public API

The capability module exposes three functions.

### `report_capabilities(schema_version)`

Returns the public capabilities available for a schema version.

Example:

```python
report_capabilities("1.0")
```

returns:

```python
(
    "report",
    "summary",
    "decision",
    "assessment",
)
```

Unsupported versions return an empty tuple.

### `report_supports_capability(schema_version, capability)`

Returns a Boolean indicating whether a specific capability is supported.

Example:

```python
report_supports_capability("1.0", "summary")
```

returns:

```python
True
```

An unknown or private capability returns:

```python
False
```

### `capability_schema_versions()`

Returns the schema versions that publish capability metadata.

This allows the test suite to verify that capability discovery remains synchronized with the official public report schema-version catalog.

## IP Protection Boundary

Capability discovery is intentionally limited to approved public functionality.

It does not expose:

* evaluation engine internals
* proprietary scoring strategies
* governance algorithms
* evidence-intelligence logic
* orchestration internals
* commercial implementation details
* internal runtime modules

For example:

```python
report_supports_capability(
    "1.0",
    "internal_scoring_engine",
)
```

returns:

```python
False
```

This preserves the existing AI Test Lab public/private architecture boundary.

## Version Synchronization

AI Test Lab already maintains the official supported report versions in:

```text
src/report_contract_validator.py
```

Sprint 11.30 adds a test ensuring that the capability catalog and the supported schema catalog remain synchronized.

Conceptually:

```text
supported report schema versions
            ==
capability metadata versions
```

This prevents capability metadata from accidentally advertising an unpublished or unsupported report version.

## Tests Added

A new test module was added:

```text
tests/test_report_capability_discovery.py
```

The test suite verifies:

1. Supported report versions have capability metadata.
2. Unsupported versions return no capabilities.
3. Unsupported versions cannot report support for a capability.
4. Public report v1.0 advertises the expected capabilities.
5. Known public capabilities return `True`.
6. Unknown or internal capabilities return `False`.
7. Capability schema versions exactly match supported report schema versions.

## Focused Validation

The report capability, consumer, and version tests were executed together:

```text
23 passed in 0.24s
```

The focused run included:

```text
tests/test_report_version_capabilities.py
tests/test_report_consumer.py
tests/test_report_capability_discovery.py
```

## Full Regression Validation

The complete AI Test Lab test suite was also executed:

```text
288 passed in 10.05s
```

This confirms that the new capability-discovery layer does not introduce regressions into the wider framework.

## Result

Sprint 11.30 establishes a small, explicit, version-aware public capability-discovery API.

Consumers can now determine what a report version supports without relying on internal implementation details.

The public report contract remains protected, deterministic, and aligned with the project's IP Protection Boundary.
