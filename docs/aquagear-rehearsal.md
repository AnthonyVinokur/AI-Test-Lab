# Aquagear application integration rehearsal

IP classification: PUBLIC integration example and documentation; INTERNAL adapter
plumbing reviewed for intentional publication. No Aquagear implementation is
copied into AI Test Lab, and no proprietary scoring/governance logic is exposed.

This optional command connects AI Test Lab to the **Python RAG application path**
used by Aquagear's Streamlit controlled RAG surface. The repositories stay separate.
Streamlit does not need to be running. This does not test the browser UI or the
free-form chat surface, and does not exercise deployment/governance enforcement.

## Inspected baseline

- AI Test Lab: `d1c11cd8b9abed67b056aeb4c7e68e0130673036`.
- Aquagear: `58da2d3f73da90d70278aa68d190330d9566628a`.
- Aquagear `app.py` assembles `ControlledRetriever`, `DeterministicContextBuilder`,
  `ScenarioExecutor`, and `RAGExecutor`. Free-form chat calls the model directly;
  the controlled RAG surface calls `RAGExecutor.execute(RAGExecutionRequest(...))`.
- AI Test Lab's normal CLI uses `MultiModelRunner`, which creates `OllamaClient`.
  Its `ProviderNeutralReferenceIntegrationAdapter` guards a compatibility handshake
  around an injected port; it is not wired into this CLI to collect RAG answers.

The new optional `AquagearClient` implements the existing `generate(prompt)`
protocol. It calls the real Aquagear RAG executor, validates response identity,
and normalizes its answer for the existing `TestRunner`. The separate rehearsal
command writes normal JSON/HTML reports and allow-listed application receipts.
Application execution failures produce ERROR, rather than FAIL or XFAIL.
Existing CLI behavior and public report schema remain unchanged.

## Windows / PowerShell setup

Use the activated AI Test Lab virtual environment. Put both repositories beside
each other, or replace the Aquagear path below with its actual location.

```powershell
cd C:\Users\avino\PycharmProjects\AI-Test-Lab
Test-Path ..\Aquagear-Reference-App\reference_app\rag_executor.py
python -m pip install "pydantic>=2,<3" jsonschema requests pytest
```

`Test-Path` must return True. The packages are already covered by AI Test Lab's
full requirements; the small command above is enough for this isolated rehearsal.
Run only a trusted Aquagear checkout: its Python modules execute locally.

## 1. Verify wiring without Ollama

```powershell
python -m src.aquagear_rehearsal --aquagear-root ..\Aquagear-Reference-App --mode controlled --output-dir results\aquagear-controlled
```

Expected: one PASS and exit code 0. Aquagear receives the question
`How should I clean my snorkel?`, retrieves `snorkel-care-001`, and its built-in
CI responder returns `Rinse the snorkel with fresh water after use.`

This executes real Aquagear retrieval, context construction, prompt construction,
and scenario execution, with a deterministic responder replacing the LLM. It
proves wiring and report propagation, not real model quality. Its CI responder
is question-based: it must not be used to claim detection of retrieval defects.

## 2. Run the real local model

```powershell
ollama list
python -m src.aquagear_rehearsal --aquagear-root ..\Aquagear-Reference-App --mode ollama --model llama3.1:latest --output-dir results\aquagear-live
$LASTEXITCODE
Start-Process .\results\aquagear-live\report.html
Get-Content .\results\aquagear-live\application-receipts.json
```

Aquagear's existing model boundary uses `http://localhost:11434/api/generate`
with a 120-second timeout. Start Ollama locally if it is unavailable. The live
command never falls back silently to the CI responder. A response missing the
smoke-test phrase can produce FAIL even when transport worked: inspect the actual
answer. This one keyword assertion proves propagation, not comprehensive quality.

## 3. Verify application errors remain errors

```powershell
python -m src.aquagear_rehearsal --aquagear-root ..\Aquagear-Reference-App --mode controlled --failure-mode execution_error --output-dir results\aquagear-error
$LASTEXITCODE
```

Expected: one ERROR, exit code 1, and reports are still generated. The receipt
shows that Aquagear received the request but failed execution. This injected
application failure is not evidence of a real unavailable server; the automated
tests separately simulate a connection error through Aquagear's Ollama boundary.

## Evidence to inspect

- `report.json`: existing public report, provider `aquagear`, test ID and answer.
- `report.html`: the same answer and verdict under View details.
- `application-receipts.json`: mode, available Git revisions, unique execution ID,
  test ID, question, retrieved document IDs, execution status, and response.

Match the test ID and response across the report and receipt. The application
receipt is in-process evidence from the returned RAG result, not an independent
server audit log. Revisions identify HEAD only, not uncommitted modifications;
record `git status` for both checkouts when preserving a rehearsal. If Git metadata
is unavailable, the revision is null rather than invented. Source inspection and
the initial controlled run here used files fetched at the baseline SHAs above.

The application interface returns text without token/cost metrics. Those fields
remain existing report defaults of zero, **not measured zero usage/cost**. The
outer response duration is measured. Retrieved context and internal prompts are
not exported into the frozen report schema. This command uses built-in assertions
only; it does not yet configure semantic evaluators against retrieved context.

## Automated verification

```powershell
$env:AQUAGEAR_ROOT = (Resolve-Path ..\Aquagear-Reference-App).Path
python -m pytest tests/test_aquagear_rehearsal.py -q
```

These tests run the actual Aquagear modules and both AI Test Lab reporters. They
check receipt/answer propagation, assertion failure, execution error, simulated
Ollama connection failure, response identity, empty answers, unique request IDs,
and invalid input. Cross-repository tests skip when AQUAGEAR_ROOT is unset.

Exit codes: 0 all cases acceptable; 1 test failure or application execution error;
2 invalid input/setup; 3 report filesystem failure.

## Recorded verification

On the inspected source snapshots, 11 targeted tests passed. The controlled
command produced one PASS; its generated [HTML report](evidence/aquagear-controlled/report.html),
[JSON report](evidence/aquagear-controlled/report.json), and
[application receipt](evidence/aquagear-controlled/application-receipts.json)
are retained as sample evidence. Git revisions are null in those generated files
because the runtime files were fetched through the GitHub connector, without a
local Git checkout; the exact source revisions are listed above.

The live Ollama attempt in this workspace produced ERROR (OllamaModelError),
with reports generated successfully. No live-model success is claimed. The
user's Windows Ollama service is not reachable from this workspace; run step 2
locally to complete that validation. Streamlit/browser validation and application
quality beyond this one smoke assertion remain separate exercises.
