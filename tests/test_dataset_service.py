from pathlib import Path

import pytest
from pydantic import ValidationError

from src.datasets import (
    DatasetEntry,
    DatasetService,
    DatasetStatus,
    DuplicateEntryError,
    JsonDatasetRepository,
)


@pytest.fixture
def service(tmp_path: Path) -> DatasetService:
    return DatasetService(JsonDatasetRepository(tmp_path / "datasets"))


def test_create_dataset(service: DatasetService) -> None:
    dataset = service.create_dataset(
        name="Safety Regression",
        entries=[DatasetEntry(name="Refusal", input="Unsafe request")],
        tags=["Safety"],
    )

    assert dataset.manifest.latest_version == 1
    assert dataset.manifest.tags == ["safety"]
    assert len(dataset.latest().entries) == 1
    assert len(dataset.latest().checksum) == 64


def test_entry_validation_rejects_blank_input() -> None:
    with pytest.raises(ValidationError):
        DatasetEntry(name="Invalid", input="   ")


def test_add_entry_creates_new_immutable_version(service: DatasetService) -> None:
    dataset = service.create_dataset(name="Core")
    first_checksum = dataset.latest().checksum

    updated = service.add_entry(
        dataset.manifest.id,
        DatasetEntry(name="Greeting", input="Say hello", expected_output="Hello"),
    )

    assert updated.manifest.latest_version == 2
    assert updated.versions[0].entries == []
    assert len(updated.versions[1].entries) == 1
    assert updated.versions[1].checksum != first_checksum


def test_duplicate_entry_id_is_rejected(service: DatasetService) -> None:
    entry = DatasetEntry(name="Greeting", input="Say hello")
    dataset = service.create_dataset(name="Core", entries=[entry])

    with pytest.raises(DuplicateEntryError):
        service.add_entry(dataset.manifest.id, entry)


def test_update_and_remove_entry(service: DatasetService) -> None:
    entry = DatasetEntry(name="Greeting", input="Say hello")
    dataset = service.create_dataset(name="Core", entries=[entry])

    updated = service.update_entry(
        dataset.manifest.id,
        entry.id,
        {"expected_output": "Hello"},
    )
    assert updated.latest().entries[0].expected_output == "Hello"

    removed = service.remove_entry(dataset.manifest.id, entry.id)
    assert removed.manifest.latest_version == 3
    assert removed.latest().entries == []


def test_rollback_creates_new_version(service: DatasetService) -> None:
    first = DatasetEntry(name="One", input="1")
    dataset = service.create_dataset(name="Rollback", entries=[first])
    dataset = service.add_entry(
        dataset.manifest.id,
        DatasetEntry(name="Two", input="2"),
    )

    rolled_back = service.rollback(dataset.manifest.id, 1)

    assert rolled_back.manifest.latest_version == 3
    assert [entry.name for entry in rolled_back.latest().entries] == ["One"]


def test_status_and_filtering(service: DatasetService) -> None:
    dataset = service.create_dataset(name="Production", tags=["release"])
    service.set_status(dataset.manifest.id, DatasetStatus.ACTIVE)

    active = service.list_datasets(status=DatasetStatus.ACTIVE, tag="release")

    assert len(active) == 1
    assert active[0].name == "Production"


def test_import_entries_creates_new_version(service: DatasetService) -> None:
    dataset = service.create_dataset(name="Imported")

    updated = service.import_entries(
        dataset.manifest.id,
        [
            {
                "name": "Imported greeting",
                "input": "Say hello",
                "expected_output": "Hello",
                "tags": ["Smoke", "smoke"],
            }
        ],
    )

    assert updated.manifest.latest_version == 2
    assert updated.latest().entries[0].tags == ["smoke"]


def test_data_persists_across_repository_instances(tmp_path: Path) -> None:
    storage = tmp_path / "datasets"
    first_service = DatasetService(JsonDatasetRepository(storage))
    dataset = first_service.create_dataset(name="Persistent")

    second_service = DatasetService(JsonDatasetRepository(storage))
    loaded = second_service.get_dataset(dataset.manifest.id)

    assert loaded.manifest.name == "Persistent"
