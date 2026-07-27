from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from datetime import datetime, timezone
from typing import Iterable

from .models import (
    Dataset,
    DatasetEntry,
    DatasetManifest,
    DatasetStatus,
    DatasetVersion,
)
from .repository import JsonDatasetRepository


class DuplicateEntryError(ValueError):
    pass


class DatasetVersionNotFoundError(KeyError):
    pass


class DatasetService:
    """Application service for dataset lifecycle and immutable versioning."""

    def __init__(self, repository: JsonDatasetRepository) -> None:
        self.repository = repository

    def create_dataset(
        self,
        *,
        name: str,
        description: str = "",
        entries: Iterable[DatasetEntry] = (),
        tags: list[str] | None = None,
        created_by: str = "system",
    ) -> Dataset:
        normalized_entries = list(entries)
        self._assert_unique_entry_ids(normalized_entries)

        manifest = DatasetManifest(
            name=name,
            description=description,
            tags=tags or [],
        )
        initial_version = self._make_version(
            version=1,
            entries=normalized_entries,
            created_by=created_by,
            change_summary="Initial version",
        )
        dataset = Dataset(manifest=manifest, versions=[initial_version])
        self.repository.save(dataset, overwrite=False)
        return dataset

    def get_dataset(
        self,
        dataset_id: str,
        version: int | None = None,
    ) -> Dataset | DatasetVersion:
        dataset = self.repository.get(dataset_id)
        if version is None:
            return dataset
        return self._find_version(dataset, version)

    def list_datasets(
        self,
        *,
        status: DatasetStatus | None = None,
        tag: str | None = None,
    ) -> list[DatasetManifest]:
        manifests = [dataset.manifest for dataset in self.repository.list()]

        if status is not None:
            manifests = [item for item in manifests if item.status == status]

        if tag is not None:
            normalized_tag = tag.strip().lower()
            manifests = [item for item in manifests if normalized_tag in item.tags]

        return sorted(manifests, key=lambda item: item.updated_at, reverse=True)

    def add_entry(
        self,
        dataset_id: str,
        entry: DatasetEntry,
        *,
        created_by: str = "system",
        change_summary: str | None = None,
    ) -> Dataset:
        dataset = self.repository.get(dataset_id)
        entries = deepcopy(dataset.latest().entries)

        if any(item.id == entry.id for item in entries):
            raise DuplicateEntryError(entry.id)

        entries.append(entry)
        return self._append_version(
            dataset,
            entries,
            created_by=created_by,
            change_summary=change_summary or f"Added entry: {entry.name}",
        )

    def update_entry(
        self,
        dataset_id: str,
        entry_id: str,
        changes: dict,
        *,
        created_by: str = "system",
    ) -> Dataset:
        dataset = self.repository.get(dataset_id)
        entries = deepcopy(dataset.latest().entries)

        for index, entry in enumerate(entries):
            if entry.id == entry_id:
                candidate = entry.model_copy(update=changes)
                entries[index] = DatasetEntry.model_validate(candidate.model_dump())

                return self._append_version(
                    dataset,
                    entries,
                    created_by=created_by,
                    change_summary=f"Updated entry: {entry_id}",
                )

        raise KeyError(f"entry not found: {entry_id}")

    def remove_entry(
        self,
        dataset_id: str,
        entry_id: str,
        *,
        created_by: str = "system",
    ) -> Dataset:
        dataset = self.repository.get(dataset_id)
        current_entries = dataset.latest().entries
        entries = [entry for entry in current_entries if entry.id != entry_id]

        if len(entries) == len(current_entries):
            raise KeyError(f"entry not found: {entry_id}")

        return self._append_version(
            dataset,
            entries,
            created_by=created_by,
            change_summary=f"Removed entry: {entry_id}",
        )

    def set_status(self, dataset_id: str, status: DatasetStatus) -> Dataset:
        dataset = self.repository.get(dataset_id)
        dataset.manifest.status = status
        dataset.manifest.updated_at = datetime.now(timezone.utc)
        self.repository.save(dataset)
        return dataset

    def rollback(
        self,
        dataset_id: str,
        source_version: int,
        *,
        created_by: str = "system",
    ) -> Dataset:
        dataset = self.repository.get(dataset_id)
        version = self._find_version(dataset, source_version)

        return self._append_version(
            dataset,
            deepcopy(version.entries),
            created_by=created_by,
            change_summary=f"Rolled back to version {source_version}",
        )

    def export_version(self, dataset_id: str, version: int | None = None) -> dict:
        dataset = self.repository.get(dataset_id)
        selected = dataset.latest() if version is None else self._find_version(dataset, version)

        return {
            "dataset_id": dataset.manifest.id,
            "dataset_name": dataset.manifest.name,
            "version": selected.version,
            "checksum": selected.checksum,
            "entries": [entry.model_dump(mode="json") for entry in selected.entries],
        }

    def import_entries(
        self,
        dataset_id: str,
        raw_entries: list[dict],
        *,
        replace: bool = False,
        created_by: str = "system",
    ) -> Dataset:
        dataset = self.repository.get(dataset_id)
        imported = [DatasetEntry.model_validate(item) for item in raw_entries]

        if replace:
            combined = imported
            summary = f"Replaced entries with {len(imported)} imported records"
        else:
            combined = deepcopy(dataset.latest().entries) + imported
            summary = f"Imported {len(imported)} entries"

        return self._append_version(
            dataset,
            combined,
            created_by=created_by,
            change_summary=summary,
        )

    def _append_version(
        self,
        dataset: Dataset,
        entries: list[DatasetEntry],
        *,
        created_by: str,
        change_summary: str,
    ) -> Dataset:
        self._assert_unique_entry_ids(entries)

        next_version = dataset.manifest.latest_version + 1
        dataset.versions.append(
            self._make_version(
                version=next_version,
                entries=entries,
                created_by=created_by,
                change_summary=change_summary,
            )
        )
        dataset.manifest.latest_version = next_version
        dataset.manifest.updated_at = datetime.now(timezone.utc)
        self.repository.save(dataset)
        return dataset

    @staticmethod
    def _make_version(
        *,
        version: int,
        entries: list[DatasetEntry],
        created_by: str,
        change_summary: str,
    ) -> DatasetVersion:
        return DatasetVersion(
            version=version,
            entries=deepcopy(entries),
            created_by=created_by,
            change_summary=change_summary,
            checksum=DatasetService._checksum(entries),
        )

    @staticmethod
    def _checksum(entries: list[DatasetEntry]) -> str:
        canonical_json = json.dumps(
            [entry.model_dump(mode="json") for entry in entries],
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        return hashlib.sha256(canonical_json).hexdigest()

    @staticmethod
    def _assert_unique_entry_ids(entries: list[DatasetEntry]) -> None:
        ids = [entry.id for entry in entries]
        if len(ids) != len(set(ids)):
            raise DuplicateEntryError("dataset contains duplicate entry ids")

    @staticmethod
    def _find_version(dataset: Dataset, version: int) -> DatasetVersion:
        for item in dataset.versions:
            if item.version == version:
                return item
        raise DatasetVersionNotFoundError(version)
