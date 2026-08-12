# Sprint 11.9 — Evidence Serialization & Reporting Contract

## Goal

Make AI Test Lab evaluation evidence portable and machine-consumable by defining and verifying a stable JSON reporting contract.

Sprint 11.9 builds directly on Sprint 11.8 provenance work. The objective is to ensure that evaluation evidence survives the transition from runtime objects into serialized reports without introducing a second serialization or reporting architecture.

## Architecture

The existing reporting path is preserved:

```text
Evaluation Engine
    → MetricResult
    → EvaluationResult / TestResult
    → Pydantic model_dump(mode="json")
    → JsonReporter
    → JSON evidence report
```

No separate evidence serializer was introduced.

The existing Pydantic models remain the source of truth for serialized evaluation evidence.

## Implemented

### 1. Evaluation evidence serialization verification

Extended JSON reporter testing to verify that `MetricResult` evidence introduced in Sprint 11.8 survives serialization.

The JSON contract now explicitly verifies preservation of:

* `engine`
* `metric_name`
* `score`
* `threshold`
* `passed`
* `reason`
* `runtime_options`
* `profile_name`
* `profile_version`
* `evaluator_model`

Example serialized metric evidence:

```json
{
  "engine": "builtin",
  "metric_name": "contains",
  "score": 1.0,
  "threshold": 1.0,
  "passed": true,
  "reason": "The response contains the expected text.",
  "runtime_options": {
    "include_reason": true
  },
  "profile_name": "fast-ci",
  "profile_version": "1.0",
  "evaluator_model": "test-judge"
}
```

### 2. Report schema version

Added an explicit top-level schema version to JSON reports:

```json
{
  "schema_version": "1.0"
}
```

The schema version provides consumers with an explicit identifier for the structure of the AI Test Lab evidence contract.

Future consumers may include:

* AI Test Lab website
* CI/CD quality gates
* dashboards
* report-processing tools
* evaluation history systems
* governance and compliance components

Consumers can use `schema_version` to determine which report structure they are processing.

## Design Decision

Sprint 11.9 intentionally does **not** introduce a new serializer.

`JsonReporter` already serializes `TestResult` using:

```python
result.model_dump(mode="json")
```

Because `TestResult.evaluation_results` contains `MetricResult` objects, Pydantic recursively serializes the complete metric evidence.

Testing confirmed that the Sprint 11.8 provenance fields are preserved automatically.

The architecture therefore remains:

```text
Runtime evidence
      ↓
MetricResult
      ↓
TestResult
      ↓
Pydantic serialization
      ↓
Versioned JSON report
```

This avoids duplicated serialization logic and keeps the runtime model and reporting contract aligned.

## Compatibility

The existing JSON report structure remains intact.

The new `schema_version` field is additive.

Existing report fields such as:

* `generated_at`
* `models`
* `summary`
* `highlights`
* `model_comparison`
* `results`

continue to behave as before.

Existing metric fields are also unchanged.

Sprint 11.9 therefore extends the reporting contract without creating a parallel reporting path or changing evaluation execution behavior.

## Verification

Focused JSON reporter testing confirmed that:

* reports are successfully generated;
* the report declares `schema_version` as `1.0`;
* metric scores and thresholds survive serialization;
* pass/fail verdicts survive serialization;
* evaluation reasons survive serialization;
* runtime metric options survive serialization;
* profile name and version survive serialization;
* evaluator-model provenance survives serialization.

Full repository verification:

```text
179 passed in 48.45s
```

## Result

Sprint 11.9 establishes a versioned evidence boundary between the AI Test Lab evaluation runtime and downstream consumers.

Sprint 11.8 made evaluation results traceable inside the framework.

Sprint 11.9 makes that evidence safely consumable outside the runtime.
