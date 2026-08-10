# Sprint 11.3 — Evaluation Profile Runtime Integration

## Status

**Complete**

## Objective

Integrate evaluation profiles into the existing AI Test Lab runtime so that a selected profile configures the evaluation pipeline used during test execution.

The primary architectural requirement was to avoid introducing a second execution path for profile-based evaluations.

Evaluation profiles must configure the existing runtime:

```text
CLI
  ↓
Evaluation Profile
  ↓
Pipeline Builder
  ↓
EvaluationPipeline
  ↓
MultiModelRunner
  ↓
TestRunner
  ↓
Evaluation Result
```

## Background

Sprint 11.1 introduced the evaluation profile catalog.

Sprint 11.2 added CLI profile selection, profile discovery, validation, and user-facing profile information.

Sprint 11.3 verifies and hardens the next layer: ensuring that the selected profile actually controls evaluation behavior at runtime.

During the initial architecture inspection, the existing runtime was found to already contain most of the required wiring.

The goal therefore became to verify the integration end-to-end and strengthen it with deterministic integration tests rather than introduce unnecessary new runtime components.

---

## Architecture Decision

AI Test Lab uses a **single evaluation execution architecture**.

Evaluation profiles do not execute evaluations themselves and do not require a separate profile-specific runner.

Instead, profiles are translated into configured runtime objects before test execution begins.

The runtime path is:

```text
CLI
  ↓
load_evaluation_profile()
  ↓
EvaluationProfile
  ↓
create_pipeline_from_profile()
  ↓
EvaluationPipeline
  ↓
MultiModelRunner
  ↓
TestRunner
  ↓
EvaluationPipeline.evaluate()
  ↓
EvaluationResult
  ↓
TestResult
  ↓
Reporters
```

This keeps configuration concerns separate from execution concerns.

---

## Runtime Responsibilities

### CLI

The CLI determines which evaluation profile should be loaded.

Example:

```powershell
python main.py --evaluation-profile fast-ci
```

The CLI does not execute individual evaluation engines.

### Evaluation Profile

`EvaluationProfile` represents evaluation policy and configuration.

A profile can define:

* enabled evaluation engines;
* enabled metrics;
* metric thresholds;
* quality-gate configuration;
* engine-specific options.

### Pipeline Builder

`create_pipeline_from_profile()` converts profile configuration into runtime objects.

The builder is responsible for:

* identifying enabled engines;
* creating external evaluation engines;
* selecting enabled metrics;
* resolving the evaluation threshold;
* resolving the verdict policy;
* constructing the configured `EvaluationPipeline`.

The assertion engine remains built into `EvaluationPipeline` and is not duplicated by the profile system.

### EvaluationPipeline

`EvaluationPipeline` performs evaluation orchestration.

Profile-derived configuration is stored as:

```text
external_engines
default_metrics
default_threshold
verdict_policy
```

When `TestRunner` calls the pipeline without explicitly specifying metrics or a threshold, the profile-derived defaults are used.

### MultiModelRunner

`MultiModelRunner` receives the already-configured `EvaluationPipeline`.

It does not need to understand evaluation profiles.

The same configured pipeline can therefore be used while executing the test suite against multiple models.

### TestRunner

`TestRunner` remains responsible for:

1. sending the prompt to the model client;
2. receiving the model response;
3. passing the response to the injected `EvaluationPipeline`;
4. classifying the resulting evaluation status;
5. producing a `TestResult`.

`TestRunner` does not know whether the pipeline configuration originated from YAML, CLI configuration, an API, or another future interface.

---

## Quality-Gate Behavior

Sprint 11.3 verifies that external evaluation results can participate in the final runtime verdict.

For an assertion-only pipeline:

```text
Built-in assertion PASS
        ↓
       PASS
```

For a quality-gated pipeline:

```text
Built-in assertion PASS
        +
External metric FAIL
        ↓
Quality gate FAIL
        ↓
Overall FAIL
```

This establishes the foundation for evaluation profiles that enforce semantic quality requirements in addition to deterministic assertions.

---

## Tests Added

A new runtime integration test module was added:

```text
tests/test_profile_runtime_integration.py
```

The tests verify the following behavior.

### Assertion-only runtime

Verifies that a pipeline using `VerdictPolicy.ASSERTION_ONLY` executes through `TestRunner` and produces a passing result when the built-in assertion succeeds.

### Quality gate affects runtime verdict

Verifies that:

```text
Built-in assertion = PASS
External metric = FAIL
Verdict policy = ALL_METRICS
```

produces:

```text
Overall result = FAIL
```

This proves that external evaluation results can affect the actual runtime verdict.

### Pipeline defaults reach external engines

Verifies that configured pipeline defaults such as:

```text
default_metrics
default_threshold
```

are propagated into the `EvaluationRequest` received by an external evaluation engine.

This is important because `TestRunner` does not need to manually pass profile configuration into each evaluation call.

### Profile configuration reaches runtime

Verifies the complete deterministic integration path:

```text
EvaluationProfile
        ↓
create_pipeline_from_profile()
        ↓
EvaluationPipeline
        ↓
TestRunner
        ↓
EvaluationResult
        ↓
TestResult
```

This test establishes that profile configuration is not merely loaded or validated—it reaches actual runtime execution.

---

## Test Strategy

Sprint 11.3 uses deterministic fake components for runtime integration testing.

The integration tests do not require:

* Ollama;
* a running LLM;
* external API access;
* live DeepEval judge execution.

This keeps the tests fast, reproducible, and suitable for CI/CD.

Dedicated integration tests remain responsible for validating external evaluation-engine implementations.

---

## Verification Results

### Runtime integration tests

```text
4 passed
```

### Targeted profile and evaluation pipeline tests

```text
13 passed
```

These tests covered:

```text
tests/test_profile_runtime_integration.py
tests/test_evaluation_profile_pipeline.py
tests/test_evaluation_pipeline.py
```

### Full regression suite

```text
151 passed in 42.75s
```

No regressions were detected.

---

## Key Architectural Outcome

Sprint 11.3 confirms that AI Test Lab does **not** need a separate profile execution architecture.

The existing runtime already supports the required dependency flow:

```text
Configuration
     ↓
Evaluation Profile
     ↓
Pipeline Builder
     ↓
Configured EvaluationPipeline
     ↓
Existing Runtime
```

This preserves separation of concerns and allows future execution interfaces to reuse the same runtime.

For example:

```text
CLI ──────────┐
Website ──────┤
REST API ─────┤
CI/CD ────────┤
Scheduler ────┤
              ↓
       Evaluation Profile
              ↓
       Pipeline Builder
              ↓
      EvaluationPipeline
              ↓
          TestRunner
```

The execution layer therefore remains independent of how an evaluation was requested.

---

## Current Limitation

The current evaluation pipeline supports one shared metric threshold per run.

If multiple enabled metrics specify different thresholds, profile construction rejects the configuration.

This limitation is intentionally preserved in Sprint 11.3 rather than expanding the pipeline API during runtime integration work.

Per-metric thresholds can be addressed in a future sprint if required.

---

## Future Consideration

External engine execution is currently triggered when evaluation metrics are selected.

This works for the current metric-oriented external evaluation architecture.

Future engines may include capabilities such as:

* security evaluation;
* policy validation;
* compliance rules;
* bias analysis;
* custom enterprise evaluators.

Such engines may not naturally operate through a metric list.

The engine-dispatch model may therefore need to evolve as the plugin architecture expands.

No change is required for Sprint 11.3.

---

## Acceptance Criteria

Sprint 11.3 is complete when:

* [x] A selected evaluation profile can produce a configured `EvaluationPipeline`.
* [x] The configured pipeline reaches `MultiModelRunner`.
* [x] The same pipeline reaches `TestRunner`.
* [x] `TestRunner` performs evaluation through the injected pipeline.
* [x] Profile-derived metrics reach external evaluation engines.
* [x] Profile-derived thresholds reach external evaluation engines.
* [x] Quality-gate policy can affect the final runtime verdict.
* [x] Assertion-only behavior remains supported.
* [x] No second profile-specific execution architecture is introduced.
* [x] Runtime integration tests are deterministic.
* [x] The targeted evaluation/profile test suite passes.
* [x] The complete regression suite passes.

---

## Sprint Result

Sprint 11.3 establishes the runtime bridge between AI Test Lab's evaluation-profile configuration system and its existing evaluation execution architecture.

Profiles are now supported as configuration for the existing pipeline rather than as a separate execution mechanism.

This creates a stable foundation for future evaluation profiles, additional evaluation engines, CI/CD quality gates, API-driven evaluations, and eventual website-driven evaluation execution.
