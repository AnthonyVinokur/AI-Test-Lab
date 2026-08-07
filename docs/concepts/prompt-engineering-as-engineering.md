# From Prompt Engineering to Prompt Quality Engineering

> **Prompt engineering becomes engineering when we start measuring it.**

There is a reasonable criticism of the term **prompt engineering**.

Changing a few words in a prompt, running it again, and deciding that the new response "looks better" is not a rigorous engineering process.

**AI Test Lab agrees.**

But the problem is not prompting itself.

The problem is the absence of **systematic experimentation, measurable evaluation, and regression testing**.

---

## The AI Test Lab Point of View

If a prompt is part of a production AI system, changing that prompt should be treated much like changing code.

A prompt change can affect:

- factual correctness
- hallucination behavior
- instruction following
- response consistency
- latency
- token consumption
- model-specific behavior
- previously working use cases

Therefore, a prompt should not be considered improved simply because one or two manually inspected responses appear better.

It should be **tested**.

---

## The Problem With "Looks Better"

Consider a simple scenario.

A developer modifies a production prompt.

The new response looks better.

But what happened to the other 200 test cases?

Did factual correctness improve?

Did hallucination increase?

Did previously passing cases start failing?

Did latency change?

Did token usage increase?

Does the prompt behave similarly with another model?

Without systematic evaluation, we cannot confidently answer those questions.

We only know that:

> **One example looked better.**

That is experimentation by observation.

It is not yet engineering-grade validation.

---

## Treat Prompts as Testable Software Artifacts

AI Test Lab approaches prompts as artifacts that can be:

- version controlled
- executed against datasets
- evaluated using explicit criteria
- compared across models
- measured using repeatable metrics
- tested for regressions
- included in CI/CD pipelines
- subjected to automated quality gates

The basic workflow is:

```text
Prompt
   ↓
Dataset
   ↓
Model
   ↓
Evaluation
   ↓
Metrics
   ↓
Report
   ↓
Quality Gate