# Changelog

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
