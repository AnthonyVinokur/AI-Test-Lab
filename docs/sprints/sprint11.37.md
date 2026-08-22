# Sprint 11.37 — Published Report Contract Verification

## Goal

Allow AI Test Lab to verify whether an actual published public report corresponds to the exact public contract
fingerprint expected by a consumer.

## Problem

Sprint 11.36 introduced verification for a supplied schema version and fingerprint.

That operation answered:

> Does this fingerprint match the public contract for this schema version?

Consumers, however, typically start with an actual published report rather than a standalone schema version.

They need to answer:

> Does this published report use the exact public report contract definition that I expect?

## Design

Sprint 11.37 composes the existing public report reader and contract fingerprint verifier.

The verification flow is:

Published report
→ load and validate public report
→ read its schema version
→ verify supplied fingerprint against that schema version
→ return match or mismatch

The new operation is:

`verify_public_report_contract_for_report(...)`

## Architecture

The implementation deliberately reuses existing contract authorities.

`load_report()` remains responsible for:

- reading report JSON
- validating the public JSON Schema
- resolving the supported report model
- returning the validated public report

`verify_public_report_contract_fingerprint()` remains responsible for:

- validating the supplied fingerprint
- computing the expected canonical contract fingerprint
- comparing fingerprints

Sprint 11.37 does not duplicate either responsibility.

## Compatibility

Sprint 11.37 does not modify `ReportV1`.

No fingerprint field is added to the public report payload.

The frozen Public Report v1 serialized contract remains unchanged.

Contract verification remains external metadata and consumer functionality.

## Verification

Sprint 11.37 tests verify:

1. a valid report with the matching contract fingerprint returns `True`
2. a valid report with a valid but different fingerprint returns `False`
3. malformed fingerprints are rejected
4. the report's own schema version is used for verification
5. invalid reports are rejected before contract verification

## IP Protection Boundary

The verification process uses only public contract information:

- public report JSON
- public schema version
- published JSON Schema
- public contract fingerprint

It does not expose:

- scoring logic
- evaluation algorithms
- evaluator internals
- governance logic
- orchestration internals
- proprietary runtime state

## Regression Result

Full test suite:

`332 passed in 10.41s`

## Result

AI Test Lab can now answer:

> Does this actual published report correspond to the exact public report contract definition that I expect?

Sprint 11.35 created the fingerprint.

Sprint 11.36 verified standalone fingerprints.

Sprint 11.37 connects that verification directly to real published reports.
