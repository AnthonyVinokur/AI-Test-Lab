# Changelog

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