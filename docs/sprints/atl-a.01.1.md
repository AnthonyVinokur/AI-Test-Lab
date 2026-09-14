# ATL-A.01.1 — Compatibility Contract

## Status

**Implemented.**

## Objective

Define the first stable public compatibility boundary between AI Test Lab and
the frozen Aquagear Reference Architecture `v1`.

This sprint answers one narrow question:

> Which exact public contract identity does AI Test Lab deliberately support?

It does not execute Aquagear, translate evaluation data, validate arbitrary
payloads, or produce compatibility evidence.

## Public contract

The module
`src/reference_architecture_compatibility_contract.py` publishes an immutable
`ReferenceArchitectureCompatibilityContractV1` DTO.

The DTO identifies:

- the AI Test Lab compatibility contract and its `1.0` version;
- the frozen Aquagear reference interface `v1`;
- the Aquagear reference-architecture contract `v1`;
- provider-neutral integration contract `v1`;
- reference round-trip client contract `v1`;
- reference-architecture conformance contract `1.0`;
- the initial `exact-version-match` policy.

All fields use fixed literal values. Unknown fields and unsupported versions
are rejected. The DTO inherits AI Test Lab's `PublicContractModel`, making it
immutable, strict, and eligible for the approved public serialization gateway.

## Compatibility semantics

The public relationship enum defines three possible outcomes:

- `exact`: every required contract identifier matches exactly;
- `compatible`: a future explicit policy declares a non-identical contract
  compatible;
- `incompatible`: compatibility has not been proven.

ATL-A.01.1 declares only `exact-version-match`. It does not declare any
cross-version relationship. Unknown or future versions must therefore never be
assumed compatible.

## Repository and IP boundary

AI Test Lab does not import the Aquagear package. Aquagear remains frozen and
unchanged. The contract duplicates no execution, authorization, governance,
scoring, evidence-intelligence, or other proprietary behavior.

The dependency direction remains:

```text
External system / Aquagear
            |
            v
AI Test Lab public compatibility contract
            |
            X
AI Test Lab private implementation
```

## Validation

Focused tests verify:

- authoritative names and versions;
- approved public serialization;
- immutable and extra-forbidden behavior;
- stable enum and policy values;
- rejection of mismatched and unsupported versions;
- rejection of the wrong contract identity;
- absence of undeclared public fields.

## Explicit non-goals

The following work belongs to later slices:

- **ATL-A.01.2:** deterministic compatibility validation and mismatch results;
- **ATL-A.01.3:** provider-neutral reference integration adapter;
- **ATL-A.01.4:** compatibility and round-trip evidence.

No HTTP transport, provider invocation, model execution, evidence enforcement,
or Aquagear feature expansion is included in ATL-A.01.1.
