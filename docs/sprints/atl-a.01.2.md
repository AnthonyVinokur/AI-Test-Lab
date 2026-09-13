# ATL-A.01.2 — Request Translation

## Status

**Implemented.**

## Objective

Translate an untrusted external compatibility request into AI Test Lab's
strict public request model, then compare its complete identity with the frozen
Aquagear Reference Architecture `v1` contract.

This slice answers two narrow questions:

1. Is the incoming request structurally valid?
2. Does every declared compatibility identity field exactly match the one
   contract supported by AI Test Lab?

## Translation behavior

`src/reference_architecture_request_translation.py` accepts a mapping at the
public boundary. It copies and validates the mapping before comparison.

- A non-mapping, missing field, extra field, or non-string identity value is a
  malformed request and raises `ReferenceArchitectureRequestTranslationError`.
- A well-formed request containing an unknown name, version, or policy is not a
  parser failure. It produces a deterministic `incompatible` result.
- A request whose full identity matches ATL-A.01.1 produces `exact` and
  `compatible: true`.
- Mismatches are returned in stable contract-field order with public
  `field`, `expected`, and `actual` values.

The `compatible` relationship remains reserved for a future explicit policy.
The current `exact-version-match` policy never infers cross-version
compatibility.

## Public boundary

The request, mismatch, and translation-result DTOs inherit
`PublicContractModel`. They are immutable, forbid undeclared fields, and can be
serialized only through the approved public serializer.

The result contains only:

- translation contract identity;
- `exact` or `incompatible` relationship;
- an explicit Boolean compatibility decision;
- the validated incoming public identity;
- the supported frozen public identity;
- deterministic public mismatch details.

No private scoring, governance, evidence intelligence, enforcement rules, or
internal exception details cross the boundary.

## Architecture protection

The translator imports only AI Test Lab public contract types. It does not
import, execute, modify, or expand Aquagear. The frozen reference application
remains an external contract producer.

## Validation

Focused tests cover exact translation, every individual identity mismatch,
multiple mismatch ordering, malformed requests, strict types, unknown fields,
immutability, approved serialization, and input non-mutation.

## Explicit non-goals

- provider transport or HTTP handling;
- Aquagear package imports;
- model or evaluation execution;
- round-trip orchestration;
- compatibility evidence production;
- compatibility enforcement;
- cross-version compatibility policy.

Those responsibilities remain in later ATL-A.01 slices.
