# ATL-A.02.10 — Integrated Threat Review and A.02 Closure

## Status

**Implemented.** ATL-A.02 is closed after its focused and complete repository
regression suites pass.

## Goal

Review the completed A.02 evidence-intake boundary as one attack surface, close
the ambiguity found during that review, and freeze the verified public
behavior. This sprint adds no DTO, public field, provider integration, scoring
logic, or proprietary implementation.

## Integrated threat review

| Threat | A.02 control | Closure verification | Residual risk |
| --- | --- | --- | --- |
| Malformed or ambiguous JSON | Exact bytes, strict UTF-8, duplicate-key and non-standard-number rejection | Ambiguous public documents fail closed | Resource exhaustion requires an outer transport-size limit |
| Schema confusion | Frozen envelope, exact literals, forbidden extra fields | All A.02 and Aquagear versions are pinned | New versions require an explicit compatibility decision |
| Evidence tampering | Canonical SHA-256 evaluation and evidence identities | Modified evidence becomes a stable integrity failure | Digests prove integrity, not producer authenticity |
| Response substitution | Binding requires a completed correlated A.01 result | Safe correlation identities survive the public path | Trust in the injected A.01 port remains external |
| Transport substitution | Exact artifact type, content type, schema version, and strict base64 handling | Invalid transports normalize to public rejection | Transport security and authorization are deployment concerns |
| Secret or IP disclosure | Minimal public DTO, normalized messages, deterministic serializer | Provider state, payloads, secrets, and tracebacks are absent | Approved evidence content may itself contain sensitive data |
| Dependency capture | Provider-neutral dependency injection | AST guard rejects Aquagear runtime, SDK, and HTTP-client imports | Dependency and supply-chain scanning remain repository controls |
| Contract drift | Frozen constants, closure suite, canonical wire round trip | Version and wire invariants are regression locked | Any intentional change requires versioning and compatibility review |

### Review finding resolved

The A.02.08 decoder previously used ordinary JSON decoding, which can accept
duplicate object keys by silently keeping the last value. A.02.10 aligns the
public decoder with the strict A.02.02 intake rule: duplicate keys,
non-standard numeric constants, malformed JSON, and excessive nesting now fail
behind the stable serialization error. No accepted public document changes.

## Frozen A.02 flow

```text
correlated A.01 result
    -> exact evidence artifact
    -> strict document translation
    -> canonical digest verification
    -> exact compatibility verification
    -> response/evidence binding
    -> redacted failure normalization
    -> minimal public outcome
    -> deterministic UTF-8 JSON
```

## Closure invariants

1. Every A.02 contract version remains `1.0`.
2. Aquagear evidence export version remains `1`; architecture remains `v1`.
3. The public wire format remains deterministic compact UTF-8 JSON.
4. Only exact, integrity-valid evidence from a completed correlated response
   reaches the success branch.
5. Failure output remains stable, non-retryable, and redacted.
6. Duplicate keys, non-standard numbers, unknown fields, malformed documents,
   digest tampering, and incompatible versions fail closed.
7. The provider port is invoked once by the integrated A.01-to-A.02 path.
8. A.02 production modules remain independent of Aquagear runtime code,
   provider SDKs, and transport clients.

## Trust boundary and explicit residual risks

A.02 verifies structural integrity with SHA-256; it does not authenticate who
created the evidence. Authenticity requires a separately designed signature or
trusted transport contract. A.02 also does not impose byte-size or nesting
budgets, authorize callers, encrypt data, perform replay prevention, or decide
whether evidence content is safe to publish. Those controls belong at the
transport, deployment, or a future explicitly versioned security boundary.

## Change control

After closure, changes to an A.02 public field, literal, version, failure
mapping, canonical byte shape, digest input, compatibility rule, binding rule,
or dependency boundary are contract changes. They require a named follow-up
architecture sprint, threat and compatibility analysis, and an explicit
versioning decision.

Internal refactoring is allowed only while the A.02 closure suite and complete
repository suite remain green.

## Verification

```powershell
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
  tests/test_reference_architecture_a02_closure.py `
  -q

python -m pytest -q
```

## Repository placement

- `src/reference_architecture_conformance_evidence_binding_serialization.py`
- `tests/test_reference_architecture_a02_closure.py`
- `docs/sprints/atl-a.02.md`
- `docs/sprints/atl-a.02.10.md`

## Suggested commit

```text
security: review and close reference architecture A.02
```
