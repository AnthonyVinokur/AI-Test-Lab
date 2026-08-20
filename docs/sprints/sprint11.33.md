Sprint 11.33 — Public Report Schema Compatibility
Objective

Sprint 11.33 introduces an explicit public compatibility contract for report schema versions.

Previous sprints established the public report contract, capability discovery, capability consumption, and capability hardening.

Sprint 11.33 answers a different consumer question:

Does this AI Test Lab consumer support the schema version used by this public report?

This keeps schema compatibility separate from capability support and makes the public contract easier to consume safely.

Existing Architecture

Public report capabilities are defined by the authoritative capability catalog:

src/report_capabilities.py

The current public schema catalog contains:

1.0

with the public capabilities:

report
summary
decision
assessment

The report itself does not control schema compatibility or capability authority.

New Compatibility API

Sprint 11.33 adds:

supports_schema_version(schema_version)

This function determines whether a schema version is recognized by the public report capability catalog.

Example:

supports_schema_version("1.0")

returns:

True

while:

supports_schema_version("2.0")

returns:

False

Sprint 11.33 also adds:

supports_report_schema(report)

This consumer-facing helper reads the report's schema_version and determines whether that schema is supported.

Example:

report = {
    "schema_version": "1.0",
}


supports_report_schema(report)

returns:

True
Compatibility Architecture

The compatibility path is:

Public report
    |
    +-- schema_version
            |
            v
supports_report_schema(report)
            |
            v
supports_schema_version(schema_version)
            |
            v
capability_schema_versions()
            |
            v
_REPORT_CAPABILITIES

The authoritative compatibility decision therefore remains inside the controlled public catalog.

Contract Behavior

Sprint 11.33 establishes the following behavior.

Supported Schema Versions

Known schema versions are accepted.

For example:

supports_schema_version("1.0")

returns True.

Unsupported Schema Versions

Unknown schema versions are rejected cleanly without raising an error.

For example:

supports_schema_version("999.0")

returns False.

This allows consumers to check compatibility before attempting to process a report.

Report-Level Compatibility

Consumers can check an entire report using:

supports_report_schema(report)

The function evaluates only the authoritative schema_version.

Invalid Schema Version Types

A public report schema version must be a string.

For example:

{
    "schema_version": 1,
}

raises:

ValueError: Public report schema_version must be a string.

This matches the validation behavior already used by the public capability-consumption API.

Contract Invariant

Sprint 11.33 adds an important cross-layer invariant:

Every schema version advertised by capability_schema_versions() must also be recognized by supports_schema_version().

This prevents schema discovery and compatibility checks from drifting apart.

Security and IP Protection Boundary

Sprint 11.33 does not expose implementation details.

The public compatibility surface contains only:

schema version
supported / unsupported decision

It does not expose:

internal evaluation engines
proprietary scoring logic
governance algorithms
evidence-intelligence logic
internal orchestration
commercial implementation details
internal policy mechanisms

Compatibility remains a public contract concern rather than an internal implementation concern.

Implementation

Sprint 11.33 updates:

src/report_capabilities.py

with two public helpers:

supports_schema_version()
supports_report_schema()

Sprint 11.33 also adds:

tests/test_report_schema_compatibility.py
Tests Added

Six tests were added:

A known schema version is supported.
An unknown schema version is not supported.
Every advertised schema version is recognized by the compatibility API.
A report using a supported schema is compatible.
A report using an unknown schema is not compatible.
A report schema version must be a string.
Focused Validation

The Sprint 11.33 compatibility test module completed successfully:

6 passed in 0.05s
Full Regression Validation

The complete AI Test Lab test suite completed successfully:

308 passed in 9.99s

The pre-Sprint 11.33 baseline was:

302 passed

Sprint 11.33 therefore adds six tests without introducing regressions.

Result

Sprint 11.33 gives public-report consumers an explicit way to determine schema compatibility.

Schema compatibility is now separated from capability support, based on the authoritative public catalog, validated by contract tests, and protected by the existing AI Test Lab public/private boundary.