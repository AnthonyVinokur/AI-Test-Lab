# Sprint 11.8 — Evaluation Result Provenance & Explainability

## Goal

Make every evaluation metric result traceable to the configuration and profile that produced it without introducing a second execution architecture.

## Implemented

- Added profile name and version to `EvaluationRequest` so provenance travels through the existing engine contract.
- Extended `MetricResult` with:
  - `runtime_options`
  - `profile_name`
  - `profile_version`
  - `evaluator_model`
- Updated `EvaluationPipeline` to retain selected profile identity and attach it to built-in and external metric evidence.
- Updated `create_pipeline_from_profile()` to pass profile identity into the pipeline.
- Updated `DeepEvalEngine` to preserve the effective runtime options actually used by the metric, including defaults.
- Preserved configured DeepEval judge-model identity when available.
- Kept existing metric score, threshold, pass/fail, engine, and reason behavior unchanged.
- Preserved plugin compatibility: external engines still receive `EvaluationRequest` and return `MetricResult`.

## Provenance flow

```text
EvaluationProfile
    -> EvaluationPipeline
    -> EvaluationRequest
    -> Evaluation Engine
    -> MetricResult
    -> EvaluationResult.evaluation_results
```

## Result evidence example

```text
engine: deepeval
metric_name: answer_relevancy
score: 0.93
threshold: 0.81
passed: true
reason: The response is relevant.
runtime_options:
  include_reason: false
  async_mode: false
profile_name: deep-quality
profile_version: 1.0
evaluator_model: test-judge
```

## Compatibility

No parallel pipeline or provenance-specific engine was introduced. Existing callers that construct `EvaluationRequest`, `MetricResult`, or `EvaluationPipeline` remain compatible because all new provenance fields are optional or have defaults.

## Verification

Focused tests cover:

- request-level profile provenance;
- assertion evidence inheriting profile identity;
- DeepEval effective runtime options;
- DeepEval profile and evaluator-model provenance;
- preservation of runtime-option validation behavior.

The full repository test suite must pass before the sprint is merged.
