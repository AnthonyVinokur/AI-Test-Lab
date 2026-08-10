## Definition of Done

Sprint 11.4 is complete when:

- all five built-in evaluation profiles are exercised through the runtime
  pipeline construction path;
- each profile produces its intended engine, metric, threshold, and
  quality-gate configuration;
- disabled engines are not instantiated or executed;
- profile configuration reaches `EvaluationPipeline` without introducing
  profile-specific execution architectures;
- `TestRunner` successfully executes with pipelines built from built-in
  profiles;
- unsupported runtime configurations fail predictably;
- existing evaluation behavior remains backward compatible;
- all automated tests pass.