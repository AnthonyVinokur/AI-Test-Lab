# Sprint 11.34 — Public Report Contract Identity

## Goal

Establish a stable public identity for the AI Test Lab public report contract without modifying the frozen Public Report v1 payload.

## Problem

A schema version such as `1.0` tells consumers which schema revision a report uses, but consumers also need a stable way to identify which public contract that version belongs to.

Contract identity must not depend on internal Python class names, package structure, evaluator implementations, or proprietary runtime details.

## Design

Sprint 11.34 introduces a public contract identity layer outside the serialized `ReportV1` payload.

The stable public contract name is:

`ai-test-lab.public-report`

A supported schema version maps deterministically to:

- contract name
- schema version

For Public Report v1:

`ai-test-lab.public-report` + `1.0`

## Architecture

The identity layer reuses the existing report schema-version authority rather than maintaining an independent version catalog.

This prevents contract identity support from drifting away from the versions recognized by the public report validator.

## Compatibility

Sprint 11.34 does not add fields to `ReportV1`.

The existing Public Report v1 JSON structure and canonical JSON Schema remain unchanged.

This preserves the frozen v1 contract while adding contract identity as a separate public capability.

## IP Protection Boundary

Contract identity exposes only stable public contract metadata.

It does not expose:

- internal class names
- package/module structure
- evaluation implementation details
- internal scoring logic
- governance internals
- orchestration internals
- proprietary runtime state

## Verification

The contract identity tests verify:

1. the public contract name is stable
2. schema version `1.0` resolves to the expected identity
3. repeated resolution is deterministic
4. unsupported schema versions are rejected
5. every supported schema version has a contract identity

## Regression Result

Full test suite:

`313 passed in 10.39s`

## Result

AI Test Lab can now answer:

> Exactly which public contract does this report belong to?

without changing the existing Public Report v1 payload.