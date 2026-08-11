# Sprint 11.6 — Per-Metric Runtime Options

## Status

Completed.

## Objective

Extend the evaluation-profile runtime architecture so individual evaluation
metrics can carry metric-specific runtime options from profile configuration
through the evaluation pipeline and into the external evaluation engine.

Sprint 11.5 introduced per-metric runtime thresholds.

Sprint 11.6 extends the same architecture to support per-metric runtime options
without introducing a second execution path or coupling the generic evaluation
pipeline to DeepEval-specific configuration.

The resulting configuration flow is:

Evaluation Profile
→ Pipeline Builder
→ EvaluationPipeline
→ EvaluationRequest
→ External Evaluation Engine
→ Metric Construction

## Motivation

Evaluation metrics may require runtime configuration beyond a numerical
threshold.

For example, a DeepEval metric may need configuration such as:

- `include_reason`
- `async_mode`

These settings belong to individual metrics rather than to the evaluation
pipeline as a whole.

Before Sprint 11.6, `MetricConfig.options` existed at the profile layer but the
configuration did not survive into runtime execution.

Sprint 11.6 closes that gap.

## Implementation

### 1. EvaluationRequest Runtime Contract

`EvaluationRequest` was extended with per-metric runtime options:

```python
metric_options: dict[str, dict[str, Any]]