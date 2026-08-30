from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from src.datasets.models import (
    Dataset,
    DatasetEntry,
    DatasetManifest,
    DatasetStatus,
    DatasetVersion,
)
from src.datasets.public_contract import DatasetExportV1
from src.datasets.public_mapper import (
    map_dataset,
    map_dataset_entry,
    map_dataset_export,
    map_dataset_manifest,
    map_dataset_version,
)
from src.public_contract import serialize_public_contract


NOW = datetime(
    2026,
    8,
    29,
    12,
    0,
    tzinfo=timezone.utc,
)


def make_entry() -> DatasetEntry:
    return DatasetEntry(
        id="entry-1",
        name="Greeting",
        input="Say hello",
        expected_output="Hello",
        category="smoke",
        tags=["smoke"],
        metadata={
            "owner": "qa",
        },
        enabled=True,
    )


def make_version() -> DatasetVersion:
    return DatasetVersion(
        version=1,
        created_at=NOW,
        created_by="test",
        change_summary="Initial version",
        entries=[make_entry()],
        checksum="a" * 64,
    )


def make_manifest() -> DatasetManifest:
    return DatasetManifest(
        id="dataset-1",
        name="Controlled Dataset",
        description="Public contract test",
        status=DatasetStatus.ACTIVE,
        created_at=NOW,
        updated_at=NOW,
        latest_version=1,
        tags=["smoke"],
    )


def make_dataset() -> Dataset:
    return Dataset(
        manifest=make_manifest(),
        versions=[make_version()],
    )


def test_dataset_entry_maps_to_explicit_public_contract() -> None:
    public_entry = map_dataset_entry(
        make_entry()
    )

    payload = serialize_public_contract(
        public_entry
    )

    assert payload == {
        "id": "entry-1",
        "name": "Greeting",
        "input": "Say hello",
        "expected_output": "Hello",
        "category": "smoke",
        "tags": ["smoke"],
        "metadata": {
            "owner": "qa",
        },
        "enabled": True,
    }


def test_dataset_manifest_maps_status_to_public_string() -> None:
    payload = serialize_public_contract(
        map_dataset_manifest(
            make_manifest()
        )
    )

    assert payload["status"] == "active"
    assert payload["id"] == "dataset-1"
    assert payload["name"] == "Controlled Dataset"


def test_dataset_version_preserves_public_shape() -> None:
    payload = serialize_public_contract(
        map_dataset_version(
            make_version()
        )
    )

    assert set(payload) == {
        "version",
        "created_at",
        "created_by",
        "change_summary",
        "entries",
        "checksum",
    }

    assert payload["version"] == 1
    assert payload["checksum"] == "a" * 64
    assert len(payload["entries"]) == 1


def test_dataset_show_contract_has_only_manifest_and_versions() -> None:
    payload = serialize_public_contract(
        map_dataset(
            make_dataset()
        )
    )

    assert set(payload) == {
        "manifest",
        "versions",
    }

    assert payload["manifest"]["id"] == "dataset-1"
    assert len(payload["versions"]) == 1


def test_dataset_export_preserves_existing_export_shape() -> None:
    dataset = make_dataset()

    payload = serialize_public_contract(
        map_dataset_export(
            dataset,
            dataset.latest(),
        )
    )

    assert set(payload) == {
        "dataset_id",
        "dataset_name",
        "version",
        "checksum",
        "entries",
    }

    assert payload["dataset_id"] == "dataset-1"
    assert payload["dataset_name"] == "Controlled Dataset"
    assert payload["version"] == 1


def test_dataset_public_contract_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        DatasetExportV1(
            dataset_id="dataset-1",
            dataset_name="Controlled Dataset",
            version=1,
            checksum="a" * 64,
            entries=[],
            proprietary_internal_state="must-not-leak",
        )