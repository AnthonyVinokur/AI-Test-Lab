# Sprint 11.25 — Public Consumer Version Boundary Hardening

## Objective

Verify that the public report consumer rejects unsupported report schema versions through the complete public consumption path.

## Background

Earlier sprints established:

- explicit public report schema versioning
- version-aware schema validation
- consumer model dispatch
- unsupported-version rejection
- public version capability introspection

Sprint 11.25 adds regression coverage at the top-level consumer facade.

## Behavior Protected

The public `consume_report()` API must reject reports whose `schema_version` is not supported.

Example:

```json
{
  "schema_version": "9.0"
}