# Sprint 11.11A — Evidence Contract Stabilization

## Status

**Completed**

Sprint 11.11A stabilizes the evaluation evidence contract before formal Report Schema v1.0 validation is introduced.

Final verification:

```text
185 passed in 10.83s
```

## Goal

The goal of Sprint 11.11A was to ensure that evidence produced by the evaluation runtime survives intact into serialized report artifacts.

The sprint addressed four gaps discovered during inspection of the post-Sprint 11.10 serialization path:

* engine execution outcomes were used during verdict resolution but discarded before reporting
* model cost information was not propagated from `ModelResponse` into `TestResult`
* model-level total cost defaulted to zero because aggregation was not populated
* `XFAIL` and `XPASS` outcomes were not explicitly represented in report summaries

## Evidence Flow Before Sprint 11.11A

```text
EvaluationPipeline
        |
        +-- MetricResult[]
        |
        +-- EngineExecutionResult[]
        |
        v
Verdict Resolution
        |
        v
EvaluationResult
        |
        +-- MetricResult[]
        |
        X  EngineExecutionResult discarded
        |
        v
TestResult
        |
        v
JsonReporter
```

Engine execution evidence could influence the final verdict but did not survive into the serialized report.

## Engine Execution Evidence

`EvaluationResult` and `TestResult` now preserve:

```python
engine_results: list[EngineExecutionResult]
```

This means external evaluation engine execution outcomes now survive the complete evidence path:

```text
External Evaluation Engine
        |
        v
EngineExecutionResult
        |
        v
EvaluationPipeline
        |
        v
EvaluationResult
        |
        v
TestResult
        |
        v
JsonReporter
        |
        v
JSON evidence artifact
```

A failed evaluator can now be serialized as structured evidence:

```json
{
  "engine": "deepeval",
  "succeeded": false,
  "error": "judge unavailable"
}
```

This preserves the distinction introduced in Sprint 11.10 between:

```text
metric failure
```

and:

```text
engine execution failure
```

## Cost Propagation

`TestRunner` now propagates:

```python
model_response.estimated_cost_usd
```

into:

```python
TestResult.estimated_cost_usd
```

The complete cost evidence path is now:

```text
ModelResponse
        |
        v
TestResult
        |
        v
ModelSummary
        |
        v
JsonReporter
```

A dedicated regression test verifies non-zero cost propagation.

Example:

```text
0.012345 USD
```

is preserved from the model response into the resulting `TestResult`.

## Model Cost Aggregation

`build_model_summaries()` now calculates:

```python
total_estimated_cost_usd
```

from all results belonging to a model.

It also continues to calculate:

```python
average_estimated_cost_usd
```

For example:

```text
Result A cost: 0.01
Result B cost: 0.03

Total:   0.04
Average: 0.02
```

This removes the previous behavior where model-level total cost silently remained at its default value of `0.0`.

## Explicit XFAIL and XPASS Summary Semantics

The report summary now includes:

```json
{
  "expected_failures": 0,
  "unexpected_passes": 0
}
```

`ModelSummary` also includes:

```python
unexpected_passes
```

This makes the status categories explicit rather than allowing `XFAIL` and `XPASS` results to contribute to `total` without appearing in summary counts.

## TestResult Cleanup

The duplicate:

```python
model: str
```

declaration in `TestResult` was removed.

This avoids carrying an accidental model-definition artifact into the future public report schema.

## Tests

Sprint 11.11A verifies:

* engine execution evidence remains attached to `EvaluationResult`
* engine execution evidence reaches `TestResult`
* engine execution evidence serializes into JSON
* model cost propagates from `ModelResponse` into `TestResult`
* model total estimated cost is calculated correctly
* model average estimated cost remains correct
* report summaries include expected failures
* report summaries include unexpected passes
* existing evaluation behavior remains backward compatible

Final regression result:

```text
185 passed in 10.83s
```

## Files Changed

Production:

```text
src/evaluation_pipeline.py
src/json_reporter.py
src/models.py
src/report_analytics.py
src/runner.py
```

Tests:

```text
tests/fakes.py
tests/test_json_reporter.py
tests/test_report_analytics.py
tests/test_test_runner.py
```

## Architectural Outcome

Before Sprint 11.11A:

```text
Runtime evidence
      |
      +-- metrics preserved
      |
      +-- engine execution evidence partially lost
      |
      +-- cost evidence partially lost
      |
      v
JSON report
```

After Sprint 11.11A:

```text
Runtime evidence
      |
      +-- deterministic assertion evidence
      +-- semantic metric evidence
      +-- engine execution evidence
      +-- cost evidence
      +-- explicit result classifications
      |
      v
TestResult
      |
      v
JSON evidence artifact
```

The serialized artifact is now stable enough to serve as the foundation for Report Schema v1.0.

## Definition of Done

Sprint 11.11A is complete when:

* engine execution outcomes survive runtime serialization
* engine failures remain structurally distinct from metric failures
* model cost propagates into test results
* total model cost is calculated
* expected failures are explicitly summarized
* unexpected passes are explicitly summarized
* duplicate `TestResult` model declarations are removed
* focused regression tests pass
* the complete test suite passes

All conditions were satisfied.

**Final verification:**

```text
185 passed in 10.83s
```

## Next Step

Sprint 11.11B will define the formal Report Schema v1.0 models and establish the machine-readable contract that future validators and evidence consumers will use.
