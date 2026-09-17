"""Cross-repository checks; set AQUAGEAR_ROOT to an actual Aquagear checkout."""

import json
import os
from dataclasses import replace
from pathlib import Path

import pytest

from src.aquagear_client import AquagearExecutionError, build_aquagear_client
from src.aquagear_rehearsal import main


@pytest.fixture
def aquagear_root(monkeypatch):
    value = os.environ.get("AQUAGEAR_ROOT")
    if not value:
        pytest.skip("Set AQUAGEAR_ROOT to run the cross-repository rehearsal tests")
    root = Path(value).resolve()
    assert (root / "reference_app" / "rag_executor.py").is_file()
    monkeypatch.syspath_prepend(str(root))
    return root


def run_rehearsal(root, tmp_path, *extra):
    output = tmp_path / "results"
    code = main([
        "--aquagear-root", str(root), "--mode", "controlled",
        "--prompts", str(Path(__file__).resolve().parents[1] / "prompts/aquagear-smoke.json"),
        "--output-dir", str(output), *extra,
    ])
    report = json.loads((output / "report.json").read_text())
    receipt = json.loads((output / "application-receipts.json").read_text())
    return code, report, receipt, (output / "report.html").read_text()


def test_real_aquagear_round_trip_and_both_reports(aquagear_root, tmp_path):
    code, report, evidence, html = run_rehearsal(aquagear_root, tmp_path)
    assert code == 0
    assert report["summary"]["passed"] == 1
    receipt = evidence["receipts"][0]
    assert receipt["application_received"] is True
    assert receipt["retrieved_document_ids"] == ["snorkel-care-001"]
    assert receipt["question"] == "How should I clean my snorkel?"

    assert receipt["response"] == (
        "Rinse the snorkel with fresh water after use "
        "and allow it to air dry before storage."
    )

    assert receipt["response"] in html

    assert receipt["response"] in json.dumps(report)
    assert receipt["test_id"] == report["results"][0]["test_id"]
    assert report["results"][0]["provider"] == "aquagear"
    assert evidence["mode"] == "controlled"


def test_application_error_is_error_not_assertion_failure(aquagear_root, tmp_path):
    code, report, evidence, html = run_rehearsal(
        aquagear_root, tmp_path, "--failure-mode", "execution_error",
    )
    assert code == 1
    assert report["summary"]["errors"] == 1
    assert report["summary"]["failed"] == 0
    receipt = evidence["receipts"][0]
    assert receipt["application_received"] is True
    assert receipt["response"] is None
    assert receipt["status"] == "error"
    assert "ERROR" in html


def test_wrong_expectation_fails_without_execution_error(aquagear_root, tmp_path):
    source = Path(__file__).resolve().parents[1] / "prompts/aquagear-smoke.json"
    cases = json.loads(source.read_text())
    cases[0]["assertion"]["expected"] = "intentionally absent phrase"
    prompts = tmp_path / "wrong.json"
    prompts.write_text(json.dumps(cases))
    code, report, evidence, _ = run_rehearsal(
        aquagear_root, tmp_path, "--prompts", str(prompts),
    )
    assert code == 1
    assert report["summary"]["failed"] == 1
    assert report["summary"]["errors"] == 0
    assert evidence["receipts"][0]["status"] == "completed"


def test_ollama_connection_failure_is_reported(aquagear_root, tmp_path, monkeypatch):
    import requests
    from reference_app import ollama_model

    def unavailable(*args, **kwargs):
        raise requests.ConnectionError("private-url-must-not-be-reported")

    monkeypatch.setattr(ollama_model.requests, "post", unavailable)
    code, report, evidence, html = run_rehearsal(
        aquagear_root, tmp_path, "--mode", "ollama",
    )
    assert code == 1
    assert report["summary"]["errors"] == 1
    assert evidence["mode"] == "ollama"
    assert evidence["receipts"][0]["application_received"] is True
    assert "private-url" not in json.dumps(report) + json.dumps(evidence) + html


@pytest.mark.parametrize("defect", ["identity", "empty"])
def test_invalid_application_response_is_rejected(aquagear_root, defect):
    client = build_aquagear_client(mode="controlled")
    original = client.executor

    class InvalidExecutor:
        def execute(self, request):
            result = original.execute(request)
            if defect == "identity":
                return replace(result, execution_id="wrong-request")
            return replace(result, execution_result=replace(result.execution_result, response=""))

    client.executor = InvalidExecutor()
    with pytest.raises(AquagearExecutionError):
        client.generate("How should I clean my snorkel?")
    assert client.receipts[-1]["status"] == "error"


def test_repeated_questions_get_distinct_execution_ids(aquagear_root):
    client = build_aquagear_client(mode="controlled")
    client.generate("How should I clean my snorkel?")
    client.generate("How should I clean my snorkel?")
    assert len({r["execution_id"] for r in client.receipts}) == 2


def test_missing_checkout_is_input_error(tmp_path):
    assert main(["--aquagear-root", str(tmp_path)]) == 2


def test_blank_question_is_input_error(aquagear_root, tmp_path):
    prompts = tmp_path / "blank.json"
    prompts.write_text(json.dumps([{
        "id": "blank", "name": "blank", "category": "test", "prompt": "   ",
        "assertion": {"type": "equals", "expected": "answer"},
    }]))
    assert main(["--aquagear-root", str(aquagear_root), "--prompts", str(prompts)]) == 2


@pytest.mark.parametrize("cases", [[], [
    {"id": "same", "name": "name", "category": "test", "prompt": "question",
     "assertion": {"type": "equals", "expected": "answer"}},
] * 2])
def test_empty_or_duplicate_dataset_is_rejected(aquagear_root, tmp_path, cases):
    prompts = tmp_path / "invalid.json"
    prompts.write_text(json.dumps(cases))
    assert main([
        "--aquagear-root", str(aquagear_root), "--prompts", str(prompts),
        "--output-dir", str(tmp_path / "out"), "--mode", "controlled",
    ]) == 2
    assert not (tmp_path / "out").exists()
