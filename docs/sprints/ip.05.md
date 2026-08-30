# IP.05 — Private Capability & Consumer Boundary

## Status

**Complete.**

IP.05 is the final planned foundational IP-protection sprint for AI Test Lab.

It establishes a durable separation between the public AI Test Lab framework, the private/proprietary implementation layer, and external consumers such as the website, APIs, SDKs, the controlled reference application, and future enterprise integrations.

IP.01–IP.04 established repository leakage protection, explicit public contracts, and controlled serialization/export. IP.05 completes that foundation by defining **where proprietary implementation may live and which dependency directions are permitted**.

---

## Objective

Create and enforce a two-repository architecture in which proprietary AI Test Lab capabilities live outside the public repository and cannot become dependencies of public-facing code.

Allowed:

```text
AI-Test-Lab-Private
        │
        │ consumes approved public contracts
        ▼
AI-Test-Lab
```

Forbidden:

```text
AI-Test-Lab
        │
        X
        ▼
AI-Test-Lab-Private
```

External consumers must remain on the public-contract side of the boundary:

```text
Website / API / SDK / Reference App / Integrations
                         │
                         ▼
                 Public AI Test Lab contracts
                         │
                         X
                         ▼
                  Private implementation
```

---

## Why This Sprint Exists

The earlier IP sprints answered three important questions:

```text
What protected content must not leak into the repository?
What data is allowed to become public?
How is public data allowed to leave?
```

One architectural question remained:

> **Where should future proprietary implementation live?**

Without a separate private repository, commercially valuable capabilities could eventually drift into the public codebase through convenience or incremental development.

Examples include:

- advanced scoring and risk aggregation;
- evidence intelligence;
- governance decision logic;
- compliance interpretation and policy mapping;
- advanced adversarial/security intelligence;
- enterprise policy evaluation;
- commercial orchestration;
- optimization and recommendation logic;
- customer-specific proprietary policy.

IP.05 closes that gap before those capabilities become substantial.

The goal is **not** to copy existing public AI Test Lab code into a private repository. The goal is to establish a permanent placement and dependency rule before proprietary implementation grows.

---

## Repository Model

### Public repository

```text
AnthonyVinokur/AI-Test-Lab
```

Appropriate public content includes:

- public DTOs and schemas;
- stable public interfaces;
- CLI contracts;
- dataset formats;
- basic deterministic evaluation;
- public plugin interfaces;
- public report schemas;
- compatibility contracts;
- approved regression interfaces;
- public serialization gateways;
- safe documentation and examples.

### Private repository

```text
AnthonyVinokur/AI-Test-Lab-Private
```

Appropriate proprietary content may include:

- advanced scoring algorithms;
- risk aggregation;
- evidence intelligence;
- governance decision engines;
- compliance engines;
- enterprise policy implementation;
- proprietary security intelligence;
- commercial orchestration;
- optimization intelligence;
- customer-specific proprietary rules.

Capabilities are added only when they actually exist. The private repository is not a duplicate of the public framework.

---

## Private Repository Foundation

The private repository was created before proprietary commercial logic was introduced.

Initial boundary commit:

```text
d5d078d chore: establish private AI Test Lab boundary
```

Foundation files:

```text
.gitattributes
.gitignore
PROPRIETARY.md
README.md
docs/ARCHITECTURE_BOUNDARY.md
src/aitestlab_private/__init__.py
tests/__init__.py
```

The repository has independent Git history, its own virtual environment, and its own Python package.

Current IP.05 working branch:

```text
ip-05-private-capability-boundary
```

Private package checkpoint:

```text
8cd8482 chore: initialize private package foundation
```

Private package verification:

```text
1 passed in 0.01s
```

---

## Core Dependency Invariant

The permanent rule is:

```text
PRIVATE → approved PUBLIC contracts    ALLOWED
PUBLIC  → PRIVATE implementation       FORBIDDEN
```

### Why private may depend on public

The public repository defines stable interoperability contracts that can be shared with:

- framework users;
- website consumers;
- SDKs;
- external integrations;
- private commercial extensions.

That makes the public layer the stable boundary.

### Why public may not depend on private

A reverse dependency would:

- make the public framework incomplete without private code;
- put proprietary implementation into the public runtime dependency graph;
- blur packaging and deployment boundaries;
- couple public development to private repository access;
- make commercial ownership ambiguous;
- create opportunities for indirect leakage through consumers.

The public project must remain independently usable.

---

## Consumer Boundary

External consumers may depend only on approved public contracts.

This includes:

```text
ai-test-lab-website
Aquagear-Reference-App
future HTTP APIs
SDKs
CLI machine-readable consumers
downloadable report consumers
webhooks
enterprise integrations
external evidence systems
```

The intended architecture is:

```text
                  AI-Test-Lab-Private
                  proprietary logic
                         │
                         │ approved contracts
                         ▼
                     AI-Test-Lab
                  public framework
                         │
             ┌───────────┼───────────┐
             ▼           ▼           ▼
          Website       API         SDK
                                      │
                                      ▼
                               Reference App
```

Consumers may receive approved public outputs. They must not import private modules or duplicate proprietary logic.

---

## Capability Classification

Before implementing a commercially significant capability, classify it as:

```text
PUBLIC
INTERNAL
PROPRIETARY
```

### PUBLIC

Intentionally part of the public contract or framework surface.

Examples:

- DTOs;
- schemas;
- stable interfaces;
- public CLI behavior;
- report formats;
- compatibility contracts.

### INTERNAL

Implementation details that are not public contracts but are still appropriate inside the public framework repository.

Examples may include:

- adapters;
- persistence helpers;
- internal validation glue;
- implementation-only utilities that are not commercially differentiating.

`INTERNAL` does not automatically mean `PROPRIETARY`.

### PROPRIETARY

Commercially valuable implementation or product differentiation.

Examples:

- advanced scoring;
- risk synthesis;
- evidence prioritization;
- governance reasoning;
- compliance interpretation;
- advanced security heuristics;
- commercial orchestration;
- optimization intelligence;
- customer-specific policy engines.

PROPRIETARY implementation belongs in `AI-Test-Lab-Private` by default.

---

## Public Contract Requirement

IP.05 does not weaken the public DTO/export controls created in IP.03 and IP.04.

Any proprietary result that becomes outward-facing must still cross an approved public transformation:

```text
Private/proprietary implementation
             │
             ▼
explicit public transformation
             │
             ▼
PublicContractModel
             │
             ▼
serialize_public_contract()
             │
             ▼
external consumer
```

The private repository must not introduce a second informal external contract.

---

## Public Repository Enforcement

The public repository mechanically rejects private-package imports.

Forbidden examples:

```python
import aitestlab_private
```

```python
from aitestlab_private import scoring
```

```python
from aitestlab_private.governance import PolicyEngine
```

The check should be syntax-aware so that harmless strings and comments do not fail:

```python
message = "aitestlab_private"
# import aitestlab_private
```

The objective is dependency-boundary enforcement, not keyword censorship.

---

### Public boundary verification

```text
Private dependency boundary tests:     11 passed in 0.17s
Combined IP boundary tests:            37 passed in 0.46s
Full public regression suite:          702 passed in 17.00s

Repository boundary scanner:           PASS
Public export boundary scanner:        PASS
Private dependency boundary scanner:   PASS
git diff --check:                       PASS
```

## Private Repository Enforcement

The private repository must:

- remain independently versioned;
- maintain a dedicated virtual environment;
- maintain its own tests;
- keep secrets and customer data out of Git;
- avoid copying public implementation unnecessarily;
- use approved public contracts rather than internal public-repo implementation details;
- avoid exposing proprietary modules through public consumer layers.

As the private repository grows, additional automated dependency checks can be introduced.

---

## Repository Privacy Is Not Secret Management

The private repository exists to protect implementation IP.

It is not a vault for:

```text
credentials
API keys
passwords
private keys
customer datasets
regulated data
production secrets
unreviewed sensitive exports
```

Those remain subject to separate secret-management and data-handling practices.

---

## Backup and Durability

The private repository also closes an important backup gap: proprietary code should not exist only on one workstation.

The intended durability model is:

```text
working copy
    │
    ├── local development machine
    ├── private GitHub repository
    └── encrypted backup for irreplaceable local-only assets
```

Data intentionally excluded from Git still requires separate backup policy.

---

## Non-Goals

IP.05 does not attempt to solve:

- license enforcement;
- customer authentication;
- API authorization;
- SaaS tenancy isolation;
- production deployment security;
- employee/contractor access governance;
- customer data retention;
- anti-reverse-engineering;
- legal contract management;
- trademark or patent strategy;
- enterprise secret management;
- generalized taint analysis.

Its responsibility is deliberately narrow:

> **Establish and enforce the public/private implementation boundary.**

---

## Relationship to Earlier IP Sprints

```text
IP.01 / IP.02
Repository leakage protection
        ↓
IP.03
Public contract exposure control
        ↓
IP.04
Public export boundary enforcement
        ↓
IP.05
Private capability & consumer boundary
```

Together, the foundational IP program answers:

```text
What must not enter or leak from repositories?
What data is allowed to become public?
How may public data be serialized/exported?
Where may proprietary implementation live?
Which layers are allowed to depend on which other layers?
```

---

## CI Strategy

The public repository enforces:

```text
Repository boundary check
        ↓
Public export boundary check
        ↓
Private dependency boundary check
        ↓
Python tests
```

The private repository maintains independent CI appropriate to proprietary development:

```text
Checkout
   ↓
Repository/security policy checks
   ↓
Dependency-boundary checks
   ↓
Private package tests
```

---

### Private repository closure verification

```text
Private CI workflow:                    established
Private repository main:                synchronized with origin/main
Private test suite:                     1 passed in 0.01s
Private git diff --check:               PASS
Private working tree:                   clean
Private feature branches:               removed/pruned
Private main merge checkpoint:          2c681db
```

## Pull-Request Review Policy

Future PRs should answer:

```text
Is this capability PUBLIC, INTERNAL, or PROPRIETARY?
Is proprietary implementation entering the public repo?
Does public code import or require aitestlab_private?
Does private code rely only on approved public contracts?
Does an external consumer bypass the public-contract boundary?
Does the change expose commercially valuable implementation details?
```

Classification must happen before exposure.

---

## Compatibility

IP.05 is intended to preserve existing public AI Test Lab behavior.

It should not intentionally change:

- evaluation semantics;
- dataset semantics;
- regression semantics;
- report schema compatibility;
- CLI process contracts;
- public DTO versions;
- public serialization behavior;
- website public-data consumption.

The principal change is architectural placement and dependency control.

---

## Current Verification Evidence

Private repository foundation:

```text
d5d078d chore: establish private AI Test Lab boundary
```

Private package foundation:

```text
8cd8482 chore: initialize private package foundation
```

Current branch:

```text
ip-05-private-dependency-boundary
```

Private package verification:

```text
1 passed in 0.01s
```

No speculative proprietary scoring, governance, compliance, evidence, or orchestration implementation has been added.

---

## Definition of Done

IP.05 is complete when:

- [x] A separate private repository exists.
- [x] The repository is configured as private.
- [x] The private repository has independent Git history.
- [x] The private repository has a dedicated Python package.
- [x] The private repository has a dedicated test foundation.
- [x] Public/private architectural policy is documented.
- [x] A proprietary software notice exists.
- [x] Secret-prone/local runtime files are excluded.
- [x] Cross-platform text normalization is configured.
- [x] Private package importability is verified.
- [x] The public repository mechanically rejects imports of `aitestlab_private`.
- [x] Boundary enforcement has positive and negative tests.
- [x] Public repository CI runs the private-dependency boundary check.
- [x] Private repository CI/test policy is established.
- [x] Public consumer rules are recorded in final sprint evidence.
- [x] Final public repository regression suite passes.
- [x] Final private repository test suite passes.
- [x] `git diff --check` is clean in both repositories.
- [x] Final staged changes are reviewed for accidental proprietary exposure.
- [x] All substantive IP.05 implementation PRs are merged.
- [x] Both repositories were verified clean before closure documentation.

---

## Post-IP.05 Operating Rule

After IP.05, IP protection becomes a standing architectural invariant rather than an endless sequence of dedicated IP sprints.

Future development should continue normally while enforcing:

```text
PUBLIC / INTERNAL / PROPRIETARY classification
public-contract boundaries
serialization/export boundaries
private repository placement
one-way dependency direction
consumer isolation from proprietary internals
```

Additional IP-specific sprints should be created only when a concrete new risk or commercial requirement appears.

---

## Final Intended Result

IP.05 completes the foundational IP-protection architecture for AI Test Lab. The foundational IP-protection program is now closed, and these controls become standing architectural invariants for future development.

The project moves from:

```text
single implementation repository
+ review discipline
```

to:

```text
public framework repository
        +
private proprietary repository
        +
explicit public contracts
        +
enforced export boundary
        +
enforced dependency direction
```

The durable rule is:

> **Proprietary implementation lives in `AI-Test-Lab-Private`; public code remains independently usable; external consumers depend only on approved public contracts.**
