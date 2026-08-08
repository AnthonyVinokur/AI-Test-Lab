# AI Test Lab Architecture Overview
| Metadata              | Value |
|-----------------------|-------|
| **Status**            | Approved Architecture |
| **Version**           | 1.0.0 |
| **Last Updated**      | 2026-08-03 |
| **Document Owner**    | AI Test Lab Core Team |
| **Applies To**        | AI Test Lab Framework v1.x |
| **Related Documents** | [core-framework.md](core-framework.md), [evaluation-engine.md](evaluation-engine.md), [model-providers.md](model-providers.md), [plugin-system.md](plugin-system.md) |
| **Audience**        | Developers, Contributors, Architects |
## Purpose

AI Test Lab is a lightweight, extensible framework for evaluating Large Language Models (LLMs) and AI systems using repeatable automated tests.

The framework separates core orchestration from evaluation engines, model providers, reporting systems, and datasets so organizations can adopt only the components they need.

---

# Design Goals

AI Test Lab is designed around several core principles.

- Lightweight core
- Plugin architecture
- Provider independent
- Evaluation-engine independent
- CI/CD friendly
- Local-first with cloud support
- Enterprise ready
- Reproducible evaluations

---

# High-Level Architecture

```
                 +----------------------+
                 |      CLI / API       |
                 +----------+-----------+
                            |
                            v
                 +----------------------+
                 |    Core Framework    |
                 |----------------------|
                 | Test Runner          |
                 | Dataset Manager      |
                 | Configuration        |
                 | Result Manager       |
                 +----------+-----------+
                            |
          +-----------------+-----------------+
          |                 |                 |
          v                 v                 v

 +----------------+  +----------------+  +----------------+
 | Model Provider |  | Evaluation     |  | Reporters      |
 | Abstraction    |  | Engine         |  | HTML           |
 |                |  |                |  | JSON           |
 | Ollama         |  | DeepEval       |  | JUnit          |
 | OpenAI         |  | Ragas          |  | Allure         |
 | Anthropic      |  | TruLens        |  | Dashboard      |
 | Azure OpenAI   |  | Custom         |  | etc.           |
 +----------------+  +----------------+  +----------------+

                            |
                            v

                 +----------------------+
                 | Datasets / Benchmarks|
                 | YAML                 |
                 | JSON                 |
                 | CSV                  |
                 +----------------------+
```
## Architecture

AI Test Lab separates model execution, evaluation, reporting, and quality gates into independent components.

```
                Prompt Dataset
                      │
                      ▼
              MultiModelRunner
                      │
                      ▼
               EvaluationPipeline
                      ▲
                      │
          Evaluation Profile (YAML)
                      │
                      ▼
             Pipeline Builder
                      │
          ┌───────────┴────────────┐
          │                        │
   Assertion Engine        External Engines
                                    │
          ┌─────────────────────────┼────────────────────┐
          │                         │                    │
      DeepEval                  Ragas             TruLens
```

This modular architecture allows semantic evaluation engines to be added without modifying the core framework.
---

# Core Components

## Test Runner

Responsible for orchestrating an evaluation run.

Responsibilities:

- load datasets
- call model providers
- execute evaluation engines
- collect metrics
- produce reports

The Test Runner contains no model-specific logic.

---

## Model Providers

A provider abstracts communication with an AI model.

Examples:

- Ollama
- OpenAI
- Anthropic
- Azure OpenAI
- AWS Bedrock
- Google Gemini

Every provider implements the same interface.

---

## Evaluation Engines

Evaluation engines calculate quality metrics.

Supported engines include:

- DeepEval
- Ragas
- TruLens

Future engines can be added without modifying the framework core.

---

## Dataset Manager

Responsible for

- loading datasets
- validation
- versioning
- metadata
- prompt templates

Supported formats

- YAML
- JSON
- CSV

---

## Report System

Responsible for producing output.

Examples:

- JSON
- HTML
- Allure
- JUnit XML
- Dashboard API

---

## Plugin System

The framework is intentionally modular.

Organizations should be able to enable only the capabilities they require.

Example:

Core Framework

+ DeepEval plugin

+ Ollama provider

+ HTML Reporter

without installing every dependency.

---

# Repository Structure

```
ai-test-lab/

docs/
src/
tests/
datasets/
reports/
examples/
plugins/
```

---

# Architectural Principles

AI Test Lab follows these principles.

1. Composition over inheritance.
2. Clear interfaces.
3. Dependency inversion.
4. Minimal core.
5. Plugins for optional functionality.
6. Deterministic evaluation.
7. CI/CD first.
8. Enterprise extensibility.

---

# Future Expansion

The architecture intentionally supports future modules including:

- AI Gateway
- Model Gateway
- Prompt Registry
- Prompt Versioning
- Dataset Registry
- Benchmark Marketplace
- Web Dashboard
- Multi-Agent Evaluation
- Human Review Workflows
- Cost Tracking
- Performance Analytics
- Enterprise Authentication
- RBAC
- REST API
- SDK
- Cloud Deployment
- - Engine-agnostic evaluation architecture
- Pluggable evaluation engines
- DeepEval integration
- Normalized evaluation results
- JSON reporting
- HTML reporting
- Extensible reporter pipeline
- Pytest integration
- Local model support (Ollama)
- CI/CD friendly execution

These modules remain optional and do not increase the complexity of the framework core.

---

# Summary

AI Test Lab is built around a small orchestration core surrounded by interchangeable providers, evaluation engines, reporters, and plugins. This architecture keeps the framework lightweight while allowing enterprise-scale expansion without redesigning the core.