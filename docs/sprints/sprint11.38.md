# Sprint 11.38 — Public Report Contract Compatibility Verification

## Goal

Add an explicit compatibility decision layer for published public report contracts.

Previous sprints established:

* public report schema compatibility
* public contract identity
* deterministic contract fingerprints
* fingerprint verification
* verification of published report artifacts

Sprint 11.38 extends that chain by answering a new question:

> Can a consumer safely accept a published report contract relative to the contract it expects?

This is different from checking whether two contracts are identical.

---

## Problem

Before this sprint, AI Test Lab could determine:

1. whether a schema version is supported;
2. the deterministic fingerprint of a published contract;
3. whether a supplied fingerprint exactly matches that contract;
4. whether a published report uses the expected contract fingerprint.

However, exact identity and compatibility are different concepts.

A future public report version may not have the same fingerprint as an earlier version while still being intentionally compatible with consumers of that earlier contract.

AI Test Lab therefore needs an explicit compatibility policy instead of inferring compatibility from version numbers.

---

## Design Principle

The contract verification sequence is:

```text
Support
   ↓
Identity
   ↓
Compatibility
```

These concepts remain separate.

### Support

Answers:

> Does this runtime know this schema version?

### Identity

Answers:

> Does this fingerprint correspond exactly to the published contract for this schema version?

### Compatibility

Answers:

> May a consumer expecting one public contract safely consume another published contract?

---

## Compatibility States

Sprint 11.38 introduces:

```python
class ReportContractCompatibility(str, Enum):
    EXACT = "exact"
    COMPATIBLE = "compatible"
    INCOMPATIBLE = "incompatible"
```

### EXACT

The published contract is the exact contract expected by the consumer.

### COMPATIBLE

The contracts differ, but an explicit compatibility policy declares the published contract safe for that consumer.

### INCOMPATIBLE

The contract cannot be proven safe for the consumer.

Unknown compatibility is never treated as compatible.

---

## Current Compatibility Policy

At the time of this sprint, public report schema `1.0` is the only published schema.

Therefore no cross-version compatibility relationship is currently declared.

The compatibility policy is intentionally explicit:

```python
_COMPATIBLE_REPORT_CONTRACTS: dict[str, frozenset[str]] = {
    "1.0": frozenset(),
}
```

This does not mean the mechanism is unused.

It establishes the compatibility framework now while avoiding invented compatibility claims for unpublished versions such as `1.1`.

A future compatibility relationship must be deliberately added and tested.

---

## Compatibility Verification Flow

The new function is:

```python
verify_public_report_contract_compatibility(
    expected_schema_version,
    published_schema_version,
    published_fingerprint,
)
```

The decision flow is:

```text
Expected schema supported?
        │
        ├── NO → reject request
        │
        ▼
Published schema supported?
        │
        ├── NO → INCOMPATIBLE
        │
        ▼
Published fingerprint valid?
        │
        ├── NO → INCOMPATIBLE
        │
        ▼
Expected version == published version?
        │
        ├── YES → EXACT
        │
        ▼
Explicit compatibility relationship exists?
        │
        ├── YES → COMPATIBLE
        └── NO  → INCOMPATIBLE
```

The fingerprint is verified before compatibility is evaluated.

This prevents an invalid or unrelated contract fingerprint from being accepted through compatibility logic.

---

## Security and Safety Rule

AI Test Lab follows a fail-closed policy:

```text
Unknown compatibility ≠ compatible
```

Compatibility must be explicitly declared.

The system does not infer compatibility from:

* matching major version numbers;
* numerically adjacent versions;
* similar version strings;
* assumed semantic-versioning behavior;
* structural resemblance.

This prevents consumers from silently accepting public contracts whose compatibility has never been verified.

---

## IP Protection Boundary

Sprint 11.38 operates only on public contract information:

* public schema versions;
* public contract fingerprints;
* explicit public compatibility relationships.

It does not expose or depend on protected internal capabilities such as:

* proprietary scoring logic;
* governance internals;
* evidence intelligence;
* orchestration rules;
* commercial policy logic;
* internal evaluation models.

The public contract boundary remains intact.

---

## Implementation

Modified:

```text
src/report_contract_verification.py
```

Added:

```text
tests/test_report_contract_compatibility_verification.py
```

The implementation introduces:

* `ReportContractCompatibility`
* `EXACT`
* `COMPATIBLE`
* `INCOMPATIBLE`
* explicit compatibility policy metadata
* `verify_public_report_contract_compatibility(...)`

Existing fingerprint-verification behavior remains unchanged.

---

## Tests Added

Sprint 11.38 adds six tests covering:

1. matching contract returns `EXACT`;
2. wrong fingerprint returns `INCOMPATIBLE`;
3. unknown published schema returns `INCOMPATIBLE`;
4. unsupported expected schema is rejected;
5. malformed fingerprint is rejected;
6. exact identity is not incorrectly classified as cross-version `COMPATIBLE`.

---

## Regression Result

Before Sprint 11.38:

```text
332 passed
```

After Sprint 11.38:

```text
338 passed
```

Full regression suite:

```text
338 passed in 11.68s
```

No existing tests regressed.

---

## Architectural Result

The public report contract lifecycle now supports:

```text
Schema publication
      ↓
Schema compatibility
      ↓
Contract identity
      ↓
Contract fingerprint
      ↓
Fingerprint verification
      ↓
Published report verification
      ↓
Contract compatibility verification
```

AI Test Lab can now distinguish between:

```text
"I know this schema."

"This is exactly this contract."

"This different contract is explicitly safe for me."
```

That distinction creates the foundation for future public schema evolution without weakening contract guarantees.

---

## Future Extension

When a real future contract version is published, compatibility can be added explicitly.

For example:

```python
_COMPATIBLE_REPORT_CONTRACTS = {
    "1.0": frozenset({"1.1"}),
    "1.1": frozenset(),
}
```

Such a relationship must only be introduced after the new public contract exists and its backward-compatibility behavior has been validated.

Sprint 11.38 deliberately does not invent future compatibility.

---

## Sprint Outcome

Sprint 11.38 establishes a conservative, explicit, fingerprint-backed compatibility boundary for public report contracts.

The key principle is:

```text
Version numbers suggest relationships.

Explicit policy proves compatibility.
```
