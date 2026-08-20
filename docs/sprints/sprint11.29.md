\# Sprint 11.29 — Public Report Contract Documentation



\## Objective



Sprint 11.29 makes the AI Test Lab Public Report v1.0 contract explicit, understandable, and discoverable for external consumers.



Previous Sprint 11 work established the technical enforcement boundary. Sprint 11.29 documents that boundary without expanding the public API or exposing proprietary implementation details.



\## Problem



AI Test Lab already enforced Public Report v1.0 through:



\* versioned public Pydantic models

\* JSON Schema validation

\* rejection of unknown fields

\* nested exposure protection

\* runtime option filtering

\* sanitized engine errors

\* compatibility enforcement

\* consumer validation

\* release-readiness validation



However, the human-readable definition of the public contract was distributed across source code, schemas, tests, and sprint documentation.



An external consumer should not need to inspect internal Python source to understand the supported report format.



\## Solution



Sprint 11.29 introduces permanent consumer documentation:



```text

docs/public-report-v1.0.md

```



The document explains:



\* schema versioning

\* root report structure

\* summary fields

\* model comparison fields

\* individual test results

\* metric evaluation results

\* engine execution results

\* approved runtime options

\* performance measurements

\* estimated cost data

\* compatibility expectations

\* release-readiness requirements

\* the public/private IP boundary



\## Public Contract Principle



The Public Report is an explicit external DTO contract.



It is not a direct serialization of internal evaluation models.



```text

Internal Evaluation

&#x20;       ↓

Public DTO Mapping

&#x20;       ↓

Public Report Contract

&#x20;       ↓

Contract Validation

&#x20;       ↓

Release Validation

&#x20;       ↓

External Consumer

```



\## Strict Allow-List



Public schemas continue to operate as allow-lists.



Fields explicitly included in the public schema are permitted.



Unknown fields are rejected.



This applies at both root and nested levels.



\## IP Protection Boundary



The documentation explicitly identifies categories that are not part of the public contract.



These include:



```text

internal scoring algorithms

proprietary weighting logic

private policy identifiers

governance implementation

internal evidence traces

orchestration internals

credentials

filesystem paths

private diagnostics

unapproved runtime configuration

```



The sprint documents the boundary without describing how proprietary systems work internally.



\## Version Compatibility



Public Report v1.0 uses:



```text

schema\_version = "1.0"

```



Consumers are expected to inspect this version.



Unsupported versions must be rejected instead of being silently interpreted using another schema.



Future incompatible public contract changes should therefore use explicit schema evolution.



\## Contract Authority



The human-readable documentation explains the contract.



The executable contract remains defined by:



```text

schemas/report-v1.0.schema.json

src/report\_schema.py

src/report\_contract\_validator.py

```



The consumer and release boundary are enforced through:



```text

src/report\_consumer.py

src/report\_release\_validator.py

```



\## Production Behavior



Sprint 11.29 intentionally does not introduce new evaluation or reporting behavior.



The existing contract has already been hardened in previous sprints.



The goal of this sprint is contract clarity and discoverability rather than additional runtime complexity.



\## Definition of Done



Sprint 11.29 is complete when:



\* Public Report v1.0 has permanent human-readable documentation

\* root-level fields are documented

\* nested report structures are documented

\* public metric fields are documented

\* public runtime options are documented

\* compatibility expectations are documented

\* release-readiness expectations are documented

\* the public/private IP boundary is documented

\* proprietary implementation logic remains undisclosed

\* the existing regression suite remains green



\## Result



AI Test Lab now has both sides of a mature public contract:



```text

Machine-readable contract

&#x20;       +

Human-readable contract documentation

```



External consumers can understand what Public Report v1.0 guarantees without depending on AI Test Lab internal implementation details.



