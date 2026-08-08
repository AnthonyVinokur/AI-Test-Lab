from argparse import Namespace
from pathlib import Path
from src.cli.execution import load_test_cases
import src.cli.execution as execution
from src.datasets import DatasetEntry, DatasetService, DatasetStatus, JsonDatasetRepository


def test_load_test_cases_uses_dataset(tmp_path: Path) -> None:
    storage = tmp_path / "datasets"
    service = DatasetService(JsonDatasetRepository(storage))
    dataset = service.create_dataset(name="CLI dataset", entries=[DatasetEntry(name="Greeting", input="Say hello", expected_output="Hello")])
    service.set_status(dataset.manifest.id, DatasetStatus.ACTIVE)
    args = Namespace(dataset=dataset.manifest.id, dataset_storage=storage, dataset_version=None, prompts=None)
    cases = load_test_cases(args)
    assert len(cases) == 1
    assert cases[0].name == "Greeting"


def test_defaults_to_prompt_file(monkeypatch) -> None:
    expected = [object()]
    captured = {}
    def fake_loader(path: Path) -> list:
        captured["path"] = path
        return expected
    monkeypatch.setattr(execution, "load_prompt_tests", fake_loader)
    args = Namespace(dataset=None, dataset_storage=Path("datasets"), dataset_version=None, prompts=None)
    result = load_test_cases(args)
    assert result is expected
    assert captured["path"] == Path("prompts/prompts.json")
