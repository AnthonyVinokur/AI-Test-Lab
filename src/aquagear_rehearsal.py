"""Run Aquagear application questions through AI Test Lab's existing reports."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from time import perf_counter

from src.aquagear_client import AquagearExecutionError, build_aquagear_client
from src.evaluation_pipeline import EvaluationPipeline
from src.html_reporter import HtmlReporter
from src.json_reporter import JsonReporter
from src.models import EvaluationStatus, TestResult
from src.prompt_loader import load_prompt_tests
from src.runner import TestRunner


def _revision(root: Path) -> str | None:
    try:
        return subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            text=True, stderr=subprocess.DEVNULL, timeout=5,
        ).strip()
    except (OSError, subprocess.SubprocessError):
        return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aquagear-root", type=Path, required=True)
    parser.add_argument("--mode", choices=("controlled", "ollama"), default="ollama")
    parser.add_argument("--model", default="llama3.1:latest")
    parser.add_argument("--prompts", type=Path, default=Path("prompts/aquagear-smoke.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("results/aquagear-rehearsal"))
    parser.add_argument("--top-k", type=int, default=1)
    parser.add_argument("--failure-mode", choices=("none", "execution_error"), default="none")
    args = parser.parse_args(argv)

    root = args.aquagear_root.resolve()
    if not (root / "reference_app" / "rag_executor.py").is_file():
        print("Input error: --aquagear-root must point to an Aquagear checkout.")
        return 2
    sys.path.insert(0, str(root))
    try:
        import reference_app.rag_executor as aquagear_module
        if not Path(aquagear_module.__file__).resolve().is_relative_to(root):
            raise ValueError("A different Aquagear checkout is already imported; use a fresh process")
        cases = load_prompt_tests(args.prompts)
        if not cases or len({case.id for case in cases}) != len(cases):
            raise ValueError("Dataset must contain cases with unique IDs")
        if any(not case.prompt.strip() for case in cases):
            raise ValueError("Questions must not contain only whitespace")
        client = build_aquagear_client(
            mode=args.mode, model=args.model, top_k=args.top_k,
            failure_mode=args.failure_mode,
        )
    except (ImportError, OSError, ValueError) as exc:
        print(f"Input error: {exc}")
        return 2

    print(f"Aquagear RAG integration mode: {args.mode}")
    if args.mode == "controlled":
        print("Controlled CI responses: this is not a live LLM quality assessment.")
    runner = TestRunner(client=client, evaluation_pipeline=EvaluationPipeline())
    results = []
    for case in cases:
        start = perf_counter()
        try:
            result = runner.run_test(case)
        except AquagearExecutionError as exc:
            result = TestResult(
                test_id=case.id, name=case.name, category=case.category,
                prompt=case.prompt, provider="aquagear", model=client.model,
                actual_response="", passed=False, status=EvaluationStatus.ERROR,
                expected_to_fail=case.expected_to_fail,
                assertion_type=case.assertion.type, expected=case.assertion.expected,
                reason=str(exc), response_time_seconds=perf_counter() - start,
            )
        results.append(result)
        client.receipts[-1]["test_id"] = case.id
        print(f"{case.id}: {result.status.value} — {result.reason}")

    # Keep application receipts separate from the frozen public report schema.
    output = args.output_dir
    evidence = {
        "schema_version": "aquagear-rehearsal-1",
        "mode": args.mode,
        "application_revision": _revision(root),
        "ai_test_lab_revision": _revision(Path(__file__).resolve().parents[1]),
        "model": client.model,
        "top_k": args.top_k,
        "metrics_note": "Token/cost fields are unavailable from this application interface; report zeros are defaults, not measurements.",
        "receipts": client.receipts,
    }
    try:
        JsonReporter(output / "report.json").write(results)
        HtmlReporter(output / "report.html").write(results)
        (output / "application-receipts.json").write_text(
            json.dumps(evidence, indent=2), encoding="utf-8",
        )
    except OSError as exc:
        print(f"Report write error: {exc}")
        return 3
    print(f"Reports and application receipts: {output.resolve()}")
    print(evidence["metrics_note"])
    return 0 if all(result.passed for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
