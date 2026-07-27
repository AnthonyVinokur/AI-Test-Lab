from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import uuid4
from pydantic import BaseModel, ConfigDict, Field, field_validator


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class DatasetStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class DatasetEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str = Field(min_length=1, max_length=200)
    input: str = Field(min_length=1)
    expected_output: str | None = None
    category: str = Field(default="general", min_length=1, max_length=100)
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True

    @field_validator("name", "input", "category")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value: raise ValueError("value cannot be blank")
        return value

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, tags: list[str]) -> list[str]:
        return sorted({tag.strip().lower() for tag in tags if tag.strip()})


class DatasetVersion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: int = Field(ge=1)
    created_at: datetime = Field(default_factory=utc_now)
    created_by: str = Field(default="system", min_length=1)
    change_summary: str = Field(default="Initial version", min_length=1)
    entries: list[DatasetEntry] = Field(default_factory=list)
    checksum: str = Field(min_length=64, max_length=64)


class DatasetManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str = Field(min_length=1, max_length=200)
    description: str = ""
    status: DatasetStatus = DatasetStatus.DRAFT
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    latest_version: int = Field(default=1, ge=1)
    tags: list[str] = Field(default_factory=list)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        value = value.strip()
        if not value: raise ValueError("name cannot be blank")
        return value

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, tags: list[str]) -> list[str]:
        return sorted({tag.strip().lower() for tag in tags if tag.strip()})


class Dataset(BaseModel):
    model_config = ConfigDict(extra="forbid")
    manifest: DatasetManifest
    versions: list[DatasetVersion] = Field(min_length=1)

    def latest(self) -> DatasetVersion:
        return max(self.versions, key=lambda item: item.version)
