# Sprint 11.39 — Evaluation Run Identity

## Goal

Introduce a stable public identity for individual AI Test Lab evaluation runs.

The purpose of this sprint is to establish the first reproducibility primitive that allows later reports, regression comparisons, and CI quality gates to refer to a specific evaluation execution.

## Problem

AI Test Lab can identify and verify its public report contract, but contract identity answers:

> Which public contract produced this report?

It does not answer:

> Which specific evaluation execution produced this result?

Two executions may use the same:

- model
- dataset
- evaluation profile
- report contract

while still being separate runs.

AI Test Lab therefore needs a dedicated evaluation-run identity.

## Implementation

Added:

`src/evaluation_run_identity.py`

### EvaluationRunIdentity

The public run identity contains:

- `run_id`
- `model`
- `evaluation_profile`
- `dataset`

The model is immutable using a frozen dataclass.

### Validation

All public identity fields must be non-empty strings.

The model rejects:

- empty run IDs
- empty model names
- empty evaluation profiles
- empty dataset names
- whitespace-only values

### Public Serialization Boundary

`to_public_dict()` explicitly exposes only supported public metadata.

Fields are serialized individually rather than automatically serializing the entire dataclass.

This preserves the AI Test Lab public/private architecture boundary and prevents future internal fields from becoming public accidentally.

### Run ID Generation

Added:

`create_evaluation_run_identity()`

The factory generates run IDs using UUID4:

`run-<uuid>`

Example:

`run-550e8400-e29b-41d4-a716-446655440000`

The run ID represents one evaluation execution.

It is deliberately not derived from model, dataset, profile, timestamps, or evaluation configuration.

Configuration reproducibility and deterministic fingerprints are separate concerns for later sprints.

## Tests

Added:

`tests/test_evaluation_run_identity.py`

Coverage verifies:

- public metadata preservation
- separate run identities
- immutability
- required field validation
- whitespace validation
- explicit public serialization
- generated run IDs

Focused verification:

`10 passed`

Full regression suite:

`348 passed`

## Architectural Result

Before Sprint 11.39:

Evaluation
→ Report
→ Public Report Contract
→ Contract Identity
→ Contract Fingerprint
→ Contract Verification

After Sprint 11.39:

Evaluation
→ Evaluation Run Identity
→ Report / Evidence

The new run identity becomes an anchor for future:

- reproducibility metadata
- run fingerprints
- historical comparison
- baseline selection
- regression detection
- CI quality gates
- audit evidence

## Scope Boundary

Sprint 11.39 intentionally does not implement:

- persistent run storage
- run history
- deterministic run fingerprints
- baseline comparison
- regression detection
- report integration
- timestamps
- internal execution-state exposure

Those capabilities should build on the run identity incrementally.

## Result

Sprint 11.39 establishes a small, explicit, immutable, and safe public identity for individual AI Test Lab evaluation executions.