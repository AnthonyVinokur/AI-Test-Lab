# ATL-A.01.3 — Provider-Neutral Reference Integration Adapter

## Status

**Implemented.**

## Objective

Connect the ATL-A.01.2 compatibility handshake to an injected integration
port without importing Aquagear, choosing a transport, or coupling AI Test Lab
to any model provider.

This slice answers one narrow question: may a structurally valid external
request enter a reference-integration port under the frozen Aquagear v1
contract?

## Adapter behavior

`src/reference_architecture_integration_adapter.py` defines a small
provider-neutral port and an adapter around it.

1. The adapter sends the untrusted mapping through the ATL-A.01.2 translator.
2. Malformed input retains `ReferenceArchitectureRequestTranslationError`.
3. A well-formed but incompatible identity raises
   `ReferenceArchitectureIncompatibleError` before the port is invoked.
4. An exact identity invokes the injected port once with the validated,
   immutable public request DTO.
5. The response is returned unchanged alongside the compatibility decision.

The adapter does not catch or reclassify a port failure. A future slice may
define error normalization, but this sprint does not guess that contract.

## Provider-neutral boundary

The port is a Python protocol with one operation: `integrate(request)`. It has
no HTTP client, URL, credential, SDK, Ollama type, cloud-provider name, model
name, retry policy, timeout, or serialization assumption. Tests use simple
recording and failing fakes, proving that the adapter depends on behavior rather
than a concrete provider.

## IP and architecture protection

- Aquagear remains frozen and external; no Aquagear package is imported.
- Only the validated public compatibility DTO crosses into the port.
- The generic provider response is held in an internal frozen result and is
  not presented as an approved public contract.
- No scoring, governance, evidence intelligence, enforcement logic, or private
  exception detail is added to the public boundary.

## Validation

Focused tests cover exact integration, one-time port invocation, incompatible
short-circuiting, stable mismatch details, malformed inputs, unchanged provider
responses, unchanged provider failures, invalid ports, result immutability, and
input non-mutation.

Recommended verification:

```powershell
python -m pytest `
  tests/test_reference_architecture_compatibility_contract.py `
  tests/test_reference_architecture_request_translation.py `
  tests/test_reference_architecture_integration_adapter.py `
  -q
```

## Explicit non-goals

- HTTP or message-queue transport;
- provider SDK integration;
- model or evaluation execution;
- credentials, retry, timeout, or availability policy;
- provider-error normalization;
- round-trip response translation;
- compatibility evidence or enforcement;
- Aquagear feature expansion;
- cross-version compatibility.
