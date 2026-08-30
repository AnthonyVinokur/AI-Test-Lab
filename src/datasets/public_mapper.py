from __future__ import annotations

from copy import deepcopy

from src.datasets.models import (
    Dataset,
    DatasetEntry,
    DatasetManifest,
    DatasetVersion,
)
from src.datasets.public_contract import (
    DatasetEntryV1,
    DatasetExportV1,
    DatasetManifestV1,
    DatasetV1,
    DatasetVersionV1,
)


def map_dataset_entry(
    entry: DatasetEntry,
) -> DatasetEntryV1:
    return DatasetEntryV1(
        id=entry.id,
        name=entry.name,
        input=entry.input,
        expected_output=entry.expected_output,
        category=entry.category,
        tags=list(entry.tags),
        metadata=deepcopy(entry.metadata),
        enabled=entry.enabled,
    )


def map_dataset_version(
    version: DatasetVersion,
) -> DatasetVersionV1:
    return DatasetVersionV1(
        version=version.version,
        created_at=version.created_at,
        created_by=version.created_by,
        change_summary=version.change_summary,
        entries=[
            map_dataset_entry(entry)
            for entry in version.entries
        ],
        checksum=version.checksum,
    )


def map_dataset_manifest(
    manifest: DatasetManifest,
) -> DatasetManifestV1:
    return DatasetManifestV1(
        id=manifest.id,
        name=manifest.name,
        description=manifest.description,
        status=manifest.status.value,
        created_at=manifest.created_at,
        updated_at=manifest.updated_at,
        latest_version=manifest.latest_version,
        tags=list(manifest.tags),
    )


def map_dataset(
    dataset: Dataset,
) -> DatasetV1:
    return DatasetV1(
        manifest=map_dataset_manifest(dataset.manifest),
        versions=[
            map_dataset_version(version)
            for version in dataset.versions
        ],
    )


def map_dataset_export(
    dataset: Dataset,
    version: DatasetVersion,
) -> DatasetExportV1:
    return DatasetExportV1(
        dataset_id=dataset.manifest.id,
        dataset_name=dataset.manifest.name,
        version=version.version,
        checksum=version.checksum,
        entries=[
            map_dataset_entry(entry)
            for entry in version.entries
        ],
    )
