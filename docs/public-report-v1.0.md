\# AI Test Lab Public Report v1.0



\## Purpose



The AI Test Lab Public Report is the stable external reporting contract produced for consumers, integrations, dashboards, automation, and downstream tooling.



The public report is intentionally separated from AI Test Lab internal evaluation models.



Only fields explicitly defined by the public contract are permitted. Unknown, internal, proprietary, or implementation-specific fields are rejected.



\---



\## Schema Version



Public Report v1.0 declares:



```json

{

&#x20; "schema\_version": "1.0"

}

```



The current runtime supports Public Report schema version `1.0`.



Consumers should inspect the declared `schema\_version` before processing a report. Reports declaring unsupported versions are rejected.



\---



\## Root Report Structure



A Public Report v1.0 contains:



```text

ReportV1

│

├── schema\_version

├── generated\_at

├── models

├── summary

├── highlights

├── model\_comparison

└── results

```



\### `schema\_version`



Identifies the version of the public report contract. For Public Report v1.0, the value is `"1.0"`.



\### `generated\_at`



Timestamp representing when the report was generated.



\### `models`



List of models represented in the evaluation report.



\### `summary`



Aggregated evaluation outcome information.



\### `highlights`



High-level model highlights.



\### `model\_comparison`



Per-model aggregate statistics.



\### `results`



Individual test and evaluation results.



\---



\## Summary



The `summary` object contains:



```text

passed

failed

expected\_failures

unexpected\_passes

errors

total

pass\_rate\_percent

total\_estimated\_cost\_usd

```



`passed` and `failed` describe the reported test outcomes.



`expected\_failures` identifies failures that were explicitly expected.



`unexpected\_passes` identifies tests that passed despite being expected to fail.



`errors` records evaluation executions that resulted in errors.



`total` represents the total number of reported test executions.



`pass\_rate\_percent` is constrained to a value between `0.0` and `100.0`.



`total\_estimated\_cost\_usd` represents the total estimated evaluation cost and cannot be negative.



\---



\## Highlights



The `highlights` object contains:



```text

highest\_scoring\_model

fastest\_model

```



Both values may be absent when a meaningful highlight cannot be determined.



`highest\_scoring\_model` identifies the model reported as having the highest score.



`fastest\_model` identifies the model reported as the fastest.



\---



\## Model Comparison



Each entry in `model\_comparison` describes aggregate results for a provider/model pair.



Public fields include:



```text

provider

model

total\_estimated\_cost\_usd

average\_estimated\_cost\_usd

passed

expected\_failures

unexpected\_failures

unexpected\_passes

errors

total

pass\_rate\_percent

average\_response\_time\_seconds

average\_prompt\_latency\_seconds

average\_generation\_latency\_seconds

average\_model\_load\_seconds

average\_prompt\_tokens

average\_output\_tokens

average\_prompt\_tokens\_per\_second

average\_generation\_tokens\_per\_second

```



These fields provide consumer-facing performance, outcome, usage, and cost information.



They do not expose internal algorithms used to calculate evaluation decisions.



\---



\## Test Results



Each item in `results` represents a public test result.



Public fields include:



```text

test\_id

name

category

prompt

provider

model

estimated\_cost\_usd

actual\_response

passed

status

expected\_to\_fail

assertion\_type

expected

reason

evaluation\_results

engine\_results

response\_time\_seconds

prompt\_tokens

output\_tokens

prompt\_latency\_seconds

generation\_latency\_seconds

model\_load\_seconds

prompt\_tokens\_per\_second

generation\_tokens\_per\_second

```



\### Test Identity



`test\_id` is the identifier associated with the reported test.



`name` is the human-readable test name.



`category` identifies the category associated with the test.



\### Model Interaction



`prompt` is the prompt submitted for the reported test.



`provider` identifies the model provider.



`model` identifies the evaluated model.



`actual\_response` contains the response produced by the model.



\### Evaluation Outcome



`passed` contains the boolean test verdict.



`status` contains the public result status.



`expected\_to\_fail` indicates whether failure was expected.



`assertion\_type` identifies the public assertion type.



`expected` contains the expected value associated with the assertion.



`reason` contains the public explanation associated with the result.



\---



\## Metric Evaluation Results



Each item in `evaluation\_results` contains:



```text

engine

metric\_name

score

threshold

passed

reason

runtime\_options

profile\_name

profile\_version

evaluator\_model

```



`engine` identifies the public evaluation engine.



`metric\_name` identifies the reported metric.



`score` contains the metric score.



`threshold` contains the threshold used for the metric verdict.



`passed` indicates whether the metric satisfied its threshold.



`reason` may contain a public explanation associated with the metric result.



`profile\_name` and `profile\_version` may identify the evaluation profile.



`evaluator\_model` may identify the public evaluator model.



\---



\## Runtime Options



Public Report v1.0 exposes only explicitly approved runtime options.



Currently supported:



```text

include\_reason

```



Internal runtime settings are not part of the public contract.



For example:



```text

internal\_weighting\_algorithm

internal\_policy\_id

internal\_scoring\_strategy

```



are not permitted public fields.



\---



\## Engine Execution Results



Each item in `engine\_results` contains:



```text

engine

succeeded

error

```



`engine` identifies the evaluation engine.



`succeeded` indicates whether execution completed successfully.



`error` may contain a sanitized public error message.



Internal filesystem paths, credentials, implementation details, and proprietary diagnostic information must not be exposed through the public error field.



\---



\## Performance Metrics



Individual results may contain:



```text

response\_time\_seconds

prompt\_tokens

output\_tokens

prompt\_latency\_seconds

generation\_latency\_seconds

model\_load\_seconds

prompt\_tokens\_per\_second

generation\_tokens\_per\_second

```



These values provide consumer-facing execution and performance measurements.



Timing values and token counts cannot be negative.



\---



\## Cost Information



The public report contains estimated cost information at individual and aggregate levels, including:



```text

estimated\_cost\_usd

total\_estimated\_cost\_usd

average\_estimated\_cost\_usd

```



Public cost values must be non-negative.



These values are estimates and should not be treated as authoritative provider billing records.



\---



\## Strict Public Contract



Public report schemas operate as allow-lists.



```text

Defined public field

&#x20;       │

&#x20;       ▼

&#x20;     ALLOW



Unknown field

&#x20;       │

&#x20;       ▼

&#x20;     REJECT

```



This rule applies to root-level and nested objects.



A field does not become public merely because it exists inside an AI Test Lab internal model.



\---



\## IP Protection Boundary



The public report is not a serialization of AI Test Lab internal models.



The controlled path is:



```text

Internal Evaluation Models

&#x20;         │

&#x20;         ▼

Public DTO Mapping

&#x20;         │

&#x20;         ▼

Public Report Schema

&#x20;         │

&#x20;         ▼

Contract Validation

&#x20;         │

&#x20;         ▼

Consumer Validation

&#x20;         │

&#x20;         ▼

Release Readiness Gate

&#x20;         │

&#x20;         ▼

External Consumer

```



The following categories are not public contract data unless deliberately introduced through a future public contract:



```text

internal scoring algorithms

proprietary weighting logic

private policy identifiers

governance implementation details

internal evidence traces

orchestration internals

credentials

API keys

filesystem paths

private engine diagnostics

unapproved runtime configuration

```



\---



\## Compatibility



Consumers must inspect `schema\_version`.



A runtime that does not support the declared schema version must reject the report rather than attempting to interpret it as another version.



Public Report v1.0 therefore establishes an explicit compatibility boundary.



Future incompatible contract changes should occur through deliberate schema-version evolution rather than silent mutation of v1.0.



\---



\## Release Readiness



Before external release, a report must pass the AI Test Lab release-readiness validation boundary.



A report is not release ready if it contains:



```text

unsupported schema versions

malformed JSON

unknown public fields

unexpected nested fields

private runtime options

invalid contract data

```



Validation fails closed.



If a report cannot be proven valid against the public contract, it must not be released.



\---



\## Contract Authority



The machine-readable JSON Schema and runtime public models remain the authoritative executable definitions of Public Report v1.0.



This document provides the human-readable explanation of that contract.



Relevant implementation boundaries are:



```text

schemas/report-v1.0.schema.json

src/report\_schema.py

src/report\_contract\_validator.py

src/report\_consumer.py

src/report\_release\_validator.py

```



Public consumers should depend on the published contract rather than AI Test Lab internal implementation models.



