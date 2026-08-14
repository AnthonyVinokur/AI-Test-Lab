# Sprint 11.11B — Report Schema v1.0 and IP Protection Boundary

## Goal

Introduce a strict public reporting contract so AI Test Lab evidence can be consumed externally without coupling customers or integrations to internal runtime models.

## Architectural rule

Public schemas describe observable results. They are not representations of internal implementation state.

All report serialization must follow this path:

`internal runtime model -> explicit mapper -> public DTO -> validation -> JSON`

Direct serialization of internal runtime models from reporters is prohibited.

## Classification

- **Public contract:** versioned report DTOs and fields intentionally exposed to report consumers.
- **Internal core:** runtime evaluation objects, execution state, orchestration, and implementation details.
- **Proprietary/commercial capability:** governance algorithms, evidence intelligence, risk aggregation, compliance mappings, enterprise policy logic, and future commercial scoring/orchestration unless explicitly approved for exposure.

## Implementation

- Add strict Pydantic Report Schema v1.0 DTOs with `extra="forbid"`.
- Add explicit field-by-field mapping from internal evaluation models to public report DTOs.
- Update `JsonReporter` to serialize only the validated public DTO.
- Preserve schema version, status, XFAIL/XPASS semantics, cost evidence, metric provenance, runtime options, and engine execution evidence.
- Add tests proving unknown/internal fields cannot silently cross the public boundary.

## Definition of Done

- Report Schema v1.0 remains the serialized contract.
- No direct `model_dump()` of internal `TestResult` or `ModelSummary` objects occurs in `JsonReporter`.
- Existing public report fields remain compatible where intended.
- Unknown fields are rejected by public DTOs.
- Evaluation provenance and engine evidence survive the mapping boundary.
- Existing test suite remains green.
