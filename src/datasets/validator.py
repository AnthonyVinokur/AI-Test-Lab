from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import dataclass
from enum import StrEnum

from .models import Dataset, DatasetEntry, DatasetStatus

from src.internal_serialization import serialize_internal_model

class ValidationSeverity(StrEnum):
    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    code: str
    message: str
    severity: ValidationSeverity = ValidationSeverity.ERROR
    version: int | None = None
    entry_id: str | None = None


@dataclass(frozen=True, slots=True)
class DatasetValidationResult:
    dataset_id: str
    issues: tuple[ValidationIssue, ...]

    @property
    def is_valid(self) -> bool:
        return not any(
            issue.severity == ValidationSeverity.ERROR for issue in self.issues
        )

    @property
    def errors(self) -> tuple[ValidationIssue, ...]:
        return tuple(
            issue
            for issue in self.issues
            if issue.severity == ValidationSeverity.ERROR
        )

    @property
    def warnings(self) -> tuple[ValidationIssue, ...]:
        return tuple(
            issue
            for issue in self.issues
            if issue.severity == ValidationSeverity.WARNING
        )


def validate_dataset(dataset: Dataset) -> DatasetValidationResult:
    """Validate cross-record dataset invariants not enforced by Pydantic."""
    issues: list[ValidationIssue] = []
    versions = sorted(dataset.versions, key=lambda item: item.version)
    version_numbers = [version.version for version in versions]

    if len(version_numbers) != len(set(version_numbers)):
        issues.append(
            ValidationIssue(
                code="duplicate_version",
                message="Dataset contains duplicate version numbers.",
            )
        )

    expected_versions = list(range(1, max(version_numbers) + 1))
    if version_numbers != expected_versions:
        issues.append(
            ValidationIssue(
                code="non_contiguous_versions",
                message=(
                    "Versions must be contiguous starting at 1; "
                    f"found {version_numbers}."
                ),
            )
        )

    highest_version = max(version_numbers)
    if dataset.manifest.latest_version != highest_version:
        issues.append(
            ValidationIssue(
                code="latest_version_mismatch",
                message=(
                    f"Manifest latest_version is {dataset.manifest.latest_version}, "
                    f"but highest stored version is {highest_version}."
                ),
            )
        )

    if dataset.manifest.updated_at < dataset.manifest.created_at:
        issues.append(
            ValidationIssue(
                code="manifest_timestamp_order",
                message="Manifest updated_at cannot be earlier than created_at.",
            )
        )

    latest_version = max(versions, key=lambda item: item.version)
    if (
        dataset.manifest.status == DatasetStatus.ACTIVE
        and not latest_version.entries
    ):
        issues.append(
            ValidationIssue(
                code="active_dataset_empty",
                message="Active dataset must contain at least one entry.",
            )
        )

    for version in versions:
        if not _is_sha256(version.checksum):
            issues.append(
                ValidationIssue(
                    code="invalid_checksum_format",
                    message=(
                        "Checksum must be a 64-character hexadecimal "
                        "SHA-256 value."
                    ),
                    version=version.version,
                )
            )
        elif version.checksum != _checksum(version.entries):
            issues.append(
                ValidationIssue(
                    code="checksum_mismatch",
                    message="Stored checksum does not match version entries.",
                    version=version.version,
                )
            )

        entry_id_counts = Counter(entry.id for entry in version.entries)
        for entry_id, count in sorted(entry_id_counts.items()):
            if count > 1:
                issues.append(
                    ValidationIssue(
                        code="duplicate_entry_id",
                        message=(
                            f"Entry id {entry_id!r} appears {count} times "
                            "in the version."
                        ),
                        version=version.version,
                        entry_id=entry_id,
                    )
                )

        if version.created_at < dataset.manifest.created_at:
            issues.append(
                ValidationIssue(
                    code="version_predates_dataset",
                    message=(
                        "Version created_at cannot be earlier than dataset "
                        "created_at."
                    ),
                    version=version.version,
                )
            )

        if not version.entries:
            issues.append(
                ValidationIssue(
                    code="empty_version",
                    message="Dataset version contains no entries.",
                    severity=ValidationSeverity.WARNING,
                    version=version.version,
                )
            )

        for entry in version.entries:
            if entry.expected_output is None:
                issues.append(
                    ValidationIssue(
                        code="missing_expected_output",
                        message=(
                            "Entry has no expected_output and may require "
                            "custom evaluation."
                        ),
                        severity=ValidationSeverity.WARNING,
                        version=version.version,
                        entry_id=entry.id,
                    )
                )

    return DatasetValidationResult(
        dataset_id=dataset.manifest.id,
        issues=tuple(issues),
    )


def _checksum(entries: list[DatasetEntry]) -> str:
    canonical_json = json.dumps(
        [
            serialize_internal_model(
                entry,
                mode="json",
            )
            for entry in entries
        ],
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")

    return hashlib.sha256(canonical_json).hexdigest()


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and all(
        character in "0123456789abcdefABCDEF" for character in value
    )
