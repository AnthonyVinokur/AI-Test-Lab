from pathlib import Path
import pytest
from src.dataset_loader import DatasetNotActiveError, EmptyDatasetError, load_dataset_tests
from src.datasets import DatasetEntry, DatasetService, DatasetStatus, JsonDatasetRepository


def test_loads_latest_active_dataset(tmp_path: Path) -> None:
    storage = tmp_path / "datasets"
    service = DatasetService(JsonDatasetRepository(storage))
    dataset = service.create_dataset(name="Core Regression", entries=[DatasetEntry(name="Basic greeting", input="Say hello", expected_output="Hello", category="functional")])
    service.set_status(dataset.manifest.id, DatasetStatus.ACTIVE)
    tests = load_dataset_tests(dataset.manifest.id, storage_dir=storage)
    assert len(tests) == 1
    assert tests[0].prompt == "Say hello"
    assert tests[0].assertion.expected == "Hello"


def test_rejects_draft_dataset(tmp_path: Path) -> None:
    storage = tmp_path / "datasets"
    service = DatasetService(JsonDatasetRepository(storage))
    dataset = service.create_dataset(name="Draft", entries=[DatasetEntry(name="Greeting", input="Say hello", expected_output="Hello")])
    with pytest.raises(DatasetNotActiveError):
        load_dataset_tests(dataset.manifest.id, storage_dir=storage)


def test_skips_disabled_entries(tmp_path: Path) -> None:
    storage = tmp_path / "datasets"
    service = DatasetService(JsonDatasetRepository(storage))
    dataset = service.create_dataset(name="Enabled only", entries=[
        DatasetEntry(name="Enabled", input="Say hello", expected_output="Hello"),
        DatasetEntry(name="Disabled", input="Do not run", expected_output="No", enabled=False),
    ])
    service.set_status(dataset.manifest.id, DatasetStatus.ACTIVE)
    tests = load_dataset_tests(dataset.manifest.id, storage_dir=storage)
    assert [test.name for test in tests] == ["Enabled"]


def test_rejects_empty_active_dataset(tmp_path: Path) -> None:
    storage = tmp_path / "datasets"
    service = DatasetService(JsonDatasetRepository(storage))
    dataset = service.create_dataset(name="Empty")
    service.set_status(dataset.manifest.id, DatasetStatus.ACTIVE)
    with pytest.raises(EmptyDatasetError):
        load_dataset_tests(dataset.manifest.id, storage_dir=storage)
