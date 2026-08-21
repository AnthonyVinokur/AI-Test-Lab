# Sprint 11.35 — Public Report Contract Fingerprint

## Goal

Add a deterministic cryptographic fingerprint for the AI Test Lab public report contract without modifying the frozen Public Report v1 payload.

## Problem

A contract name and schema version identify a public contract, but they do not prove that two systems are using exactly the same contract definition.

For example, two runtimes could both claim to support:

`ai-test-lab.public-report` + `1.0`

while their underlying JSON Schema definitions differ.

Consumers need a deterministic way to verify the exact public contract definition.

## Design

Sprint 11.35 introduces a SHA-256 fingerprint calculated from the canonical public JSON Schema.

The fingerprint format is:

`sha256:<64 lowercase hexadecimal characters>`

The fingerprint is computed from a canonical JSON representation using:

- sorted object keys
- compact JSON separators
- UTF-8 encoding
- SHA-256 hashing

This means insignificant formatting changes such as indentation or object-key ordering do not change the fingerprint.

Meaningful public schema changes do change the fingerprint.

## Architecture

The fingerprint implementation uses the existing public report schema-version authority.

The flow is:

Public schema version  
→ schema filename  
→ public JSON Schema  
→ canonical JSON representation  
→ SHA-256 digest  
→ public contract fingerprint

The schema-version-to-file mapping remains owned by `report_contract_validator.py`.

The fingerprint implementation does not maintain a duplicate version catalog.

## Compatibility

Sprint 11.35 does not add fields to `ReportV1`.

The frozen Public Report v1 serialized payload remains unchanged.

The fingerprint is an external contract capability, similar to the contract identity introduced in Sprint 11.34.

## Determinism

For the same public contract definition:

`fingerprint(A) == fingerprint(A)`

For a meaningfully changed public contract definition:

`fingerprint(A) != fingerprint(B)`

The fingerprint therefore acts as a content identity for the published public contract.

## IP Protection Boundary

The fingerprint includes only the public JSON Schema definition.

It does not fingerprint or expose:

- evaluation algorithms
- scoring logic
- evaluator implementations
- governance logic
- orchestration internals
- proprietary runtime state
- private implementation details

This preserves the public/private architecture boundary.

## Verification

Sprint 11.35 tests verify:

1. SHA-256 is the stable fingerprint algorithm
2. supported public schema versions produce fingerprints
3. fingerprints use the expected `sha256:<digest>` format
4. repeated fingerprint generation is deterministic
5. every supported public schema version has a fingerprint
6. unsupported schema versions are rejected

## Regression Result

Full test suite:

`318 passed in 10.05s`

## Result

AI Test Lab can now answer:

> Is this exactly the same public report contract definition that I expect?

Contract identity identifies the contract.

Contract fingerprint verifies its exact public definition.
