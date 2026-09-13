# ATL–A.01.5 — Request/Response Correlation

## Objective

Associate one validated provider-neutral response with the exact request that
originated it, without importing Aquagear implementation code or adding a
transport, provider, persistence, retry, or timeout layer.

## Public contract

The correlation layer publishes an immutable `1.0` result containing:

- the minimal validated request identity;
- the already translated response DTO;
- a deterministic `correlated` decision; and
- ordered identity mismatches when the response does not belong to the request.

The frozen correlation fields are evaluated in this order:

1. `contract_version`
2. `integration_id`
3. `correlation_id`
4. `operation`

`source_system` is required and validated on both sides, but is intentionally
not compared. A provider-neutral request and its response can be produced by
different systems.

## Failure semantics

- Malformed request identity raises
  `ReferenceArchitectureRequestResponseCorrelationError`.
- An unvalidated response raises the same stable boundary error.
- A well-formed identity mismatch is data, not an infrastructure failure; it
  returns `correlated=False` and ordered mismatch records.
- The layer does not catch or normalize response-translation failures.

## IP and architecture boundaries

- Public DTOs extend `PublicContractModel` and use the approved serializer.
- Undeclared fields are forbidden and models are immutable.
- No provider SDK, Aquagear runtime module, HTTP type, internal evidence model,
  policy algorithm, retry rule, or commercial scoring logic crosses the public
  boundary.
- ATL–A.01.1 through ATL–A.01.4 remain unchanged.

## Verification

```powershell
python -m pytest `
  tests/test_reference_architecture_response_translation.py `
  tests/test_reference_architecture_request_response_correlation.py `
  -q
```

The focused suite covers successful correlation, direct validated DTO input,
every variable correlation field, deterministic multi-mismatch ordering,
different source systems, immutable mapping input, malformed requests,
untranslated responses, result consistency, immutability, extra-field
rejection, and public serialization.

## Explicit exclusions

- request dispatch or response polling;
- HTTP or provider error normalization;
- timeout, retry, replay, deduplication, or persistence;
- multi-response aggregation;
- evidence acceptance or policy enforcement;
- changes to the frozen Aquagear reference architecture.
