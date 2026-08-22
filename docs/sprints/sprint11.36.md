# Sprint 11.36 — Public Report Contract Fingerprint Verification

## Goal

Allow AI Test Lab to verify whether a supplied public report contract fingerprint matches the exact contract definition supported by the runtime.

## Problem

Sprint 11.35 introduced deterministic SHA-256 fingerprints for public report contracts.

A fingerprint by itself is useful, but consumers also need a standard verification operation that can answer:

> Does this supplied fingerprint match the public report contract supported by this runtime?

## Design

Sprint 11.36 introduces public contract fingerprint verification.

Verification performs these steps:

1. validate the requested schema version
2. validate the supplied fingerprint format
3. compute the expected fingerprint using the existing Sprint 11.35 fingerprint capability
4. compare the expected and supplied fingerprints
5. return a boolean match result

The public fingerprint format remains:

`sha256:<64 lowercase hexadecimal characters>`

## Comparison Strategy

Fingerprint equality uses Python's `hmac.compare_digest()`.

This avoids ordinary string comparison for the final verification operation and provides a constant-time comparison primitive where supported.

The sprint does not introduce Double HMAC because public contract fingerprints are not secrets and already have a fixed validated format.

## Architecture

The verification layer consumes the existing fingerprint capability rather than reproducing hashing or canonicalization logic.

The flow is:

Public schema version  
→ validate version  
→ validate supplied fingerprint  
→ compute canonical contract fingerprint  
→ constant-time comparison  
→ match / mismatch

`report_contract_fingerprint.py` remains responsible for fingerprint generation.

`report_contract_verification.py` is responsible only for verification.

## Compatibility

Sprint 11.36 does not modify `ReportV1`.

The frozen Public Report v1 serialized payload remains unchanged.

No new fields are added to public report JSON.

## Error Handling

Verification rejects:

- unsupported schema versions
- empty fingerprints
- incorrect algorithms
- incorrect digest lengths
- invalid hexadecimal characters
- malformed fingerprint structures

A valid but non-matching fingerprint returns `False`.

Malformed or unsupported input raises `ValueError`.

## IP Protection Boundary

Verification operates only on public contract metadata and the published public JSON Schema fingerprint.

It does not expose or verify:

- proprietary scoring logic
- evaluation algorithms
- evaluator implementation details
- governance internals
- orchestration internals
- private runtime state

## Verification

Sprint 11.36 tests verify:

1. matching fingerprints return `True`
2. valid but mismatched fingerprints return `False`
3. empty fingerprints are rejected
4. missing digests are rejected
5. unsupported algorithms are rejected
6. incorrect digest lengths are rejected
7. invalid hexadecimal characters are rejected
8. unsupported schema versions are rejected
9. verification reuses the canonical public fingerprint capability

## Regression Result

Full test suite:

`327 passed in 9.73s`

## Result

AI Test Lab can now answer:

> Does this supplied fingerprint match the exact public report contract supported by this runtime?

Sprint 11.35 created deterministic contract fingerprints.

Sprint 11.36 makes those fingerprints verifiable.