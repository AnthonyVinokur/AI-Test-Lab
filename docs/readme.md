# AI Test Lab

<p align="center">

![Python](https://img.shields.io/badge/Python-3.13+-3776AB?style=for-the-badge&logo=python&logoColor=white)

![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

![Tests](https://img.shields.io/github/actions/workflow/status/AnthonyVinokur/AI-Test-Lab/tests.yml?style=for-the-badge&label=Tests)

![Coverage](https://img.shields.io/badge/Coverage-100%25-brightgreen?style=for-the-badge)

![Release](https://img.shields.io/github/v/release/AnthonyVinokur/AI-Test-Lab?style=for-the-badge)

![Docs](https://img.shields.io/badge/Documentation-Active-blue?style=for-the-badge)

</p>

# AI Test Lab

Enterprise-ready framework for automated LLM evaluation, prompt regression testing, and AI quality engineering.

AI Test Lab enables engineering teams to validate prompts, compare models, measure AI quality, and detect regressions using a standardized, engine-independent evaluation pipeline.

The framework integrates modern evaluation engines—including DeepEval, Ragas, and future providers—while exposing a stable internal API for reporting, CI/CD, and enterprise automation.


## Why AI Test Lab?

Modern AI applications evolve continuously.

Prompt changes, model upgrades, and evaluation frameworks all introduce uncertainty.

AI Test Lab provides repeatable, automated evidence that an AI system continues to meet quality expectations before it reaches production.

## Features

- Engine-independent evaluation framework
- DeepEval integration
- Future support for Ragas and TruLens
- Prompt regression testing
- Dataset validation
- JSON and HTML reporting
- Evaluation normalization layer
- Performance metrics
- CI/CD integration
- Lightweight plugin architecture
-  Prompt regression testing
- Multiple model evaluation
- Deterministic assertion engine
- Engine-agnostic evaluation pipeline
- External evaluation plugin architecture
- HTML and JSON reporting
- CI/CD friendly execution
- - Prompt regression testing
- Multi-model evaluation
- External evaluation engine plugins
- Configuration-driven evaluation profiles
- JSON & HTML reporting
- CI/CD quality gates

## Architecture

Dataset / Prompt
        │
        ▼
 Model Provider
        │
        ▼
 Built-in Assertions
        │
        ▼
 External Evaluation Engines
        │
        ▼
 Verdict Policy
        │
        ▼
 JSON • HTML • Quality Gate

## Project Status

Current Release

Sprint 10.6

Completed

- Dataset Management
- Evaluation Framework
- Evaluation Pipeline
- Engine Abstraction
- Engine-independent Reporting
- DeepEval Integration

Next

Sprint 10.7

- Production evaluation pipeline
- Multiple evaluation engines
- CI quality gates
- 
### Evaluation Pipeline

- Built-in deterministic assertions
- Pluggable evaluation engine architecture
- Configurable evaluation quality gates
- Multiple verdict policies
- Engine-agnostic evaluation pipeline
- Structured evaluation metrics
- 
## Documentation

| Document | Description |
|-----------|-------------|
| Architecture Overview | Overall system design |
| Sprint Documentation | Technical implementation history |
| Roadmap | Planned development |
| Changelog | Release history |

## Roadmap

- Multiple evaluation engines
- Multi-provider support
- REST API
- Web Dashboard
- GitHub Actions
- Enterprise reporting
- Plugin ecosystem