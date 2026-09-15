from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_all_ten_slice_documents_and_overview_exist() -> None:
    assert (ROOT / "docs/sprints/atl-a.06.md").is_file()
    for number in range(1, 11):
        assert (ROOT / "docs/sprints" / f"atl-a.06.{number:02d}.md").is_file()

def test_ledger_layer_remains_provider_and_storage_neutral() -> None:
    sources = "\n".join(path.read_text(encoding="utf-8") for path in
        (ROOT / "src").glob("reference_architecture_evidence_ledger*.py"))
    for forbidden in ("ollama", "openai", "deepeval", "psycopg", "sqlite3", "boto3", "blockchain"):
        assert forbidden not in sources.lower()

def test_public_outcome_contains_no_protected_contract_fields() -> None:
    source = (ROOT / "src/reference_architecture_evidence_ledger_outcome.py").read_text(encoding="utf-8")
    for forbidden in ("key_id:", "signature:", "policy_id:", "storage_location:", "traceback:", "score:"):
        assert forbidden not in source

def test_public_projection_does_not_serialize_internal_entry_directly() -> None:
    source = (ROOT / "src/reference_architecture_evidence_ledger_outcome.py").read_text(encoding="utf-8")
    assert "serialize_public_contract(outcome)" in source
    assert "serialize_public_contract(result)" not in source
    assert "serialize_public_contract(entry)" not in source

def test_orchestration_depends_on_replaceable_storage_port() -> None:
    source = (ROOT / "src/reference_architecture_evidence_ledger_orchestration.py").read_text(encoding="utf-8")
    assert "EvidenceLedgerPort" in source
    assert "ledger: InMemoryEvidenceLedger" not in source
