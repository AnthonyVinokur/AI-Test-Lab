# Sprint 11.32 — Public Report Capability Contract Hardening

## Objective

Sprint 11.32 hardens the public report capability contract introduced in Sprints 11.30 and 11.31.

Sprint 11.30 added public capability discovery.

Sprint 11.31 added consumer-facing capability checks.

Sprint 11.32 verifies that these layers remain synchronized and that public reports cannot redefine, expand, or reduce their own capability contract.

The sprint focuses on contract invariants rather than adding new runtime behavior.

## Existing Capability Architecture

Public capability handling follows this path:

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

The authoritative source of capability information remains:

```text
src/report_capabilities.py
```

The public report itself does not define capability authority.

## Contract Invariants

Sprint 11.32 introduces tests that protect five important invariants.

### 1. Advertised Capabilities Must Be Supported

Every capability returned by:

```python
report_capabilities(schema_version)
```

must also be accepted by:

```python
report_supports_capability(
    schema_version,
    capability,
)
```

This prevents discovery and version-level capability checks from drifting apart.

### 2. Advertised Capabilities Must Be Consumable

Every capability advertised for a supported schema version must also be available through:

```python
supports_capability(report, capability)
```

This guarantees consistency between capability discovery and consumer behavior.

### 3. Capability Catalog Entries Must Be Valid

Each public capability catalog must:

* contain at least one capability;
* contain unique capability names;
* contain only strings;
* contain no empty or whitespace-only capability names.

This prevents malformed capability metadata from becoming part of the public contract.

### 4. Reports Cannot Self-Declare Private Capabilities

A report may contain arbitrary additional fields.

For example:

```python
{
    "schema_version": "1.0",
    "capabilities": (
        "internal_scoring_engine",
    ),
}
```

However, this does not grant access to that capability.

The consumer API still resolves capability support against the authoritative public capability catalog.

Therefore:

```python
supports_capability(
    report,
    "internal_scoring_engine",
)
```

returns:

```python
False
```

### 5. Reports Cannot Remove Public Capabilities

A report also cannot reduce the public contract by providing misleading capability metadata.

For example:

```python
{
    "schema_version": "1.0",
    "capabilities": (),
}
```

does not remove the public `summary` capability.

The authoritative schema-level contract still determines the result.

Therefore:

```python
supports_capability(
    report,
    "summary",
)
```

returns:

```python
True
```

## Security and IP Protection Boundary

Sprint 11.32 reinforces an important architectural rule:

> Reports contain data. Reports do not define their own public contract.

Capability authority remains inside the controlled capability catalog.

This prevents report-provided data from exposing or enabling proprietary functionality such as:

* internal evaluation engines;
* proprietary scoring logic;
* governance algorithms;
* evidence-intelligence logic;
* orchestration internals;
* commercial implementation details;
* internal policy mechanisms.

The public contract continues to expose only approved consumer-facing capabilities.

## Implementation

Sprint 11.32 adds:

```text
tests/test_report_capability_contract.py
```

No production-code changes were required.

The existing implementation already satisfied the new contract-hardening requirements.

## Tests Added

Five new tests were added:

1. Every advertised capability is supported by the version-level API.
2. Every advertised capability is consumable through the report-level API.
3. Public capability catalogs contain unique, non-empty strings.
4. Report-supplied capability metadata cannot grant a private capability.
5. Report-supplied capability metadata cannot remove an approved public capability.

## Focused Validation

The new Sprint 11.32 test module completed successfully:

```text
5 passed in 0.07s
```

## Full Regression Validation

The complete AI Test Lab test suite completed successfully:

```text
302 passed in 9.88s
```

The pre-Sprint 11.32 baseline was:

```text
297 passed
```

Sprint 11.32 therefore adds 5 tests without introducing regressions.

## Result

Sprint 11.32 strengthens the public report capability contract without expanding the public API.

Capability discovery, version-level capability checks, and report-level capability consumption are now protected by explicit cross-layer invariants.

The public capability catalog remains authoritative, report-supplied metadata cannot redefine the contract, and proprietary implementation details remain behind the AI Test Lab IP Protection Boundary.
