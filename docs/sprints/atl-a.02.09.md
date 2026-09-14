# ATL-A.02.09 — End-to-End Evidence-Binding Regression Verification

## Status

**Implemented.**

## Objective

Lock the complete A.01-to-A.02 evidence-binding behavior with regression tests
that cross every real boundary from a provider-neutral response to the frozen
A.02.08 public wire document.

## Verified path

The regression fixture executes the production composition:

1. perform one provider-neutral A.01 compatibility round trip;
2. translate and correlate the returned response;
3. extract its conformance-evidence artifact;
4. translate the untrusted evidence document;
5. verify both SHA-256 integrity identities;
6. enforce exact evidence compatibility;
7. bind the verified evidence to its correlated response;
8. normalize any ordinary rejection;
9. project the minimal A.02.07 public outcome;
10. encode and decode the deterministic A.02.08 JSON document.

## Regression coverage

- A valid artifact completes the full path and produces decodable verified
  public evidence.
- The provider port is called exactly once.
- Re-encoding the decoded success produces identical bytes.
- Missing artifacts, invalid transport identity, and corrupt integrity digests
  complete the same public path as stable, redacted failure outcomes.
- Safe integration and correlation identifiers survive both success and
  failure paths.
- Provider metadata, raw artifact data, base64 transport, source-system state,
  secrets, and tracebacks never appear in either public wire branch.
- A post-export attempt to add provider state is rejected by the frozen decoder.

## Architectural result

A.02.09 adds no new production contract and no new public field. It verifies
the contracts already frozen by A.02.01 through A.02.08 as one integrated
behavior. This keeps regression assurance separate from the implementation and
preserves the IP-protection boundary.

## Verification

```powershell
python -m pytest `
  tests/test_reference_architecture_conformance_evidence_binding_end_to_end.py `
  -q

python -m pytest `
  tests/test_reference_architecture_conformance_evidence_intake_contract.py `
  tests/test_reference_architecture_conformance_evidence_document_translation.py `
  tests/test_reference_architecture_conformance_evidence_integrity_verification.py `
  tests/test_reference_architecture_conformance_evidence_compatibility_verification.py `
  tests/test_reference_architecture_conformance_evidence_round_trip_binding.py `
  tests/test_reference_architecture_conformance_evidence_binding_failure_normalization.py `
  tests/test_reference_architecture_conformance_evidence_binding_outcome.py `
  tests/test_reference_architecture_conformance_evidence_binding_serialization.py `
  tests/test_reference_architecture_conformance_evidence_binding_end_to_end.py `
  -q

python -m pytest -q
```

## Repository placement

- `tests/test_reference_architecture_conformance_evidence_binding_end_to_end.py`
- `docs/sprints/atl-a.02.md`
- `docs/sprints/atl-a.02.09.md`

## Suggested commit

```text
test: verify evidence binding end to end
```
