# Changelog
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