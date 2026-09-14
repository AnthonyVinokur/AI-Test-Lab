# ATL-A.02.05 — Round-Trip Evidence Binding

## Status

**Implemented.**

## Objective

Bind accepted Aquagear conformance evidence to the successful, correlated A.01
round-trip response that actually carried it.

This slice answers one narrow question:

> Did this exact response carry evidence that passed every A.02 acceptance gate?

## Binding behavior

The binder accepts an internal `ReferenceArchitectureRoundTripResultV1`, not a
free-standing evidence object. It then fails closed unless:

1. the A.01 correlation result is successful;
2. the provider-neutral response status is `completed`;
3. the response contains an artifact;
4. the artifact declares type `conformance-evidence`, content type
   `application/json`, and schema version `1.0`;
5. the artifact payload is valid strict base64;
6. the decoded bytes pass the A.02.02 untrusted-document translator;
7. both A.02.03 SHA-256 identities match; and
8. A.02.04 classifies the evidence target as `EXACT`.

Success returns an immutable internal binding containing only the validated
public response DTO and the validated evidence intake DTO. Raw provider state,
the integration adapter, proprietary evaluation meaning, and orchestration
internals are not projected into the binding.

## Why the evidence is genuinely bound

The caller cannot supply one response and a separate evidence object. The
binder decodes the evidence directly from that response's artifact payload.
This prevents a valid evidence package from being substituted for invalid or
unrelated bytes after the round trip.

Requiring `ReferenceArchitectureRoundTripResultV1` also preserves A.01's
request-response correlation gate. A merely well-formed response is not enough.

## Acceptance criteria

1. Valid evidence in a completed, correlated response binds successfully.
2. A response that is not completed fails closed.
3. A missing artifact fails closed.
4. Artifact type, content type, and schema version are exact-match fields.
5. Malformed evidence bytes fail closed through the A.02.02 boundary.
6. Evidence with a mismatched digest fails closed through A.02.03.
7. Only exact A.02.04 compatibility is accepted.
8. Arbitrary objects cannot impersonate an A.01 round-trip result.
9. The returned binding is frozen and omits raw provider state.

## Explicit non-goals

- reevaluating Aquagear's conformance verdict;
- interpreting evaluation scores, requirements, or governance meaning;
- normalizing binding failures (ATL-A.02.06+);
- defining a public A.02 outcome or wire format (ATL-A.02.06+);
- persistence, signatures, authentication, retries, or provider SDKs;
- importing, executing, or modifying Aquagear.

## Verification

```powershell
python -m pytest `
  tests/test_reference_architecture_conformance_evidence_intake_contract.py `
  tests/test_reference_architecture_conformance_evidence_document_translation.py `
  tests/test_reference_architecture_conformance_evidence_integrity_verification.py `
  tests/test_reference_architecture_conformance_evidence_compatibility_verification.py `
  tests/test_reference_architecture_conformance_evidence_round_trip_binding.py `
  -q
```

## Repository placement

- `src/reference_architecture_conformance_evidence_round_trip_binding.py`
- `tests/test_reference_architecture_conformance_evidence_round_trip_binding.py`
- `docs/sprints/atl-a.02.md`
- `docs/sprints/atl-a.02.05.md`

## Suggested commit

```text
feat: bind conformance evidence to correlated round trip
```
