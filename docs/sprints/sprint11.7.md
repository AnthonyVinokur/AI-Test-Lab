# Sprint 11.7 — Evaluation Runtime Deduplication and Evidence Flow

## Objective

Sprint 11.7 strengthens the evaluation runtime architecture by removing duplicated configuration handling and establishing a single normalized evidence flow through the evaluation pipeline.

The sprint follows a core architectural principle:

> Normalize once at the engine boundary and preserve the normalized result downstream.

The goal is not to remove every repeated line of code. The goal is to ensure that each responsibility has one clear owner and that evaluation engines do not create parallel execution or result architectures.

## Architectural Principles

Sprint 11.7 establishes the following rules for the AI Test Lab evaluation architecture:

1. One evaluation execution path through `EvaluationPipeline`.
2. One normalized metric result contract through `MetricResult`.
3. One runtime configuration contract through `EvaluationRequest`.
4. Evaluation engines translate engine-specific behavior into normalized AI Test Lab results.
5. The pipeline orchestrates results but does not rebuild engine evidence.
6. Profile configuration is interpreted once and passed downstream.
7. Shared abstractions are introduced only when responsibilities are genuinely shared.

## Runtime Configuration Ownership

`EvaluationRequest` now owns resolution of effective per-metric runtime configuration.

Two helper methods were introduced:

* `threshold_for(metric_name)`
* `options_for(metric_name)`

This moves threshold and runtime-option resolution out of individual evaluation engines.

Previously, an engine could independently inspect:

* the shared threshold;
* per-metric threshold overrides;
* metric runtime options.

That could eventually lead to different engines interpreting the same configuration differently.

The runtime flow is now:

```text
Evaluation Profile
        ↓
Pipeline Builder
        ↓
EvaluationPipeline
        ↓
EvaluationRequest
   ├── threshold_for(metric)
   └── options_for(metric)
        ↓
Evaluation Engine
```

## Configuration Validation

`EvaluationRequest` now verifies that per-metric configuration refers only to metrics selected for the evaluation.

The request rejects:

* threshold overrides for unselected metrics;
* runtime options for unselected metrics.

Metric-name lookup also normalizes whitespace and casing.

Runtime option dictionaries are returned as defensive copies so an evaluation engine cannot accidentally mutate the request configuration.

## Duplication Removed

Sprint 11.7 removed several concrete duplications discovered in the runtime code.

### EvaluationPipeline

Duplicate assignments inside `EvaluationPipeline.__init__()` were removed.

The pipeline now initializes runtime configuration only once.

### DeepEvalEngine

Duplicate imports were removed.

Duplicate metric-option validation was removed.

DeepEval no longer independently resolves metric thresholds and runtime options.

Instead it calls:

```python
request.threshold_for(metric_name)
request.options_for(metric_name)
```

### Pipeline Builder

Duplicate metric-name assignment was removed.

An unused threshold variable was removed.

Unnecessary duplicated spacing was cleaned up.

## Normalized Evidence Contract

AI Test Lab already had the appropriate normalized result model:

```text
MetricResult
├── engine
├── metric_name
├── score
├── threshold
├── passed
└── reason
```

Sprint 11.7 deliberately reuses this existing model instead of creating additional result types such as engine-specific evidence models.

External engines normalize their results into `MetricResult`.

`EvaluationPipeline` then preserves those results inside:

```text
EvaluationResult.evaluation_results
```

The resulting evidence path is:

```text
Evaluation Engine
        ↓
MetricResult
        ↓
EvaluationPipeline
        ↓
EvaluationResult
```

## Evidence Flow Verification

New tests prove that normalized evidence survives the complete runtime flow.

The tests verify that:

* builtin assertion evidence survives into `EvaluationResult`;
* external metric evidence survives into `EvaluationResult`;
* engine name is preserved;
* metric name is preserved;
* score is preserved;
* configured threshold is preserved;
* pass/fail verdict is preserved;
* evaluator reason is preserved;
* failed external evidence remains available when a quality gate fails.

A dedicated identity test also proves that the pipeline does not rebuild the external metric result.

Conceptually:

```python
assert result.evaluation_results[1] is produced_result
```

This verifies that the exact normalized `MetricResult` produced by the engine is carried through the pipeline.

## Tests Added

Two new test modules were added:

```text
tests/test_evaluation_request_runtime_config.py
tests/test_evaluation_evidence_flow.py
```

The runtime configuration tests verify:

* per-metric threshold overrides;
* fallback to shared threshold;
* normalized metric-name lookup;
* defensive runtime-option copies;
* rejection of threshold configuration for unselected metrics;
* rejection of runtime options for unselected metrics.

The evidence-flow tests verify:

* normalized evidence survives through the pipeline;
* failed external evidence survives quality-gate resolution;
* the pipeline preserves the original normalized metric result instead of rebuilding it.

## Verification

Focused runtime and evidence tests:

```text
38 passed
```

Full regression suite:

```text
175 passed
0 failed
```

`git diff --check` completed with no errors.

## Result

Sprint 11.7 establishes an architectural rule for future evaluation engines and capabilities:

> Adapters and engines normalize. The pipeline orchestrates. Result models preserve evidence.

Future integrations should plug into the same execution pipeline and produce the same normalized `MetricResult` contract rather than introducing engine-specific execution or reporting paths.

This reduces architectural duplication while preserving extensibility for future evaluation engines, reporting, dashboards, governance evidence, and quality gates.
