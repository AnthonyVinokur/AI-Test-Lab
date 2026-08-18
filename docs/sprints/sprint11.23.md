# Sprint 11.23 — Public Report Compatibility Policy

## Objective

Define and regression-test the compatibility policy for the versioned public report contract.

Sprint 11.23 confirms that published report schema versions are immutable contracts. Structural changes to the public report require a new schema version rather than modifying an existing published version.

## Background

The AI Test Lab public report architecture already provides:

- explicit `schema_version` declaration
- version-aware JSON Schema validation
- version-aware consumer model dispatch
- strict rejection of unknown public fields
- Pydantic consumer models configured with `extra="forbid"`
- explicit producer-to-consumer contract validation

Sprint 11.23 does not add a new compatibility abstraction. Instead, it freezes the existing behavior through dedicated regression tests.

## Compatibility Policy

Public Report v1.0 is immutable.

The following changes are breaking changes and therefore require a new public schema version:

- adding a new public field
- removing a required public field
- renaming a public field
- changing a public field type
- changing the meaning of an existing public field
- changing the declared schema version

Internal implementation changes remain allowed as long as they do not alter the published public contract.

Internal or proprietary implementation state must never be exposed through public report evolution.

## Strict Contract Boundary

The published JSON Schema uses:

`"additionalProperties": false`

for public report objects.

The public Pydantic models also use:

`extra="forbid"`

This provides defense in depth against accidental contract expansion or leakage of internal implementation state.

The `runtime_options` object remains intentionally extensible at the JSON object level, but public serialization is still responsible for allow-listing safe keys before data crosses the public boundary.

## Tests Added

`tests/test_report_compatibility.py`

The compatibility regression suite verifies that:

1. Public Report v1.0 is currently the only supported schema version.
2. Unknown root fields are rejected.
3. Unknown nested result fields are rejected.
4. Removing a required field is rejected.
5. Renaming a required field is rejected.
6. Changing a public field type is rejected.
7. Unpublished future schema versions are rejected.

## Architectural Result

No production-code changes were required.

The existing version-aware report validator, JSON Schema, report reader, and strict consumer models already enforce the intended compatibility policy.

Sprint 11.23 therefore strengthens the architecture by documenting and regression-testing the contract evolution rules rather than introducing redundant compatibility infrastructure.

## Verification

```text
7 passed in 0.12s