# Sprint 11.24 — Public Report Version Capability Introspection

## Objective

Provide a small public capability API that allows consumers to determine whether the current AI Test Lab runtime supports a specific public report schema version.

## Background

The public report architecture already provides:

- explicit `schema_version` declarations
- version-aware JSON Schema validation
- version-aware consumer model dispatch
- strict rejection of unsupported schema versions
- immutable published report contracts
- public/private architecture boundaries

Sprint 11.23 established and regression-tested the compatibility policy.

Sprint 11.24 adds a public way to inspect version support without requiring callers to access private implementation details or deliberately trigger validation failures.

## Capability Added

The report contract validator now exposes:

`is_report_schema_version_supported(schema_version)`

Example:

```python
is_report_schema_version_supported("1.0")
# True

is_report_schema_version_supported("1.1")
# False