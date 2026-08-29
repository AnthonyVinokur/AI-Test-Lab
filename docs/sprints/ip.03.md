# IP.03 — Public Contract Exposure Control

## Status

Complete

## Purpose

IP.03 establishes an explicit runtime boundary controlling what AI Test Lab data may be exposed through public artifacts.

IP.02 protects what may enter the public Git repository.

IP.03 protects what may leave internal runtime objects and cross into public-facing contracts such as reports, serialized regression results, APIs, CLI consumers, website integrations, and future external artifacts.

The central rule is:

```text
Internal domain object
        |
        X
        |
        v
Explicit public DTO
        |
        v
Controlled public serializer
        |
        v
Public artifact
```

Internal objects must not be treated as public contracts simply because they can technically be serialized.

## IP Classification

* [x] PUBLIC
* [ ] INTERNAL
* [ ] PROPRIETARY

The public-contract boundary mechanism is intentionally public infrastructure.

It exposes the safety architecture used to protect AI Test Lab's public interfaces without exposing proprietary scoring, governance, evidence-intelligence, security, orchestration, optimization, or customer-specific implementation logic.

## Goals

* Establish an explicit base type for public DTOs.
* Reject arbitrary internal models at the controlled public serialization boundary.
* Preserve allow-list based exposure rather than block-list based filtering.
* Integrate the existing Report V1 contract with the common public boundary.
* Integrate regression-result serialization with an explicit public DTO.
* Preserve existing public JSON structures.
* Prevent unknown fields from silently crossing public boundaries.
* Keep internal evaluation and regression domain objects separate from published contracts.
* Preserve compatibility with existing report schema validation.
* Avoid exposing proprietary implementation details.

## Implementation

### Public Contract Base

Added:

```text
src/public_contract.py
```

The module introduces:

```text
PublicContractModel
PublicContractExposureError
serialize_public_contract()
```

`PublicContractModel` is the common base for data explicitly approved for external exposure.

Its Pydantic configuration enforces:

```text
extra="forbid"
frozen=True
```

This means unknown fields cannot silently appear in a public contract and approved public contract instances cannot be mutated after construction.

### Controlled Public Serializer

The new:

```text
serialize_public_contract()
```

accepts only objects derived from:

```text
PublicContractModel
```

Objects that are merely serializable are not automatically public.

For example:

```text
Internal dataclass          -> rejected
Arbitrary Pydantic model    -> rejected
PublicContractModel         -> accepted
```

The boundary therefore uses positive authorization rather than attempting to recognize every possible private or proprietary field name.

## Allow-List Exposure Model

IP.03 deliberately does not use a block-list as its primary defense.

A block-list would require AI Test Lab to continuously recognize names such as:

```text
private_score
governance_weight
secret_algorithm
internal_strategy
proprietary_evidence
```

Such an approach is incomplete because future internal fields could use names that the filter does not know.

IP.03 instead uses:

```text
Explicit public DTO
        |
        v
Only declared fields are allowed
        |
        v
Unknown fields are rejected
```

This creates an architectural allow-list.

## Report V1 Integration

Updated:

```text
src/report_schema.py
src/json_reporter.py
```

The existing public report hierarchy now participates in the common exposure boundary.

The hierarchy is:

```text
PublicContractModel
        |
        v
PublicReportModel
        |
        +--> ReportV1
        +--> ReportTestResultV1
        +--> ReportMetricResultV1
        +--> ReportEngineExecutionResultV1
        +--> ReportSummaryV1
        +--> other Report V1 DTOs
```

The existing report DTO fields remain the public allow-list.

### Reporter Serialization

Before IP.03:

```text
ReportV1
   |
   v
model_dump()
   |
   v
Report payload
```

After IP.03:

```text
ReportV1
   |
   v
serialize_public_contract()
   |
   v
Public-contract verification
   |
   v
Report payload
   |
   v
Existing JSON-schema validation
```

The published Report V1 schema and external structure were not changed.

Existing report contract validation remains in place after public-contract serialization.

## Regression Public Contract

Added:

```text
src/evaluation_run_regression_public_contract.py
```

The explicit public DTO is:

```text
EvaluationRunRegressionResultV1
```

Only the existing approved regression output fields are exposed:

```text
enforcement
exit_code
```

No internal regression-comparison state, gate implementation details, scoring data, diagnostic internals, or other implementation information is included.

## Regression Serializer Integration

Updated:

```text
src/evaluation_run_regression_result_serializer.py
```

Before IP.03:

```text
Internal EvaluationRunRegressionResult
        |
        v
Manually constructed dictionary
        |
        v
Public output
```

After IP.03:

```text
Internal EvaluationRunRegressionResult
        |
        v
Explicit mapping
        |
        v
EvaluationRunRegressionResultV1
        |
        v
serialize_public_contract()
        |
        v
Public output
```

The existing regression JSON shape remains unchanged.

Allow remains:

```json
{
  "enforcement": "allow",
  "exit_code": 0
}
```

Block remains:

```json
{
  "enforcement": "block",
  "exit_code": 1
}
```

No additional public fields or schema-version fields were introduced in this sprint.

## Exposure-Control Tests

Added:

```text
tests/test_public_contract_exposure.py
```

The tests verify that:

1. an explicitly approved public contract can be serialized;
2. nested public DTOs serialize correctly;
3. internal runtime dataclasses are rejected;
4. arbitrary Pydantic models are rejected;
5. unknown public fields are rejected;
6. Report V1 is recognized as an explicit public contract;
7. regression public DTOs serialize through the controlled boundary;
8. internal regression result objects cannot directly cross that boundary;
9. regression public contracts reject undeclared fields.

These tests verify the architectural rule rather than relying on specific proprietary-field names.

## Compatibility

IP.03 intentionally preserves current external contracts.

### Report Contract

Report V1 remains:

```text
schema_version = "1.0"
```

No Report V1 fields were added, removed, or renamed as part of IP.03.

The existing published JSON schema continues to validate reporter output.

### Regression Contract

Regression output remains limited to:

```text
enforcement
exit_code
```

Existing serializer, JSON encoder, and writer compatibility tests continue to pass.

## Verification

Focused regression/public-contract verification:

```text
24 passed in 0.20s
```

Combined report and regression public-boundary verification:

```text
32 passed in 0.39s
```

Full regression suite:

```text
665 passed in 17.23s
```

Repository IP boundary:

```text
Repository boundary check: PASS
```

Git whitespace validation:

```text
git diff --check
```

Result:

```text
clean
```

## Security and IP Boundary

IP.03 establishes a supported public serialization gateway.

It does not claim that Python itself makes it impossible for a future developer to manually create a dictionary or invoke another serialization mechanism.

Instead, it creates the architectural contract that supported public export paths must use explicit public DTOs and the controlled public-contract boundary.

Future enforcement may add architectural scanning or linting to detect unsupported direct serialization paths.

IP.03 does not expose or implement proprietary AI Test Lab:

* scoring algorithms;
* governance decision logic;
* compliance decision engines;
* evidence-intelligence algorithms;
* security or adversarial intelligence;
* risk-ranking algorithms;
* advanced regression intelligence;
* optimization algorithms;
* commercially valuable orchestration;
* customer-specific policy logic.

## Outcome

Before IP.03:

```text
Internal object
      |
      +--> Could be directly serialized
      |
      v
Public artifact
```

After IP.03:

```text
Internal object
      |
      X
      |
      v
Explicit mapper
      |
      v
Approved PublicContractModel
      |
      v
Controlled public serializer
      |
      v
Schema / compatibility validation
      |
      v
Public artifact
```

IP.03 therefore establishes a reusable runtime exposure boundary between AI Test Lab's internal implementation and its public contracts.

Combined with IP.02:

```text
                    AI Test Lab IP Boundary

External/public repository
          ^
          |
     IP.02 protects
   what enters Git
          |
    ----------------
          |
     Internal runtime
          |
     IP.03 protects
   what leaves runtime
          |
          v
Public DTO / artifact
```

IP.02 and IP.03 together protect both sides of the public boundary: repository exposure and runtime-contract exposure.