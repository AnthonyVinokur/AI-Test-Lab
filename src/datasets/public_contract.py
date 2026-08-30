from __future__ import annotations

from datetime import datetime
from typing import Any

from src.public_contract import PublicContractModel


class DatasetEntryV1(PublicContractModel):
    id: str
    name: str
    input: str
    expected_output: str | None
    category: str
    tags: list[str]
    metadata: dict[str, Any]
    enabled: bool


class DatasetVersionV1(PublicContractModel):
    version: int
    created_at: datetime
    created_by: str
    change_summary: str
    entries: list[DatasetEntryV1]
    checksum: str


class DatasetManifestV1(PublicContractModel):
    id: str
    name: str
    description: str
    status: str
    created_at: datetime
    updated_at: datetime
    latest_version: int
    tags: list[str]


class DatasetV1(PublicContractModel):
    manifest: DatasetManifestV1
    versions: list[DatasetVersionV1]


class DatasetExportV1(PublicContractModel):
    dataset_id: str
    dataset_name: str
    version: int
    checksum: str
    entries: list[DatasetEntryV1]
