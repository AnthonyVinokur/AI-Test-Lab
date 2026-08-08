
from main import list_available_datasets
from pathlib import Path

from main import print_dataset_info
from src.datasets import (
    DatasetEntry,
    DatasetService,
    DatasetStatus,
    JsonDatasetRepository,
)


def create_test_dataset(tmp_path: Path):
    service = DatasetService(JsonDatasetRepository(tmp_path))

    dataset = service.create_dataset(
        name="Core Regression",
        description="Golden prompts for AI regression testing",
        tags=["regression"],
        entries=[
            DatasetEntry(
                id="greeting-001",
                name="Basic greeting",
                input="Say hello",
                expected_output="Hello",
                category="functional",
                tags=["smoke"],
            )
        ],
        created_by="test",
    )

    service.set_status(
        dataset.manifest.id,
        DatasetStatus.ACTIVE,
    )

    return dataset


def test_print_dataset_info_displays_metadata(
    tmp_path: Path,
    capsys,
) -> None:
    dataset = create_test_dataset(tmp_path)

    exit_code = print_dataset_info(
        dataset.manifest.id,
        tmp_path,
    )

    output = capsys.readouterr().out

    assert exit_code == 0
    assert "Core Regression" in output
    assert dataset.manifest.id in output
    assert "ACTIVE" in output
    assert "Golden prompts for AI regression testing" in output
    assert "Entries          : 1" in output
    assert "Enabled          : 1" in output
    assert "Disabled         : 0" in output
    assert "Average prompt   : 9.0 characters" in output
    assert "functional" in output
    assert "smoke" in output
    assert dataset.latest().checksum in output


def test_print_dataset_info_supports_specific_version(
    tmp_path: Path,
    capsys,
) -> None:
    dataset = create_test_dataset(tmp_path)

    service = DatasetService(JsonDatasetRepository(tmp_path))

    service.add_entry(
        dataset.manifest.id,
        DatasetEntry(
            id="python-001",
            name="Python creator",
            input="Who created Python?",
            expected_output="Guido van Rossum",
            category="factual",
        ),
        created_by="test",
    )

    exit_code = print_dataset_info(
        dataset.manifest.id,
        tmp_path,
        version=1,
    )

    output = capsys.readouterr().out

    assert exit_code == 0
    assert "Latest version   : 2" in output
    assert "Viewing version  : 1" in output
    assert "Entries          : 1" in output

def test_list_available_datasets_when_storage_is_empty(
    tmp_path: Path,
    capsys,
) -> None:
    exit_code = list_available_datasets(tmp_path)

    output = capsys.readouterr().out

    assert exit_code == 0
    assert "Available datasets" in output
    assert "No datasets found." in output


def test_list_available_datasets_displays_dataset(
    tmp_path: Path,
    capsys,
) -> None:
    service = DatasetService(JsonDatasetRepository(tmp_path))

    dataset = service.create_dataset(
        name="Factual Questions",
        description="General factual-answer evaluation dataset",
        tags=["qa", "factual"],
        entries=[
            DatasetEntry(
                id="capital-france",
                name="Capital of France",
                input="What is the capital of France?",
                expected_output="Paris",
                category="geography",
            )
        ],
        created_by="test",
    )

    service.set_status(
        dataset.manifest.id,
        DatasetStatus.ACTIVE,
    )

    exit_code = list_available_datasets(tmp_path)

    output = capsys.readouterr().out

    assert exit_code == 0
    assert "Factual Questions" in output
    assert "[ACTIVE]" in output
    assert dataset.manifest.id in output
    assert "version=1" in output
    assert "factual, qa" in output
    assert "Total datasets: 1" in output