from __future__ import annotations

from collections import Counter
from pathlib import Path

from src.datasets.models import DatasetStatus
from src.datasets.repository import JsonDatasetRepository
from src.datasets.service import DatasetService

from src.cli.exit_codes import CliExitCode


def list_available_datasets(storage_dir: Path) -> int:
    """Print all managed datasets stored in the configured directory."""

    service = DatasetService(JsonDatasetRepository(storage_dir))
    datasets = service.list_datasets()

    print("\nAvailable datasets")
    print("==================")

    if not datasets:
        print("No datasets found.")
        return CliExitCode.SUCCESS

    for dataset in datasets:
        status_marker = {
            DatasetStatus.ACTIVE: "[ACTIVE]",
            DatasetStatus.DRAFT: "[DRAFT]",
            DatasetStatus.ARCHIVED: "[ARCHIVED]",
        }[dataset.status]

        print(
            f"{status_marker:<12} "
            f"{dataset.name} "
            f"(id={dataset.id}, version={dataset.latest_version})"
        )

        if dataset.description:
            print(f"{'':12} {dataset.description}")

        if dataset.tags:
            print(f"{'':12} Tags: {', '.join(dataset.tags)}")

    print(f"\nTotal datasets: {len(datasets)}")
    return CliExitCode.SUCCESS

def print_dataset_info(
    dataset_id: str,
    storage_dir: Path,
    version: int | None = None,
) -> int:
    service = DatasetService(JsonDatasetRepository(storage_dir))

    dataset = service.get_dataset(dataset_id)

    if version is None:
        selected = dataset.latest()
    else:
        loaded = service.get_dataset(dataset_id, version)

        if not hasattr(loaded, "entries"):
            raise TypeError("Expected DatasetVersion")

        selected = loaded

    enabled = sum(entry.enabled for entry in selected.entries)
    disabled = len(selected.entries) - enabled

    categories = Counter(
        entry.category
        for entry in selected.entries
    )

    tags = sorted(
        {
            tag
            for entry in selected.entries
            for tag in entry.tags
        }
    )

    average_prompt_length = (
        sum(len(entry.input) for entry in selected.entries)
        / len(selected.entries)
        if selected.entries
        else 0
    )

    print("\nDataset Information")
    print("===================")
    print(f"Name             : {dataset.manifest.name}")
    print(f"ID               : {dataset.manifest.id}")
    print(f"Status           : {dataset.manifest.status.value.upper()}")
    print(f"Latest version   : {dataset.manifest.latest_version}")
    print(f"Viewing version  : {selected.version}")
    print(f"Description      : {dataset.manifest.description or 'None'}")

    print("\nStatistics")
    print("----------")
    print(f"Entries          : {len(selected.entries)}")
    print(f"Enabled          : {enabled}")
    print(f"Disabled         : {disabled}")
    print(f"Average prompt   : {average_prompt_length:.1f} characters")

    print("\nCategories")
    print("----------")

    if categories:
        for category, count in sorted(categories.items()):
            print(f"{category:<20} {count}")
    else:
        print("None")

    print("\nTags")
    print("----")

    if tags:
        for tag in tags:
            print(tag)
    else:
        print("None")

    print("\nChecksum")
    print("--------")
    print(selected.checksum)

    return CliExitCode.SUCCESS
