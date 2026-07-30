---
title: Test Reports
description: Understand AI Test Lab HTML reports, model comparisons, execution metrics, and individual test results.
---


AI Test Lab generates structured reports that explain how each model performed, which tests passed or failed, and how much time and output each evaluation consumed.

<img
  src="/images/ai-test-lab-report.png"
  alt="AI Test Lab multi-model evaluation report"
/>
*Example multi-model report comparing pass rate, response time, generation speed, output tokens, and detailed test results.*

The HTML report is designed for both engineers and nontechnical stakeholders.

## Report summary

The top section provides an immediate view of the evaluation run:

- total evaluations;
- passed tests;
- failed tests;
- errors;
- overall pass rate;
- estimated execution cost.

A multi-model run also identifies:

- the top-ranked model;
- the fastest model by average response time.

## Model comparison

The model comparison table aggregates results for every tested model.

Typical fields include:

| Field | Meaning |
| --- | --- |
| Provider | The model provider, such as Ollama |
| Model | The exact model identifier |
| Passed | Number of successful evaluations |
| Failed | Number of failed evaluations |
| Errors | Number of execution errors |
| Total | Total evaluations for the model |
| Pass Rate | Percentage of evaluations that passed |
| Avg Response | Average end-to-end response time |
| Avg Generation | Average generation latency |
| Avg Speed | Average generated tokens per second |
| Avg Output Tokens | Mean output-token count |
| Total Cost | Estimated cost for the model run |

## Example comparison

In one evaluation run:

- `qwen2.5-coder:7b` completed 7 evaluations;
- `llama3.1:latest` completed 7 evaluations;
- both models achieved a 71.43% pass rate;
- `qwen2.5-coder:7b` had the faster average response time.

This makes the report useful for comparing quality and performance without reviewing each raw response manually.

## Individual test results

The individual-results table displays each executed test separately.

Each row includes:

- test ID;
- provider;
- model;
- status;
- response time;
- estimated cost;
- a link to detailed evaluation evidence.

Possible statuses are:

- `PASS`
- `FAIL`
- `ERROR`

## Detailed evidence

The detail view should provide enough information to explain the result, including:

- original prompt;
- actual model response;
- assertion type;
- expected value;
- evaluation reason;
- token counts;
- latency measurements;
- generation speed;
- model and provider information.

This is important because an AI evaluation result should not only state that a test failed. It should also preserve the evidence needed to understand why it failed.

## Multi-model evaluation

AI Test Lab can execute the same prompt suite against multiple models.

Example:

```powershell
python main.py --models llama3.1:latest qwen2.5-coder:7b