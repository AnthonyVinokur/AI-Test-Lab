# Sprint 11.41 — Evaluation Run Provenance Fingerprint

## Objective

Introduce a deterministic fingerprint for evaluation run provenance.

Sprint 11.40 established an immutable provenance record describing the reproducibility-critical inputs associated with an evaluation run.

Sprint 11.41 extends that foundation by answering:

> Can AI Test Lab represent those provenance facts with one stable deterministic fingerprint?

This creates another foundational primitive for future provenance verification, reproducibility verification, and regression analysis.

---

## Motivation

Evaluation provenance records the facts that produced a run, including:

* run identity,
* model identity,
* evaluation profile,
* dataset,
* dataset version,
* public report contract,
* report contract fingerprint.

Comparing every provenance field individually is possible, but it becomes cumbersome as provenance is used throughout the system.

A deterministic provenance fingerprint provides a compact identity for the complete public-safe provenance representation.

Equivalent provenance should always produce the same fingerprint.

Meaningful provenance changes should produce a different fingerprint.

---

## Scope

Sprint 11.41 introduces:

* deterministic evaluation provenance fingerprinting,
* canonical provenance serialization,
* SHA-256 fingerprint generation,
* stable fingerprints for equivalent provenance,
* observable fingerprints when provenance changes,
* protection of the explicit public-safe provenance boundary,
* focused fingerprint tests.

This sprint intentionally does not:

* modify public report schemas,
* modify evaluation execution,
* modify the CLI,
* persist fingerprints,
* verify stored fingerprints,
* compare evaluation runs,
* produce reproducibility verdicts,
* implement regression detection,
* add CI quality gates.

Those capabilities can be layered on top of this primitive in later sprints.

---

## Fingerprint Input Boundary

The fingerprint is derived from:

```python
provenance.to_dict()
```

rather than automatically serializing the internal dataclass.

This is intentional.

The explicit `to_dict()` method introduced in Sprint 11.40 defines the public-safe provenance representation.

Using that representation as the fingerprint boundary prevents future internal implementation fields from silently becoming part of the fingerprint.

This supports:

* deterministic behavior,
* controlled contract evolution,
* public/private architecture separation,
* reduced accidental information exposure,
* protection of internal implementation details.

---

## Canonical Serialization

Before hashing, provenance is converted to deterministic JSON.

The implementation uses behavior equivalent to:

```python
json.dumps(
    provenance.to_dict(),
    sort_keys=True,
    separators=(",", ":"),
    ensure_ascii=False,
)
```

Canonical serialization matters because semantically equivalent provenance must generate exactly the same byte sequence before hashing.

Sorting keys eliminates dependency on dictionary ordering.

Compact separators eliminate irrelevant whitespace differences.

UTF-8 encoding provides a deterministic byte representation.

---

## SHA-256 Fingerprint

The canonical provenance payload is hashed using SHA-256.

Conceptually:

```text
EvaluationRunProvenance
        ↓
to_dict()
        ↓
Canonical JSON
        ↓
UTF-8 bytes
        ↓
SHA-256
        ↓
64-character hexadecimal fingerprint
```

The resulting fingerprint is a lowercase hexadecimal string with 64 characters.

---

## Deterministic Behavior

Equivalent provenance objects produce the same fingerprint.

For example:

```python
first = make_provenance()
second = make_provenance()

assert (
    fingerprint_evaluation_run_provenance(first)
    == fingerprint_evaluation_run_provenance(second)
)
```

This property is essential for future reproducibility verification.

---

## Observable Provenance Changes

Changes to reproducibility-critical provenance produce different fingerprints.

Examples include changes to:

* model,
* evaluation profile,
* dataset,
* dataset version,
* report contract,
* report contract fingerprint.

For example:

```python
first = make_provenance(dataset_version="1")
second = make_provenance(dataset_version="2")

assert (
    fingerprint_evaluation_run_provenance(first)
    != fingerprint_evaluation_run_provenance(second)
)
```

This gives AI Test Lab a compact signal that the declared execution provenance changed.

---

## Non-Mutating Behavior

Fingerprint generation does not modify the provenance object.

Evaluation provenance represents historical evidence and is immutable.

Fingerprinting must therefore be observational only.

The implementation reads the explicit serialized provenance representation and leaves the original object unchanged.

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
        ↓
Evaluation Run Provenance Fingerprint
```

Sprint 11.39 answers:

> Which evaluation run is this?

Sprint 11.40 answers:

> What produced this evaluation run?

Sprint 11.41 answers:

> What deterministic fingerprint represents that provenance?

Future work can build provenance verification and reproducibility verification on top of this foundation.

---

## Files Added

* `src/evaluation_run_provenance_fingerprint.py`
* `tests/test_evaluation_run_provenance_fingerprint.py`
* `docs/sprints/sprint11.41.md`

---

## Verification

Focused provenance fingerprint tests:

```text
9 passed in 0.06s
```

Full regression suite:

```text
370 passed in 10.31s
```

No existing tests were broken.

---

## Acceptance Criteria

Sprint 11.41 satisfies the following requirements:

* evaluation provenance can be fingerprinted,
* fingerprinting uses the explicit public-safe provenance representation,
* provenance is serialized deterministically before hashing,
* SHA-256 is used,
* fingerprints are lowercase hexadecimal strings,
* fingerprints contain 64 hexadecimal characters,
* equivalent provenance produces equivalent fingerprints,
* model changes alter the fingerprint,
* evaluation profile changes alter the fingerprint,
* dataset changes alter the fingerprint,
* dataset version changes alter the fingerprint,
* report contract changes alter the fingerprint,
* report contract fingerprint changes alter the provenance fingerprint,
* fingerprinting does not mutate provenance,
* existing public report contracts remain unchanged,
* the complete regression suite remains green.

---

## Result

Sprint 11.41 establishes deterministic evaluation run provenance fingerprinting.

AI Test Lab can now represent not only:

> Which run is this?

and:

> What produced this run?

but also:

> What stable fingerprint represents those reproducibility-critical provenance facts?

This provides another clean foundation for future provenance verification, reproducibility verification, evidence comparison, and regression engineering.
