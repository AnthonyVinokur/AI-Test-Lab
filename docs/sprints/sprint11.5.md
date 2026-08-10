# Sprint 11.5 --- Per-Metric Runtime Configuration

## Status

**Completed**

Final regression result:

``` text
162 passed in 4.29s
```

------------------------------------------------------------------------

## Goal

Extend the evaluation-profile runtime so individual evaluation metrics
can use independent thresholds.

Before Sprint 11.5, an evaluation profile could define thresholds for
individual metrics, but the runtime pipeline reduced those values to one
shared threshold.

For example, a profile could define:

``` yaml
metrics:
  - name: answer_relevancy
    threshold: 0.80

  - name: faithfulness
    threshold: 0.85
```

However, the runtime required all enabled metrics to use the same
threshold.

Sprint 11.5 removes that restriction.

------------------------------------------------------------------------

## Problem

The profile configuration layer already supported metric-specific
thresholds, but the runtime contract did not.

The previous runtime flow was effectively:

``` text
Evaluation Profile
        ↓
Metric configurations
        ↓
pipeline_builder.py
        ↓
One shared threshold
        ↓
EvaluationPipeline
        ↓
EvaluationRequest
        ↓
DeepEvalEngine
```

`EvaluationRequest` contained:

``` python
metrics: tuple[str, ...]
threshold: float
```

This meant multiple metrics could be requested, but only one threshold
could be supplied to the evaluation engine.

The profile pipeline builder therefore rejected profiles containing
different thresholds for enabled metrics.

------------------------------------------------------------------------

## Implementation

### 1. Added per-metric thresholds to EvaluationRequest

`EvaluationRequest` was extended with a per-metric threshold mapping.

Conceptually:

``` python
metric_thresholds: dict[str, float]
```

The existing shared `threshold` remains available as a fallback.

This preserves backward compatibility with existing runtime callers.

The resulting contract supports:

``` text
shared threshold:
    0.70

metric overrides:
    answer_relevancy → 0.80
    faithfulness     → 0.85
```

### 2. Added metric-threshold validation

Per-metric threshold configuration is validated before evaluation.

Metric threshold values must remain within the valid evaluation range:

``` text
0.0 <= threshold <= 1.0
```

Invalid metric threshold configuration therefore fails early rather than
reaching an evaluation engine.

### 3. Updated DeepEvalEngine

`DeepEvalEngine` now resolves the threshold independently for every
requested metric.

Resolution follows:

``` text
Does the metric have an explicit threshold?
                │
          ┌─────┴─────┐
         Yes          No
          │            │
          ▼            ▼
 metric-specific    shared request
    threshold        threshold
```

Conceptually:

``` python
metric_threshold = request.metric_thresholds.get(
    metric_name,
    request.threshold,
)
```

The resolved threshold is used consistently for:

-   DeepEval metric construction
-   fallback score comparison
-   normalized `MetricResult.threshold`

This ensures the reported threshold is the threshold actually used
during evaluation.

### 4. Updated EvaluationPipeline

`EvaluationPipeline.evaluate()` now accepts per-metric threshold
overrides and transports them through `EvaluationRequest`.

The pipeline also supports profile-provided default metric thresholds.

This allows configuration loaded when the pipeline is constructed to
automatically reach runtime evaluation without requiring every caller to
manually supply metric thresholds.

Runtime callers can still provide explicit configuration when required.

### 5. Updated Profile → Pipeline Mapping

`create_pipeline_from_profile()` now preserves individual metric
thresholds instead of collapsing them into one value.

The builder constructs a mapping such as:

``` python
{
    "answer_relevancy": 0.80,
    "faithfulness": 0.85,
}
```

and supplies it to `EvaluationPipeline` as its default per-metric
configuration.

The previous `_resolve_threshold()` restriction requiring one shared
metric threshold was removed.

------------------------------------------------------------------------

## Runtime Architecture After Sprint 11.5

The runtime configuration path is now:

``` text
Evaluation Profile
        │
        ▼
Engine Configuration
        │
        ▼
Metric Configuration
        │
        ├── answer_relevancy → 0.80
        └── faithfulness     → 0.85
        │
        ▼
pipeline_builder.py
        │
        ▼
EvaluationPipeline
        │
        ▼
EvaluationRequest
        │
        ▼
DeepEvalEngine
        │
        ├── Answer Relevancy Metric → threshold 0.80
        └── Faithfulness Metric     → threshold 0.85
        │
        ▼
MetricResult
```

The evaluation profile is therefore no longer only descriptive
configuration.

Its individual metric thresholds now control actual runtime behavior.

------------------------------------------------------------------------

## Backward Compatibility

Sprint 11.5 intentionally preserves the existing shared-threshold API.

Existing callers can continue using:

``` python
threshold=0.7
```

without supplying metric-specific configuration.

When no per-metric override exists, the runtime falls back to the shared
threshold.

This allows gradual adoption of richer evaluation profiles without
breaking existing evaluation workflows.

------------------------------------------------------------------------

## Tests Added and Updated

Sprint 11.5 introduced or updated coverage for:

-   per-metric threshold transport
-   multiple metrics with different thresholds
-   shared-threshold fallback behavior
-   profile-to-pipeline metric threshold mapping
-   built-in profile runtime configuration
-   DeepEval metric threshold construction
-   normalized result threshold reporting

An obsolete regression test that expected different metric thresholds to
be rejected was replaced with coverage verifying that different
thresholds are now supported.

The built-in `deep-quality` profile was verified to preserve its
configured thresholds:

``` text
answer_relevancy → 0.80
faithfulness     → 0.85
```

------------------------------------------------------------------------

## Verification

Focused tests were run throughout implementation for:

``` text
test_deepeval_engine.py
test_evaluation_pipeline.py
test_evaluation_profile_pipeline.py
test_builtin_profile_runtime.py
```

Final full regression suite:

``` text
162 passed in 4.29s
```

No existing regression failures remained after updating tests
representing the previous shared-threshold restriction.

------------------------------------------------------------------------

## Result

Sprint 11.5 closes an important gap between evaluation-profile
configuration and runtime execution.

Before:

``` text
Multiple configured metrics
        ↓
One runtime threshold
```

After:

``` text
Multiple configured metrics
        ↓
Independent runtime thresholds
```

AI Test Lab can now express evaluation policies such as:

``` text
Answer relevancy ≥ 0.80
Faithfulness    ≥ 0.85
```

without changing application code.

This provides a stronger foundation for customer-specific evaluation
profiles, quality policies, CI/CD evaluation gates, and future
governance-oriented configuration.

------------------------------------------------------------------------

## Sprint 11.5 Completion Criteria

-   [x] Support per-metric thresholds in the runtime request model
-   [x] Validate per-metric threshold values
-   [x] Preserve shared-threshold fallback behavior
-   [x] Resolve thresholds independently inside DeepEvalEngine
-   [x] Transport metric thresholds through EvaluationPipeline
-   [x] Preserve profile metric thresholds in pipeline construction
-   [x] Remove the one-shared-threshold runtime restriction
-   [x] Update obsolete regression expectations
-   [x] Verify built-in profile runtime behavior
-   [x] Pass the complete regression suite

**Sprint 11.5 complete.**
