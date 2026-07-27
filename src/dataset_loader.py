from __future__ import annotations

from pathlib import Path

from src.datasets import Dataset, DatasetService, DatasetStatus, DatasetVersion, JsonDatasetRepository
from src.datasets.ai_test_lab_adapter import dataset_entry_to_prompt_test
from src.models import PromptTest


class DatasetNotActiveError(ValueError):
    pass


class EmptyDatasetError(ValueError):
    pass


def load_dataset_tests(dataset_id: str, *, storage_dir: str | Path = "datasets", version: int | None = None) -> list[PromptTest]:
    service = DatasetService(JsonDatasetRepository(storage_dir))
    dataset = service.get_dataset(dataset_id)
    if not isinstance(dataset, Dataset):
        raise TypeError("Expected a Dataset aggregate")
    if dataset.manifest.status != DatasetStatus.ACTIVE:
        raise DatasetNotActiveError(
            f"Dataset '{dataset.manifest.name}' has status '{dataset.manifest.status.value}'. Only active datasets can run."
        )
    selected: DatasetVersion
    if version is None:
        selected = dataset.latest()
    else:
        loaded = service.get_dataset(dataset_id, version=version)
        if not isinstance(loaded, DatasetVersion):
            raise TypeError("Expected a DatasetVersion object")
        selected = loaded
    enabled_entries = [entry for entry in selected.entries if entry.enabled]
    if not enabled_entries:
        raise EmptyDatasetError(
            f"Dataset '{dataset.manifest.name}' version {selected.version} has no enabled entries."
        )
    return [dataset_entry_to_prompt_test(entry) for entry in enabled_entries]
