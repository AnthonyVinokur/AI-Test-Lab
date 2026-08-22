# Sprint 11.40 — Evaluation Run Provenance

## Objective

Introduce a small, immutable provenance record that captures the minimum
report-safe facts required to explain what produced an evaluation run.

Sprint 11.39 established evaluation run identity.

Sprint 11.40 extends that foundation by answering:

> What model, evaluation profile, dataset, dataset version, and public report
> contract produced this run?

This is another foundational step toward deterministic reproducibility and
future regression analysis.

---

## Motivation

A run identifier tells AI Test Lab which evaluation run is being referenced,
but identity alone does not explain how that result was produced.

For example, two runs may have different results because:

- the model changed,
- the evaluation profile changed,
- the dataset changed,
- the dataset version changed,
- or the public report contract changed.

Without provenance, those differences can be difficult to diagnose reliably.

Evaluation run provenance records those important inputs explicitly.

---

## Scope

Sprint 11.40 introduces:

- `EvaluationRunProvenance`
- immutable provenance records
- required provenance field validation
- explicit public-safe serialization
- deterministic provenance representation
- observable provenance differences
- focused provenance tests

This sprint intentionally does not:

- modify report schemas,
- modify the CLI,
- modify evaluation execution,
- persist provenance,
- bind provenance to run identity,
- compute provenance fingerprints,
- implement reproducibility verification,
- or implement regression comparison.

Those capabilities can be layered on top of this primitive in later sprints.

---

## Provenance Fields

`EvaluationRunProvenance` records:

### `run_id`

Identifies the evaluation run associated with the provenance record.

### `model`

Identifies the model used during the evaluation.

Example:

```text
llama3.1:latest
```

### `evaluation_profile`

Identifies the evaluation configuration/profile used for the run.

Example:

```text
fast-ci
```

### `dataset`

Identifies the dataset used during evaluation.

### `dataset_version`

Identifies the specific dataset revision used by the run.

This is important because two executions using the same dataset name may
produce different results if different dataset versions were used.

### `report_contract`

Identifies the public report contract associated with the evaluation output.

### `report_contract_fingerprint`

Identifies the exact report contract definition associated with the run.

---

## Immutability

`EvaluationRunProvenance` is implemented as a frozen dataclass.

After provenance has been created, fields cannot be silently changed.

This matters because provenance describes historical evidence.

A completed run should continue to describe the same execution environment
and inputs later.

---

## Explicit Serialization

The provenance object provides an explicit `to_dict()` representation.

Serialization is intentionally implemented by explicitly selecting public
fields rather than automatically serializing every dataclass field.

This creates a controlled contract boundary.

If internal implementation fields are added later, they will not
automatically become part of serialized provenance.

This supports:

- public contract stability,
- intentional API evolution,
- reduced accidental information exposure,
- protection of internal implementation details.

---

## Deterministic Representation

Equivalent provenance records produce equivalent dictionary representations.

For example:

```python
first = make_provenance()
second = make_provenance()

assert first.to_dict() == second.to_dict()
```

This deterministic representation provides a foundation for future:

- provenance fingerprints,
- reproducibility verification,
- evidence comparison,
- regression analysis.

---

## Observable Changes

Changes to reproducibility-critical provenance remain visible.

For example:

```python
first = make_provenance(dataset_version="1")
second = make_provenance(dataset_version="2")

assert first.to_dict() != second.to_dict()
```

This prevents meaningful execution differences from disappearing inside
opaque runtime state.

---

## Architecture

The reproducibility sequence now includes:

```text
Public Report Contract
        ↓
Contract Identity
        ↓
Contract Fingerprint
        ↓
Contract Verification
        ↓
Contract Compatibility
        ↓
Evaluation Run Identity
        ↓
Evaluation Run Provenance
```

Sprint 11.39 answers:

> Which run is this?

Sprint 11.40 answers:

> What produced this run?

Future work can safely build identity/provenance binding and reproducibility
verification on top of these primitives.

---

## Files Added

- `src/evaluation_run_provenance.py`
- `tests/test_evaluation_run_provenance.py`
- `docs/sprints/sprint11.40.md`

---

## Verification

Focused provenance tests:

```text
13 passed
```

Full regression suite:

```text
361 passed in 10.37s
```

No existing tests were broken.

---

## Acceptance Criteria

Sprint 11.40 satisfies the following requirements:

- provenance can be created for an evaluation run,
- run identity is included,
- model identity is captured,
- evaluation profile is captured,
- dataset identity is captured,
- dataset version is captured,
- report contract identity is captured,
- report contract fingerprint is captured,
- required fields reject blank values,
- provenance is immutable,
- serialization is deterministic,
- provenance changes remain observable,
- serialization uses an explicit public-safe boundary,
- existing report contracts remain unchanged,
- the complete regression suite remains green.

---

## Result

Sprint 11.40 establishes a minimal evaluation provenance primitive.

AI Test Lab can now represent not only:

> Which evaluation run is this?

but also:

> What reproducibility-critical inputs produced this evaluation run?

This provides another foundational layer for deterministic reproducibility,
evidence verification, and future regression engineering.
