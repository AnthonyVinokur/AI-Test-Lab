from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from threading import RLock

from .models import Dataset


class DatasetNotFoundError(KeyError):
    pass


class DatasetAlreadyExistsError(ValueError):
    pass


class JsonDatasetRepository:
    """JSON repository that stores one dataset aggregate per file."""

    def __init__(self, storage_dir: str | Path = "datasets") -> None:
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()

    def save(self, dataset: Dataset, *, overwrite: bool = True) -> None:
        path = self._path(dataset.manifest.id)

        with self._lock:
            if path.exists() and not overwrite:
                raise DatasetAlreadyExistsError(dataset.manifest.id)

            payload = dataset.model_dump(mode="json")
            self._atomic_write(path, payload)

    def get(self, dataset_id: str) -> Dataset:
        path = self._path(dataset_id)
        if not path.exists():
            raise DatasetNotFoundError(dataset_id)

        with path.open("r", encoding="utf-8") as file:
            return Dataset.model_validate(json.load(file))

    def delete(self, dataset_id: str) -> None:
        path = self._path(dataset_id)

        with self._lock:
            if not path.exists():
                raise DatasetNotFoundError(dataset_id)
            path.unlink()

    def list(self) -> list[Dataset]:
        datasets: list[Dataset] = []

        for path in sorted(self.storage_dir.glob("*.json")):
            with path.open("r", encoding="utf-8") as file:
                datasets.append(Dataset.model_validate(json.load(file)))

        return datasets

    def exists(self, dataset_id: str) -> bool:
        return self._path(dataset_id).exists()

    def _path(self, dataset_id: str) -> Path:
        safe_id = Path(dataset_id).name
        if safe_id != dataset_id or dataset_id in {"", ".", ".."}:
            raise ValueError("invalid dataset id")
        return self.storage_dir / f"{safe_id}.json"

    @staticmethod
    def _atomic_write(path: Path, payload: dict) -> None:
        file_descriptor, temporary_name = tempfile.mkstemp(
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            text=True,
        )

        try:
            with os.fdopen(file_descriptor, "w", encoding="utf-8") as temporary_file:
                json.dump(payload, temporary_file, indent=2, ensure_ascii=False)
                temporary_file.write("\n")
                temporary_file.flush()
                os.fsync(temporary_file.fileno())

            os.replace(temporary_name, path)
        except Exception:
            try:
                os.unlink(temporary_name)
            except FileNotFoundError:
                pass
            raise
