<div align="center">

# AI Test Lab

### A Python framework for repeatable testing, evaluation, and reporting of AI and LLM systems

[![Python](https://img.shields.io/badge/Python-3.13%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![pytest](https://img.shields.io/badge/Tested%20with-pytest-0A9EDC?logo=pytest&logoColor=white)](https://pytest.org/)
[![Ollama](https://img.shields.io/badge/Models-Ollama-black)](https://ollama.com/)
[![Status](https://img.shields.io/badge/status-active%20development-orange)](#project-status)

**Define test cases. Run them across one or more local models. Evaluate the responses. Produce evidence.**

</div>

---

## What is AI Test Lab?

AI Test Lab is an open-source testing framework for evaluating large language model behavior with structured, repeatable test cases.

It applies familiar software-testing practices to nondeterministic AI systems: explicit assertions, automated execution, expected-failure handling, model comparison, performance measurement, regression detection, and machine-readable reporting.

The project is designed as a practical engineering lab for developers, QA engineers, test-automation specialists, and teams exploring reliable AI quality assurance.

## Why this project exists

Traditional software tests usually compare deterministic outputs. LLM responses are variable, context-sensitive, and model-dependent. A useful AI testing system therefore needs more than a collection of prompts.

AI Test Lab is being built to provide:

- repeatable prompt and dataset execution;
- transparent pass, fail, error, XFAIL, and XPASS outcomes;
- reusable response assertions;
- side-by-side execution across multiple models;
- latency, token, and throughput measurements;
- JSON and human-readable HTML evidence;
- a foundation for AI safety, security, regression, and governance testing.

## Current capabilities

### Test execution

- Run structured prompt tests from JSON files.
- Run versioned tests from managed datasets.
- Execute the same suite against one or multiple Ollama models.
- Return meaningful command-line exit codes for local use and CI pipelines.

### Response evaluation

Supported assertion strategies include:

- `contains`
- `not_contains`
- `equals`
- `starts_with`
- `ends_with`
- `icontains`
- `regex`

Expected failures are represented explicitly, allowing known model limitations to remain visible without being confused with new regressions.

### Reporting and metrics

Each test result can include:

- model name;
- actual response;
- evaluation status and explanation;
- prompt and output token counts;
- total response time;
- prompt-processing latency;
- generation latency;
- model load time;
- prompt and generation throughput;
- JSON report output;
- styled HTML report output.

## How it works

```text
Prompt file or managed dataset
            |
            v
       Test loader
            |
            v
    Multi-model runner
            |
            v
      Ollama models
            |
            v
   Assertion evaluator
            |
            v
 CLI + JSON + HTML reports
```

## Quick start

### Prerequisites

- Python 3.13 or newer
- Git
- Ollama installed and running
- At least one local Ollama model

### 1. Clone the repository

```bash
git clone https://github.com/AnthonyVinokur/AI-Test-Lab.git
cd AI-Test-Lab
```

### 2. Create and activate a virtual environment

**Windows PowerShell**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**macOS or Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Prepare an Ollama model

```bash
ollama pull llama3.1
ollama list
```

### 5. Run the test suite

```bash
python -m pytest
```

### 6. Run AI Test Lab

```bash
python main.py
```

The default run loads `prompts/prompts.json`, executes the tests with `llama3.1:latest`, and creates:

```text
results/latest_results.json
results/latest_report.html
```

## Command-line examples

Show all options:

```bash
python main.py --help
```

Run one model:

```bash
python main.py --models llama3.1:latest
```

Compare multiple models:

```bash
python main.py --models llama3.1:latest qwen2.5-coder:7b
```

Use a custom prompt file:

```bash
python main.py --prompts prompts/prompts.json
```

Run the latest active version of a managed dataset:

```bash
python main.py --dataset regression-core
```

Run a specific dataset version:

```bash
python main.py --dataset regression-core --dataset-version 2
```

Choose report locations:

```bash
python main.py \
  --report results/run_results.json \
  --html-report results/run_report.html
```

## Example test definition

```json
{
  "test_id": "greeting-001",
  "name": "Basic greeting",
  "category": "functional",
  "prompt": "Say hello",
  "assertion": {
    "type": "contains",
    "expected": "Hello"
  }
}
```

A test defines the input, the evaluation rule, and the expected behavior. The runner captures the model response and operational metrics, while the evaluator converts the observation into a traceable test result.

## Project  structure

```text
AI-Test-Lab/
|-- datasets/              # Managed and versioned AI test datasets
|-- prompts/               # JSON prompt test definitions
|-- results/               # Generated JSON and HTML reports
|-- src/                   # Framework implementation
|   |-- dataset_loader.py
|   |-- datasets.py
|   |-- evaluator.py
|   |-- html_reporter.py
|   |-- json_reporter.py
|   |-- models.py
|   |-- multi_model_runner.py
|   |-- ollama_client.py
|   `-- prompt_loader.py
|-- tests/                 # Automated pytest suite
|-- main.py                # Command-line entry point
|-- requirements.txt
`-- README.md
```

## Testing philosophy

AI Test Lab treats AI evaluation as an evidence-producing engineering process:

1. Define the expected behavior before execution.
2. Preserve the model's actual response.
3. Separate expected limitations from unexpected regressions.
4. Record performance data alongside functional results.
5. Keep results reproducible and suitable for automation.
6. Expand from simple assertions toward richer safety, security, and quality evaluations.

## Roadmap

The framework is being developed incrementally. Planned areas include:

- GitHub Actions continuous integration;
- richer multi-model comparison reports;
- dataset lifecycle and traceability improvements;
- hallucination and groundedness evaluation;
- prompt-injection and jailbreak testing;
- toxicity, bias, and policy-compliance checks;
- LLM-as-a-judge evaluation with calibration controls;
- Playwright-based testing of AI-enabled web applications;
- trend analysis and regression history;
- compliance-oriented audit reports for enterprise AI governance.

## Project status

**Active development — Sprint11.6**

The current release is an engineering work in progress, not yet a production compliance platform. APIs, report schemas, dataset formats, and command-line options may evolve as the framework matures.

## Who is building it?

AI Test Lab is created by **Anthony Vinokur**, a Python and Playwright test-automation specialist expanding traditional QA engineering into AI system evaluation, LLM testing, and AI quality governance.

- GitHub: [AnthonyVinokur](https://github.com/AnthonyVinokur)
- Project repository: [AI-Test-Lab](https://github.com/AnthonyVinokur/AI-Test-Lab)

## Contributing

The project is currently evolving rapidly. Bug reports, test ideas, architecture feedback, and focused pull requests are welcome.

Before submitting a change:

```bash
python -m pytest
```

Please keep changes small, documented, and covered by tests where practical.

## Disclaimer

AI Test Lab reports are engineering evidence, not guarantees of model safety, regulatory compliance, factual correctness, or fitness for a particular use. High-impact AI systems require domain-specific validation, human oversight, security review, and appropriate legal or compliance expertise.

---

<div align="center">

**Built to make AI behavior testable, visible, and accountable.**

</div>
