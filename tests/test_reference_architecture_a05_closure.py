from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_all_ten_slice_documents_exist() -> None:
    for number in range(1, 11):
        assert (ROOT / "docs" / "sprints" / f"atl-a.05.{number:02d}.md").is_file()


def test_admission_layer_does_not_import_crypto_or_provider_implementations() -> None:
    sources = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (ROOT / "src").glob("reference_architecture_evidence_admission_*.py")
    )
    for forbidden in ("cryptography", "hashlib", "ollama", "openai", "deepeval"):
        assert forbidden not in sources


def test_public_outcome_contains_only_approved_fields() -> None:
    source = (ROOT / "src" / "reference_architecture_evidence_admission_outcome.py").read_text()
    assert "policy_id:" not in source
    assert "signer_id:" not in source
    assert "key_id:" not in source
    assert "traceback" not in source
