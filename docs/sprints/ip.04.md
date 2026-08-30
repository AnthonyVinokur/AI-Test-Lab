# IP.04 — Public Export Boundary Enforcement

## Status

**Implementation complete; final merge verification pending.**

IP.04 establishes a mechanically enforced serialization boundary for AI Test Lab. Production code may no longer serialize Pydantic models directly from arbitrary locations. Model serialization must cross one of two explicit gateways:

- a **public serialization gateway** for data intentionally approved for external exposure; or
- an **internal serialization gateway** for persistence, checksum generation, validation, and other implementation-only operations.

This sprint builds on the public-contract exposure control introduced in IP.03 and converts that architectural policy into an enforceable repository invariant.

---

## Objective

Prevent accidental exposure of internal AI Test Lab models by ensuring that public data leaves the framework only through explicit, reviewed public-contract transformations.

The required public path is:

```text
Internal model
      │
      ▼
Explicit public mapper
      │
      ▼
PublicContractModel
      │
      ▼
serialize_public_contract()
      │
      ▼
JSON-safe public payload
      │
      ▼
CLI / report / API / website / SDK / integration
```

Internal serialization uses a separate path:

```text
Internal model
      │
      ▼
serialize_internal_model()
      │
      ▼
Persistence / checksum / validation / internal processing
```

The two paths are intentionally distinct.

---

## Why This Sprint Exists

Pydantic makes serialization convenient:

```python
payload = model.model_dump(mode="json")
```

That convenience is also a public-contract risk.

If internal models are serialized directly, a future internal field can silently become part of an outward-facing payload. That can create several problems at once:

- accidental disclosure of implementation details;
- exposure of proprietary or commercially sensitive fields;
- unintended expansion of the public compatibility surface;
- coupling between internal refactors and external consumers;
- inconsistent serialization behavior across CLI, reports, APIs, and integrations;
- difficult review because public exposure decisions become distributed across the codebase.

IP.03 established **what data is allowed to become public**.

IP.04 establishes **how serialization is allowed to occur**.

Together, the two controls create a deliberate boundary between the protected framework core and external consumers.

---

## Security and IP Invariant

Production code must not directly invoke Pydantic export primitives outside approved serialization gateways.

The guarded methods are:

```python
model_dump()
model_dump_json()
```

A production call such as:

```python
payload = internal_result.model_dump(mode="json")
```

is considered a boundary violation.

Public serialization must instead look like:

```python
public_result = map_to_public_contract(internal_result)
payload = serialize_public_contract(public_result)
```

Internal serialization must use:

```python
payload = serialize_internal_model(internal_result, mode="json")
```

The architectural rule is therefore:

> **Model serialization is centralized, classified, and reviewable.**

---

## Serialization Gateways

### Public Gateway

The authoritative public serialization gateway remains:

```text
src/public_contract.py
```

`PublicContractModel` identifies models that are explicitly approved for public exposure.

`serialize_public_contract()` rejects arbitrary internal objects and serializes only approved public-contract models.

Conceptually:

```text
Internal runtime object
        │
        ▼
Explicit mapper
        │
        ▼
PublicContractModel
        │
        ▼
serialize_public_contract()
```

This ensures that adding a field to an internal implementation model does not automatically add that field to public output.

### Internal Gateway

IP.04 adds:

```text
src/internal_serialization.py
```

This gateway exists for implementation-only operations that legitimately require a model representation, including:

- repository persistence;
- deterministic checksum generation;
- internal validation transformations;
- internal model revalidation.

`serialize_internal_model()` explicitly rejects `PublicContractModel` instances.

That restriction prevents public DTOs from being routed through the internal path and preserves a clear distinction between internal and external serialization responsibilities.

---

## Dataset Boundary Hardening

Initial enforcement revealed that dataset functionality contained both legitimate internal serialization and genuine outward-facing serialization.

The sprint therefore did not simply allow-list the dataset subsystem. Instead, each call site was classified by responsibility.

### Internal dataset operations

Internal persistence and checksum-related serialization were moved behind:

```text
serialize_internal_model()
```

This applies to internal behavior such as:

```text
dataset repository persistence
entry model revalidation
dataset checksum generation
dataset checksum verification
```

These operations remain internal implementation details and do not define an external API contract.

### Public dataset operations

Dataset output exposed by CLI and export functionality now uses explicit public DTOs.

Added:

```text
src/datasets/public_contract.py
src/datasets/public_mapper.py
```

The public contract defines explicit approved fields for:

```text
DatasetEntryV1
DatasetVersionV1
DatasetManifestV1
DatasetV1
DatasetExportV1
```

The mapper performs deliberate field-by-field transformation from internal dataset models into those public DTOs.

The public path is now:

```text
Dataset / DatasetManifest / DatasetVersion
                │
                ▼
       explicit public mapper
                │
                ▼
       Dataset*V1 public DTO
                │
                ▼
     serialize_public_contract()
                │
                ▼
        CLI / exported payload
```

This is a critical IP-protection property.

If an internal dataset model later gains fields such as proprietary scoring metadata, internal policy state, orchestration metadata, or implementation diagnostics, those fields do not automatically become public.

---

## Public Report Consumer Hardening

The report consumer already operates on an approved public report model.

IP.04 removes its direct model serialization and routes the report through:

```python
serialize_public_contract(report)
```

This keeps public-report consumption aligned with the same approved serialization gateway used by report production.

The consumer therefore no longer creates a second, informal serialization path around the public-contract boundary.

---

## Automated Boundary Scanner

IP.04 adds:

```text
scripts/check_public_export_boundary.py
```

The scanner performs AST-based analysis of production Python source.

AST inspection is used instead of simple text matching so that comments and string literals do not create false violations.

For example, these do **not** fail the scanner:

```python
# result.model_dump()
message = "result.model_dump_json()"
```

A real call does fail:

```python
payload = result.model_dump()
```

---

## Production Scope

The scanner protects Python production surfaces, including:

```text
src/**/*.py
root-level production *.py entry points
```

Tests and enforcement scripts are not treated as production export surfaces.

This distinction is intentional.

Tests may need to inspect Pydantic models directly to verify behavior. Such test-only inspection does not create an external product boundary.

At the same time, root-level executable Python entry points remain protected because they may emit user-visible output.

---

## Working-Tree Protection

The scanner does not rely exclusively on `git ls-files`.

It scans production Python files in the working tree, including newly created files that have not yet been staged.

This prevents a local false PASS such as:

```text
create src/new_export.py
add direct model_dump()
run scanner before git add
```

The new file is still inspected.

The rule therefore protects the code being developed, not merely the subset Git already knows about.

---

## Fail-Closed Inspection

A security boundary must not interpret "could not inspect" as "safe."

The scanner therefore distinguishes three outcomes:

| Result | Meaning |
|---|---|
| `PASS` | Production source was inspected successfully and no serialization bypass was found. |
| `FAIL` | Source was inspected successfully and a forbidden direct serialization call was found. |
| `ERROR` | Production source could not be safely inspected. |

Malformed Python source raises an inspection error rather than producing a false PASS.

Unreadable production source likewise causes an error.

This fail-closed behavior is intentional.

---

## Cross-Platform Determinism

Diagnostics normalize paths to POSIX-style representation.

Example:

```text
src/example.py:42:11
```

rather than allowing platform-specific output such as:

```text
src\example.py:42:11
```

This keeps diagnostics stable between Windows development environments and Linux CI runners.

Violation ordering is also deterministic.

---

## Initial Findings

When the rule was first applied, the scanner found eight production serialization call sites.

They were not blindly suppressed.

Each was classified as either:

```text
PUBLIC EXPORT
INTERNAL TRANSFORMATION
```

The initial set included:

```text
dataset CLI output
dataset repository persistence
dataset update/revalidation
dataset export
dataset checksum generation
dataset checksum verification
public report consumption
```

The remediation progressed from:

```text
8 violations
     ↓
3 violations
     ↓
0 violations
```

The remaining production uses of Pydantic export primitives are now confined to the approved gateways:

```text
src/internal_serialization.py
src/public_contract.py
```

Historical documentation and tests may still contain examples or direct test inspection calls; those are outside the production export boundary.

---

## Scanner Test Coverage

`tests/test_public_export_boundary.py` protects the scanner itself.

Coverage includes:

- rejection of direct `model_dump()`;
- rejection of `model_dump(mode="json")`;
- rejection of `model_dump_json()`;
- ignoring comments and string literals;
- allowing ordinary `json.dumps()`;
- allowing the approved public serializer;
- allowing the trusted public serialization gateway;
- allowing the trusted internal serialization gateway;
- rejecting untrusted production serialization;
- deterministic source-location diagnostics;
- production-scope classification;
- exclusion of test files;
- exclusion of scanner scripts from production scope;
- repository-wide zero-violation enforcement;
- scanning of newly created untracked production files;
- fail-closed behavior for invalid Python source.

Latest focused scanner verification:

```text
17 passed in 0.18s
```

---

## Dataset Public-Contract Tests

`tests/test_dataset_public_contract.py` verifies that dataset public output is explicit rather than inherited from internal models.

Coverage includes:

- explicit `DatasetEntryV1` mapping;
- public manifest status normalization;
- stable public version shape;
- stable dataset `show` shape;
- stable exported dataset shape;
- rejection of unknown public-contract fields.

The public contract uses `extra="forbid"` through the shared `PublicContractModel` base.

This means an unexpected field cannot silently enter a public DTO.

---

## Internal Serialization Tests

`tests/test_internal_serialization.py` verifies the internal gateway.

Coverage includes:

- serialization of ordinary internal Pydantic models;
- JSON-mode internal serialization;
- rejection of public-contract models by the internal serializer.

The negative test is especially important:

```text
PublicContractModel
        X
        │
        ▼
serialize_internal_model()
```

Public DTOs must remain on the public path.

---

## Regression Verification

Affected dataset and public-report behavior was verified after the serialization refactor.

The targeted regression run covered:

```text
tests/test_dataset_service.py
tests/test_dataset_validator.py
tests/test_dataset_info_cli.py
tests/test_dataset_loader.py
tests/test_main_dataset_source.py
tests/test_report_consumer.py
```

Result:

```text
43 passed in 2.37s
```

This verifies that the boundary changes preserve dataset lifecycle behavior, checksum behavior, dataset loading, CLI information behavior, and public report consumption.

A complete repository suite was also executed during the sprint:

```text
691 passed in 18.46s
```

That full-suite result was recorded before the final two scanner-hardening tests for untracked-file inspection and fail-closed syntax handling were added. The focused scanner suite was rerun afterward and passed all 17 tests.

A final full-suite rerun should be recorded before merge so the release evidence reflects the exact final staged tree.

---

## Repository Security Verification

The repository leakage boundary remains green:

```text
Repository boundary check: PASS
```

The new public export boundary is also green:

```text
Public export boundary check: PASS
```

These controls protect different risks:

```text
Repository boundary
        │
        └── prevents secrets / forbidden repository content

Public export boundary
        │
        └── prevents uncontrolled model serialization
```

Together they provide defense in depth.

---

## CI Enforcement

The sprint is designed to run the export-boundary scanner in the normal GitHub Actions test workflow.

The intended order is:

```text
Checkout
   ↓
Install dependencies
   ↓
Repository boundary check
   ↓
Public export boundary check
   ↓
Unit / regression tests
```

Required workflow step:

```yaml
- name: Enforce public export boundary
  run: python scripts/check_public_export_boundary.py
```

Once committed, a future pull request that introduces direct production model serialization will fail CI before merge.

---

## Pull-Request Review Control

The repository PR checklist should include explicit export-boundary review.

Required review assertions:

```text
Public export boundary scanner passes.
No direct model serialization bypasses an approved serialization gateway.
```

This adds a human-review layer on top of automated enforcement.

Automation detects prohibited calls.

Reviewers remain responsible for deciding whether a new DTO or mapper intentionally exposes the correct fields.

---

## Scope

IP.04 intentionally focuses on high-value, deterministic serialization primitives.

It does **not** attempt to implement generalized data-flow or taint analysis.

The sprint does not attempt to prohibit every possible Python mechanism that could theoretically expose data, such as:

```text
vars()
__dict__
reflection
custom JSON encoders
handwritten dictionaries
arbitrary string construction
network transport policy
authorization policy
consumer identity
```

Those concerns may require separate controls later.

The IP.04 rule is deliberately narrow:

> **Pydantic model export primitives may only be invoked through approved serialization gateways.**

This gives the repository a strong, low-noise invariant without introducing a brittle static-analysis system.

---

## Compatibility

The sprint is intended to preserve existing external behavior while changing how payloads are constructed.

The changes do not intentionally alter:

- dataset lifecycle semantics;
- dataset versioning;
- dataset checksums;
- dataset import behavior;
- dataset loading behavior;
- report schema versioning;
- report compatibility policy;
- report release-readiness behavior;
- evaluation semantics;
- regression semantics;
- CLI process exit-code semantics.

Where dataset output already existed, the new public DTOs preserve the existing intended public shape while making the shape explicit and reviewable.

---

## Files Introduced

### Production

```text
src/internal_serialization.py
src/datasets/public_contract.py
src/datasets/public_mapper.py
```

### Enforcement

```text
scripts/check_public_export_boundary.py
```

### Tests

```text
tests/test_public_export_boundary.py
tests/test_internal_serialization.py
tests/test_dataset_public_contract.py
```

---

## Production Areas Updated

The sprint refactors serialization behavior in:

```text
dataset_cli.py
src/datasets/repository.py
src/datasets/service.py
src/datasets/validator.py
src/report_consumer.py
```

The exact final changed-file list should be taken from the staged Git diff before merge.

---

## Architectural Result

Before IP.04:

```text
Internal model
     │
     ├──────────────► model_dump()
     │
     ├──────────────► model_dump_json()
     │
     └──────────────► arbitrary public/internal destinations
```

After IP.04:

```text
                     ┌────────────────────────────┐
                     │      INTERNAL PATH         │
                     │                            │
Internal model ─────►│ serialize_internal_model() │
                     │        ↓                   │
                     │ persistence / checksum     │
                     └────────────────────────────┘

Internal model
      │
      ▼
explicit public mapper
      │
      ▼
PublicContractModel
      │
      ▼
serialize_public_contract()
      │
      ▼
public output
```

The difference is not merely code organization.

It changes public exposure from an incidental property of implementation models into an explicit contract decision.

---

## IP-Protection Impact

IP.04 strengthens the software boundary in several durable ways.

### Internal evolution no longer implies public evolution

Internal models can gain implementation fields without those fields automatically appearing in public JSON.

### Public exposure becomes reviewable

A public field must appear explicitly in a public DTO and mapper.

### Proprietary internals remain easier to isolate

Future governance, scoring, evidence-intelligence, compliance, security, and orchestration fields can remain internal by default.

### External integrations depend on stable contracts

The website, APIs, downloadable artifacts, SDKs, and enterprise integrations can consume deliberate public DTOs rather than internal object graphs.

### CI catches accidental bypasses

Future direct serialization shortcuts fail automatically.

---

## Relationship to Previous IP Sprints

The repository protection sequence now forms a layered control model:

```text
IP.01 / IP.02
Repository leakage protection
        │
        ▼
Prevent secrets and protected repository content
        │
        ▼
IP.03
Public contract exposure control
        │
        ▼
Define what data is allowed to be public
        │
        ▼
IP.04
Public export boundary enforcement
        │
        ▼
Enforce how model data is allowed to be serialized
```

This sequence separates three distinct security questions:

```text
Should this content exist in the public repository?

Is this field approved for public exposure?

Did the data leave through an approved serialization path?
```

That separation keeps the controls understandable and maintainable.

---

## Future Direction

IP.04 provides the serialization foundation for future controlled outward-facing channels, including:

```text
HTTP APIs
downloadable reports
CLI machine-readable output
website data feeds
SDK payloads
webhooks
enterprise integrations
external evidence systems
governance exports
```

Future controls can build on this boundary to address questions such as:

```text
Who may consume a public contract?
Which contract versions may a consumer request?
Which integrations may receive which public fields?
How are exports authenticated, authorized, logged, and audited?
```

Those concerns are intentionally separate from this sprint.

---

## Definition of Done

IP.04 is complete when all of the following are true:

- [x] Direct production `model_dump()` calls are detected.
- [x] Direct production `model_dump_json()` calls are detected.
- [x] Comments and string literals do not create false positives.
- [x] Public serialization uses `serialize_public_contract()`.
- [x] Internal serialization uses a separate explicit gateway.
- [x] The internal gateway rejects public-contract models.
- [x] Dataset public output uses explicit public DTOs.
- [x] Dataset public mapping is field-by-field.
- [x] Public report consumption uses the approved public serializer.
- [x] Root-level production entry points are protected.
- [x] Newly created untracked production source is inspected.
- [x] Malformed production source fails closed.
- [x] Diagnostics are cross-platform deterministic.
- [x] The repository contains zero direct production serialization bypasses.
- [x] Public export boundary scanner passes.
- [x] Repository boundary scanner passes.
- [x] Affected subsystem regression suite passes.
- [ ] Final full-suite verification is rerun against the exact final staged tree.
- [ ] `git diff --check` is clean on the exact final staged tree.
- [ ] GitHub Actions contains the public export boundary step.
- [ ] Pull-request checklist contains the public export boundary review items.

---

## Verification Evidence

| Verification | Result |
|---|---:|
| Public export boundary focused tests | **17 passed in 0.18s** |
| Dataset/public-contract/internal boundary checkpoint | **24 passed in 0.36s** |
| Affected dataset/report regression suite | **43 passed in 2.37s** |
| Complete project suite checkpoint | **691 passed in 18.46s** |
| Repository boundary scanner | **PASS** |
| Public export boundary scanner | **PASS** |

> The 691-test full-suite checkpoint predates the final two scanner-hardening tests. Record a final full-suite result after all IP.04 code, CI, PR-template, documentation, and formatting changes are staged.

---

## Final Result

IP.04 converts AI Test Lab's public serialization policy from convention into an enforceable engineering boundary.

The framework now distinguishes:

```text
internal representation
        │
        ├── internal serialization gateway
        │
        └── explicit public transformation
                  │
                  ▼
           public contract DTO
                  │
                  ▼
           public serializer
```

That separation protects public contract stability, reduces accidental information exposure, and creates a durable foundation for future APIs, website integrations, SDKs, downloadable artifacts, and enterprise-facing interfaces.

**IP.04 therefore answers a foundational product-security question:**

> When AI Test Lab data leaves an internal model, can we prove that it crossed an intentional, reviewable boundary?

With this sprint, the repository now has a deterministic mechanism for answering **yes**.
