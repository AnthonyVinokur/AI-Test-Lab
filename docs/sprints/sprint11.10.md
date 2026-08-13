# Sprint 11.10 — Quality-Gate Runtime Semantics

## Status

**Completed**

Sprint 11.10 completes the runtime semantics for evaluation-profile quality gates.

The sprint closes the gap between quality-gate configuration and the final runtime verdict by giving `fail_on_engine_error` and `require_all_engines` explicit runtime meaning.

Final verification:

```text
185 passed in 12.12s
```

Implementation commit:

```text
b4e8659 feat: enforce quality-gate runtime semantics
```

---

## Goal

The goal of Sprint 11.10 was to make the complete `QualityGateConfig` contract authoritative at runtime.

Before this sprint, evaluation profiles already supported:

```yaml
quality_gate:
  enabled: true
  minimum_score: 0.70
  fail_on_engine_error: true
  require_all_engines: false
```

However, only part of this configuration affected runtime behavior.

The existing runtime already supported:

* `enabled`
* `minimum_score`

The following settings existed in the configuration model but did not yet participate in final verdict resolution:

* `fail_on_engine_error`
* `require_all_engines`

Sprint 11.10 completes that contract.

---

## Problem

Before Sprint 11.10, the runtime quality-gate path was effectively:

```text
EvaluationProfile
       |
       v
QualityGateConfig
       |
       +-- enabled
       |      |
       |      v
       |  VerdictPolicy
       |
       +-- minimum_score
              |
              v
       metric threshold
              |
              v
       EvaluationPipeline
              |
              v
       final verdict
```

The profile could declare:

```text
fail_on_engine_error
require_all_engines
```

but these values had no runtime authority.

A second problem existed around external evaluation failures.

External engines such as DeepEval intentionally raise exceptions when evaluation cannot be completed. Examples include:

* evaluator/judge model unavailable
* metric execution failure
* missing metric score
* external evaluation runtime failure

These exceptions propagated out of `EvaluationPipeline`.

That meant the pipeline could not distinguish between:

```text
Metric failure
score < threshold
```

and:

```text
Engine execution failure
evaluation could not be completed
```

This distinction is essential for reliable quality-gate behavior and future governance evidence.

---

## Design Principle

Sprint 11.10 preserves the existing single evaluation architecture.

No second quality-gate pipeline was introduced.

The runtime remains:

```text
Evaluation Profile
       |
       v
Pipeline Builder
       |
       v
EvaluationPipeline
       |
       +-- Built-in assertion
       |
       +-- External evaluation engines
       |
       +-- Metric results
       |
       +-- Engine execution outcomes
       |
       v
Verdict Resolution
       |
       v
EvaluationResult
```

Quality-gate semantics remain part of the existing `EvaluationPipeline`.

---

## Engine Execution Evidence

Sprint 11.10 introduces an engine-level execution result.

```python
@dataclass(frozen=True, slots=True)
class EngineExecutionResult:
    """Outcome of running one external evaluation engine."""

    engine: str
    succeeded: bool
    error: str | None = None
```

This deliberately remains separate from `MetricResult`.

A metric failure means that evaluation successfully occurred but the evaluated response did not satisfy the metric threshold.

For example:

```text
engine: deepeval
metric: faithfulness
score: 0.63
threshold: 0.80
passed: false
```

This is a valid evaluation result.

An engine execution failure means that evaluation could not be completed.

For example:

```text
engine: deepeval
succeeded: false
error: judge unavailable
```

No artificial metric score is generated for an engine failure.

In particular, the runtime does not convert an engine failure into a synthetic result such as:

```text
score = 0.0
passed = false
```

because that would incorrectly imply that the response was successfully evaluated and received a zero score.

---

## External Engine Error Normalization

External evaluation engines retain their existing contract.

An external engine still returns:

```python
list[MetricResult]
```

and may raise an exception when execution fails.

The plugin protocol was not changed.

Instead, `EvaluationPipeline` now owns the integration boundary.

Conceptually:

```text
ExternalEvaluationEngine
       |
       +-- success
       |      |
       |      v
       |  MetricResult[]
       |
       +-- exception
              |
              v
       EngineExecutionResult
              |
              v
       Quality-Gate Resolution
```

The external engine remains responsible for determining why execution failed.

The pipeline is responsible for determining what that failure means to the final evaluation verdict.

---

## Runtime Quality-Gate Semantics

Sprint 11.10 establishes the following behavior.

### Quality Gate Disabled

When the profile resolves to:

```text
VerdictPolicy.ASSERTION_ONLY
```

the built-in assertion determines the final verdict.

External evaluation evidence does not override the assertion verdict.

This preserves the existing assertion-only behavior.

---

### Metric Failure

When the quality gate is enabled, an external metric that evaluates successfully but fails its threshold causes the quality gate to fail.

Example:

```text
Built-in assertion     PASS
Answer relevancy       PASS
Faithfulness           FAIL
--------------------------------
Final verdict          FAIL
```

Metric failure remains distinct from engine failure.

---

### `fail_on_engine_error = true`

When an external evaluation engine fails to execute and:

```yaml
fail_on_engine_error: true
```

the quality gate fails.

Example:

```text
Built-in assertion     PASS
DeepEval               ERROR
--------------------------------
Final verdict          FAIL
```

The engine error is preserved as runtime evidence and incorporated into the failure reason.

---

### `fail_on_engine_error = false`

When:

```yaml
fail_on_engine_error: false
require_all_engines: false
```

an engine execution failure does not automatically fail the quality gate.

The failure remains recorded as engine execution evidence, but the policy permits the remaining successful evidence to determine acceptance.

---

### `require_all_engines = true`

When:

```yaml
require_all_engines: true
```

every configured external evaluation engine participating in the evaluation must complete successfully.

Example:

```text
Built-in assertion     PASS
Engine A               PASS
Engine B               ERROR
--------------------------------
Final verdict          FAIL
```

This remains true even when:

```yaml
fail_on_engine_error: false
```

because the two settings express different policies.

`fail_on_engine_error` determines whether an engine error itself is fatal.

`require_all_engines` determines whether successful participation from every configured external engine is required.

---

## Policy Interaction

The resulting runtime contract is:

| Situation                 | `fail_on_engine_error` | `require_all_engines` | Result                       |
| ------------------------- | ---------------------: | --------------------: | ---------------------------- |
| All required metrics pass |                    any |                   any | PASS                         |
| Metric score fails        |                    any |                   any | FAIL                         |
| Engine error              |                 `true` |               `false` | FAIL                         |
| Engine error              |                `false` |               `false` | Does not automatically fail  |
| Engine error              |                 `true` |                `true` | FAIL                         |
| Engine error              |                `false` |                `true` | FAIL                         |
| Gate disabled             |                    any |                   any | Assertion determines verdict |

This makes the two engine-related policies orthogonal rather than redundant.

---

## Profile-to-Runtime Propagation

`create_pipeline_from_profile()` now propagates the complete quality-gate configuration into `EvaluationPipeline`.

The runtime mapping is:

```text
quality_gate.enabled
        |
        v
VerdictPolicy

quality_gate.minimum_score
        |
        v
default_threshold

quality_gate.fail_on_engine_error
        |
        v
EvaluationPipeline.fail_on_engine_error

quality_gate.require_all_engines
        |
        v
EvaluationPipeline.require_all_engines
```

This closes the configuration/runtime gap.

A quality-gate setting declared in an evaluation profile now has corresponding runtime semantics.

---

## Verdict Resolution

The final verdict remains centralized in `EvaluationPipeline`.

The decision flow is conceptually:

```text
Built-in assertion failed?
        |
        +-- YES --> FAIL
        |
        NO
        |
        v
Assertion-only policy?
        |
        +-- YES --> assertion verdict
        |
        NO
        |
        v
External metric failed?
        |
        +-- YES --> FAIL
        |
        NO
        |
        v
External engine failed?
        |
        +-- YES
        |     |
        |     v
        |  fail_on_engine_error?
        |     |
        |     +-- YES --> FAIL
        |
        |  require_all_engines?
        |     |
        |     +-- YES --> FAIL
        |
        v
       PASS
```

This keeps final acceptance deterministic and centralized.

---

## Tests

Sprint 11.10 adds:

```text
tests/test_quality_gate_runtime.py
```

The dedicated runtime tests verify:

* engine errors fail the gate when `fail_on_engine_error=True`
* engine errors can be tolerated when policy permits
* required engine failures fail when `require_all_engines=True`
* metric failures remain metric failures rather than engine errors
* assertion-only mode preserves the built-in assertion verdict
* successful engines and passing metrics produce a passing verdict

The initial test run intentionally exposed the missing runtime behavior:

```text
4 failed, 2 passed
```

After engine execution outcomes were introduced, the remaining failures exposed missing policy state on `EvaluationPipeline`:

```text
3 failed, 3 passed
```

After completing the runtime policy implementation:

```text
6 passed in 0.06s
```

The full regression suite then completed successfully:

```text
185 passed in 12.12s
```

---

## Files Changed

Sprint 11.10 modifies:

```text
src/evaluation_config/pipeline_builder.py
src/evaluation_models.py
src/evaluation_pipeline.py
```

and adds:

```text
tests/test_quality_gate_runtime.py
```

---

## Architectural Outcome

Before Sprint 11.10:

```text
Profile configuration
       |
       v
metric evaluation
       |
       v
metric pass/fail
       |
       v
partial quality-gate semantics
```

After Sprint 11.10:

```text
Profile configuration
       |
       v
EvaluationPipeline
       |
       +-- deterministic assertion evidence
       +-- semantic metric evidence
       +-- engine execution evidence
       |
       v
policy-aware quality gate
       |
       v
deterministic final verdict
```

AI Test Lab can now distinguish between:

```text
"The model response failed evaluation."
```

and:

```text
"The evaluation system could not complete evaluation."
```

The quality-gate policy determines how each condition affects acceptance.

This distinction is important for CI/CD quality gates, audit evidence, operational diagnosis, and future enterprise governance reporting.

---

## Definition of Done

Sprint 11.10 is complete when:

* quality-gate enable/disable behavior is preserved
* the configured minimum metric score reaches runtime
* `fail_on_engine_error` reaches runtime
* `require_all_engines` reaches runtime
* external engine failures are represented independently from metric failures
* engine errors no longer have to be represented as artificial metric scores
* quality-gate verdict resolution handles engine execution failures deterministically
* assertion-only behavior remains backward compatible
* existing external evaluation engine contracts remain unchanged
* the complete regression suite passes

All conditions were satisfied.

**Final verification:**

```text
185 passed in 12.12s
```

**Implementation commit:**

```text
b4e8659 feat: enforce quality-gate runtime semantics
```
