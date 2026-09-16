# Changelog

## ATL-A.29 — Protected-Operation Outcome Settlement and Lifecycle Finalization

### Added

- Strict immutable settlement requests, versioned policies, authoritative lineage
  inputs, statuses, stable reasons, evidence, results, repository ports, signer
  port, and allowlisted public DTO.
- Complete A.26 consumption, A.27 execution, and A.28 reconciliation admission
  with digest, freshness, policy, and exact lifecycle-binding verification.
- Deterministic fail-closed lifecycle mapping to `settled_success`,
  `settled_failure`, `suspended`, or `rejected` without external-state mutation.
- Thread-safe and SQLite single-winner repositories with exact replay, conflict
  rejection, immutable commits, pending-record recovery, and unknown-commit safety.
- Canonical domain-separated evidence identity, signature verification, stable
  timestamps, and protected-field exclusion from public output.

### Security

- Only an authentic, fresh, exactly bound A.28 `verified` attestation can produce
  `settled_success`; A.27 completion alone has no settlement authority.
- Mismatch, uncertainty, invalidity, staleness, storage ambiguity, and concurrent
  conflict cannot be promoted to success.
- ATL-A.29 cannot execute, observe, retry, remediate, compensate, roll back, or
  restore authorization, and public output exposes no evidence digests or secrets.

## ATL-A.28 — Protected-Operation Outcome Verification and Reconciliation

### Added

- Authoritative committed ATL-A.27 evidence intake with exact A.26 lineage,
  execution-command, manifest, adapter, operation, target, and parameter binding.
- Deterministic manifest-derived expected postconditions and provider-neutral,
  exact-match, versioned, read-only observer registration.
- Fresh observation acquisition, deterministic normalization, and fail-closed
  `verified`, `mismatch`, `indeterminate`, and `invalid` reconciliation.
- Thread-safe and SQLite append-only evidence stores with exact retry, conflict,
  concurrent-claim, later-round, and unknown-commit behavior.
- Digest-verifiable immutable attestations and an allowlisted public projection.

### Security

- Execution success claims never substitute for independently observed provider
  state, and uncertainty never defaults to verification.
- A.28 cannot invoke, retry, repair, compensate, roll back, or consume authorization.
- Public evidence excludes raw observations, provider payloads, authorization
  artifacts, credentials, policy mechanics, canonical parameters, and exceptions.

## ATL-A.25 — Trusted Deployment Continued-Operation Authorization

### Added

- Strict A.24-authenticated, fail-closed authorization for one exact continued-operation proposition.
- Immutable policy, grant, authority, resolved-key, signed-artifact, verification, outcome, and public contracts.
- Deterministic domain-separated proposition identity and Ed25519 authorization signatures with no retained private keys.
- Independent A.26-ready verifier and strict canonical request/artifact serialization boundaries.
- Security, expiry, mutation, substitution, lifecycle, protected-data, and A.22–A.24 compatibility coverage.

### Security

- Only internally verified `verified + ready` A.24 results can authorize; caller-created trusted references are insufficient.
- Authorized validity cannot exceed readiness, policy, signer, or resolved-key validity.
- Public output excludes signatures, digests, fingerprints, authority identities, policy mechanics, trusted references, and internal diagnostics.

## ATL-A.24 — Trusted Deployment Readiness Authentication and Provenance Verification

- Added strict ATL-A.23 result adaptation and deterministic, domain-separated binding fingerprints and signing payloads.
- Added immutable readiness-authentication envelope, issuer/key authorization policy, resolved-key lifecycle, verification outcome, and trusted-reference contracts.
- Added independent Ed25519 signature, authority, lifecycle, policy, exact-binding, and freshness verification without recomputing ATL-A.22.
- Added fail-closed `verified`, `rejected`, and `review_required` outcomes; only authenticated `ready` results mint an internal trusted reference.
- Added a minimal public projection with normalized non-oracular reasons and no signatures, keys, evidence, revisions, or internal diagnostics.
- Added tampering, substitution, expiry, missing-material, authorization, determinism, immutability, serialization, compatibility, and protected-boundary coverage.

## ATL-A.17 — Trusted Deployment Outcome Verification and Reconciliation

- Added verified ATL-A.16 attestation intake, derived expected-state projection, and an observer-only provider-neutral port.
- Added allowlisted observer resolution, evidence freshness, normalized observations, deterministic reconciliation, and atomic replay-safe verification claims.
- Added immutable digest-verifiable verification attestations and a minimal public outcome projection.

## ATL-A.14 — Trusted Deployment Authorization

- Added strict deployment-authorization requests and separately digested versioned authorization policy.
- Added narrow verified ATL-A.12 and ATL-A.13 references with exact cross-attestation and deployment-context binding.
- Added deterministic fail-closed authorization outcomes and immutable canonical signed authorization attestations.
- Added hash-linked revocation and supersession lifecycle records, independent safe verification, sanitized public projection, and threat/regression coverage.

## ATL-A.13 — Authorized Deployment Approval and Release Attestation

- Added exact artifact-and-target approval contracts, strict translation, scoped authority, separation of duties, role quorum, signed attestations, append-only lifecycle verification, and safe public deployment authorization.

## ATL-A.12 — Evidence-Based Policy Decision and Quality-Gate Attestation

- Added strict policy/request contracts, verified-evidence admission, canonical policy identity, deterministic requirement evaluation, fail-closed aggregation, signed decision attestations, and minimal public outcomes.

## ATL-A.07 — Verifiable Evidence Packages and Audit Export

- Added deterministic, portable public evidence-package contracts and canonical JSON.
- Added strict untrusted request translation and authorized verified-ledger selection.
- Added allowlisted record projection, chain inclusion proofs, and offline verification.
- Added normalized safe failures plus tampering, completeness, and stability coverage.

## ATL-A.06 — Trusted Evidence Ledger and Chain of Custody

- Added a provider-neutral, append-only trusted evidence ledger reference boundary.
- Added strict append translation and factory-minted ATL-A.05 admission authorization.
- Added exact evidence/admission/provenance/run binding and trusted timestamp assignment.
- Added deterministic identities, supersession chains, replay/conflict handling,
  structured verification, and safe deterministic public outcomes.


---

## 2. Update `docs/changelog.md`

Add this **directly below `# Changelog` and above Sprint 11.1**:

```markdown
## Sprint 11.2 — Profile CLI UX & Validation

### Added

- Added `--list-evaluation-profiles` CLI support.
- Added built-in evaluation profile discovery from the command line.
- Added semantic evaluation-engine validation.
- Added evaluation metric validation.
- Added DeepEval metric capability validation for:
  - `answer_relevancy`
  - `faithfulness`
  - `hallucination`
- Added CLI integration tests for profile discovery and invalid profile handling.

### Improved

- `--evaluation-profile` now clearly supports both built-in profile names and YAML/JSON file paths.
- Unknown profile errors now display the available built-in profiles.
- Profile validation now occurs before test-case loading.
- Invalid metrics are rejected before model execution.
- Unsupported evaluation engines are treated as configuration-validation failures.
- Evaluation profile handling now follows a fail-fast execution model.

### Validation

- ✅ 147 automated tests passing
- ✅ No regressions introduced

## Sprint 11.1 — Evaluation Profile Catalog

- Added built-in evaluation profiles:
  `default`, `fast-ci`, `deep-quality`, `rag`, and `enterprise`.
- Added catalog discovery and profile-name resolution.
- Integrated built-in profiles with the existing evaluation configuration loader.
- Preserved explicit YAML, YML, and JSON profile paths.
- Added catalog and loader tests.
- Full regression suite: 133 passing tests.
- 
## Sprint 11.0

### Added

- Configuration-driven evaluation profiles
- YAML and JSON profile support
- Profile validation
- Evaluation pipeline builder
- CLI support for evaluation profiles

### Improved

- Runtime evaluation configuration
- Engine selection architecture
- Foundation for enterprise evaluation policies
## Sprint 10.9

### Added

- DeepEval integration package
- DeepEval evaluation engine
- DeepEval factory
- DeepEval metric registry
- DeepEval exception hierarchy
- Plugin registry integration
- End-to-end plugin workflow
- Semantic evaluation support

### Changed

- AI Test Lab now supports external semantic evaluation through the plugin architecture.
- External evaluation engines can now be instantiated from configuration through registered factories.

### Validation

- ✅ 118 automated tests passing
- No regressions introduced

## Sprint 10.8

### Added

- External evaluation plugin architecture
- Evaluation engine registry
- Plugin discovery mechanism
- ExternalEvaluationEngine protocol
- Plugin exception hierarchy
- Plugin registration and validation
- Comprehensive registry and discovery tests

### Changed

- Evaluation Pipeline now depends on a shared engine interface instead of concrete implementations.
- External evaluation engines are now fully decoupled from the framework core.

### Validation

- ✅ 99 automated tests passing
- No regressions introduced

## Sprint 10.5

### Added

- Engine-agnostic reporting architecture
- Normalized evaluation result support
- Shared reporting pipeline

### Changed

- JSON reporter now consumes normalized evaluation results
- HTML reporter now consumes normalized evaluation results

### Improved

- Reporter maintainability
- Future evaluation engine compatibility
- Reporting architecture

## Sprint 10.6

### Added

- Evaluation framework
- EvaluationEngine abstraction
- Normalized EvaluationResult model
- EvaluationPipeline orchestration
- Engine-independent architecture

### Improved

- Separation of evaluation and reporting
- Extensibility for future evaluation engines
- Foundation for enterprise AI quality workflows
- ## Sprint 10.7

### Added

- Configurable VerdictPolicy
- Quality gate aggregation
- Strict ALL_METRICS policy
- Backward-compatible ASSERTION_ONLY policy
- Expanded evaluation pipeline tests

### Improved

- Evaluation reasoning
- Final verdict generation
- Pipeline architecture

### Validation

- 89 pytest tests passing
# ATL-A.19 — Trusted Deployment Integrity Incident Management

### Added

- Immutable digest-verifiable incident attestations bound to verified deployment integrity findings.
- Versioned deterministic severity rules, evidence preservation, safe containment requests, and idempotent incident storage.
- Verified-only containment and resolution transition contract; no remediation is silently executed.

# ATL-A.21 — Trusted Deployment Post-Incident Closure and Preventive Assurance

### Added

- Immutable, versioned closure records bound to resolved incidents, reconciliation, and passed ATL-A.20 remediation verification.
- Structured root-cause and impact classifications plus immutable preventive-action records and dispositions.
- Safe public closure attestations and fail-closed lifecycle, tamper, authorization-binding, and incomplete-evidence coverage.

# ATL-A.18 — Trusted Deployment Continuous Integrity Monitoring and Trust Revocation

### Added

- Immutable A.17-derived trusted deployment baselines and configuration-binding retention.
- Deterministic continuous integrity observations, drift classes, trust statuses, and safe remediation signals.
- Fail-closed authorization lifecycle handling, revocation records, and tamper-verifiable results.

# ATL-A.16 — Trusted Deployment Execution and Outcome Attestation

### Added

- Frozen provider-neutral execution contracts and strict canonical input translation.
- Narrow ATL-A.15 receipt verification, exact admission binding, and command identity.
- Versioned execution policy and registered-adapter capability admission.
- Atomic claims, idempotent replay, conflict protection, and concurrency-safe execution.
- Normalized provider outcomes and immutable digest-verifiable execution attestations.
- Explicit safe public projection and backward-compatible ATL-A.15 executor adapter.

### Security

- Only an internally verified permitted receipt can reach a registered adapter.
- Ambiguous provider results remain `outcome_unknown` and are not retried.
- Public output excludes credentials, raw provider data, internal state, and proprietary policy logic.

# ATL-A.15 — Trusted Deployment Admission Enforcement

### Added

- Strict immutable deployment-admission contracts and untrusted-input translation.
- Deterministic canonical request identity and exact ATL-A.14 authorization binding.
- Narrow integration with ATL-A.14's approved safe verifier.
- Versioned enforcement policy for operations, environment classifications, lifetime,
  clock skew, and single-use or reusable authorization consumption.
- Thread-safe atomic replay and idempotency state with immutable enforcement receipts.
- Provider-neutral mandatory gateway that invokes an executor only after permission.
- Sanitized public admission projection and threat, replay, concurrency, and boundary tests.

### Security

- Admission has one success state: `permitted`; all other outcomes block execution.
- Verifier, lifecycle-store, adapter, unsupported-input, and executor failures fail closed.
- Public results expose no proprietary policy, authorization reasoning, signatures,
  consumption internals, raw exceptions, or provider details.

# ATL-A.26 — Continued-Operation Enforcement and Atomic Authorization Consumption

### Added

- Strict immutable continued-operation enforcement contracts and canonical request binding.
- Exact ATL-A.25 artifact, digest, lifecycle, validity, policy, gateway, and operation checks.
- Storage-neutral atomic consumption contract with in-memory and durable SQLite adapters.
- Storage-level single-use and request-ID uniqueness, idempotent recovery, and replay blocking.
- Deterministic immutable enforcement evidence and an allowlisted public result projection.

### Security

- Permission is issued only after successful atomic authorization consumption.
- Concurrent distinct requests have one winner; storage failure and unknown commit state fail closed.
- Consumed authorizations remain terminal and cannot be restored after protected-operation failure.

# ATL-A.27 — Trusted Continued-Operation Execution and Outcome Attestation

### Added

- Strict immutable execution, trusted-permit, operation-manifest, claim, adapter-result,
  attestation, storage-port, and public projection contracts.
- Authoritative ATL-A.26 consumption resolution with exact evidence and protected-operation
  binding plus domain-separated execution-command identity.
- Registered operation and adapter admission with manifest, policy, version, capability,
  deployment, and execution-window enforcement.
- Four-key atomic at-most-once execution claims with thread-safe and durable SQLite stores.
- Explicit provider success, failure, rejection, timeout, and unknown-outcome handling with
  deterministic digest-verifiable attestations and persisted-result recovery.

### Security

- Callers cannot inject trusted permits, raw commands, unrestricted parameters, credentials,
  provider responses, or trust-bypass flags.
- A consumed authorization produces at most one execution claim and one framework-controlled
  adapter invocation; exact retries never reinvoke it.
- Adapter exceptions, malformed responses, and post-invocation persistence failures remain
  `outcome_unknown`; protected-operation failure never restores ATL-A.26 consumption.
