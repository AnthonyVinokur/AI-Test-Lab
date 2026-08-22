# Sprint 11.42 — Evaluation Run Provenance Verification

## Goal

Add verification for evaluation run provenance fingerprints so AI Test Lab can confirm that a provenance record still matches a previously generated fingerprint.

## Problem

Sprint 11.41 can generate a deterministic SHA-256 fingerprint for evaluation run provenance, but generation alone does not prove that a later provenance record is unchanged.

Sprint 11.42 adds the comparison step.

## Implementation

Added:

- `src/evaluation_run_provenance_verification.py`
- `tests/test_evaluation_run_provenance_verification.py`

The verification function:

1. Receives an `EvaluationRunProvenance`
2. Recalculates its fingerprint using the existing Sprint 11.41 implementation
3. Compares the calculated fingerprint with the expected fingerprint
4. Returns `True` for a match
5. Returns `False` for a mismatch

The implementation reuses the existing provenance fingerprint function and does not duplicate canonicalization or hashing logic.

## Security Detail

Fingerprint comparison uses `hmac.compare_digest()`.

## Verification Scenarios

Covered by tests:

- unchanged provenance verifies successfully
- modified provenance fails verification

## Regression Result

```text
372 passed in 10.93s
Evaluation Run Identity
        ↓
Evaluation Run Provenance
        ↓
Provenance Fingerprint
        ↓
Provenance Verification

This adds an integrity-verification primitive to the reproducibility layer of AI Test Lab.

Acceptance Criteria
 Verification accepts provenance and expected fingerprint
 Matching provenance returns True
 Modified provenance returns False
 Existing Sprint 11.41 fingerprint logic is reused
 No duplicate hashing implementation
 Full regression suite passes