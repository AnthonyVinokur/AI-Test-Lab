from datetime import timedelta

from src.datasets import (
    Dataset,
    DatasetEntry,
    DatasetManifest,
    DatasetStatus,
    DatasetVersion,
    ValidationSeverity,
    validate_dataset,
)
from src.datasets.validator import _checksum


def make_dataset(
    *,
    entries: list[DatasetEntry] | None = None,
    status: DatasetStatus = DatasetStatus.DRAFT,
) -> Dataset:
    selected_entries = (
        entries
        if entries is not None
        else [
            DatasetEntry(
                id="entry-1",
                name="Greeting",
                input="Say hello",
                expected_output="Hello",
            )
        ]
    )
    manifest = DatasetManifest(
        id="dataset-1",
        name="Validator dataset",
        status=status,
        latest_version=1,
    )
    version = DatasetVersion(
        version=1,
        entries=selected_entries,
        checksum=_checksum(selected_entries),
        created_at=manifest.created_at,
    )
    return Dataset(manifest=manifest, versions=[version])


def issue_codes(dataset: Dataset) -> set[str]:
    return {issue.code for issue in validate_dataset(dataset).issues}


def test_valid_dataset_has_no_issues() -> None:
    result = validate_dataset(make_dataset())

    assert result.is_valid
    assert result.issues == ()
    assert result.errors == ()
    assert result.warnings == ()


def test_checksum_mismatch_is_error() -> None:
    dataset = make_dataset()
    dataset.versions[0].checksum = "0" * 64

    result = validate_dataset(dataset)

    assert "checksum_mismatch" in {issue.code for issue in result.errors}
    assert not result.is_valid


def test_invalid_checksum_format_is_error() -> None:
    dataset = make_dataset()
    dataset.versions[0].checksum = "z" * 64

    assert "invalid_checksum_format" in issue_codes(dataset)


def test_duplicate_entry_ids_are_reported() -> None:
    entry = DatasetEntry(
        id="duplicate",
        name="First",
        input="A",
        expected_output="A",
    )
    dataset = make_dataset(
        entries=[entry, entry.model_copy(update={"name": "Second"})]
    )

    result = validate_dataset(dataset)

    duplicate_issue = next(
        issue for issue in result.errors if issue.code == "duplicate_entry_id"
    )
    assert duplicate_issue.version == 1
    assert duplicate_issue.entry_id == "duplicate"


def test_manifest_latest_version_must_match_highest_version() -> None:
    dataset = make_dataset()
    dataset.manifest.latest_version = 2

    assert "latest_version_mismatch" in issue_codes(dataset)


def test_version_numbers_must_be_contiguous() -> None:
    dataset = make_dataset()
    dataset.versions[0].version = 2
    dataset.manifest.latest_version = 2

    assert "non_contiguous_versions" in issue_codes(dataset)


def test_duplicate_version_numbers_are_reported() -> None:
    dataset = make_dataset()
    dataset.versions.append(dataset.versions[0].model_copy(deep=True))

    assert "duplicate_version" in issue_codes(dataset)


def test_active_dataset_cannot_be_empty() -> None:
    result = validate_dataset(
        make_dataset(entries=[], status=DatasetStatus.ACTIVE)
    )

    assert "active_dataset_empty" in {
        issue.code for issue in result.errors
    }
    assert not result.is_valid


def test_empty_draft_version_is_warning_only() -> None:
    result = validate_dataset(make_dataset(entries=[]))

    assert result.is_valid
    assert any(
        issue.code == "empty_version"
        and issue.severity == ValidationSeverity.WARNING
        for issue in result.warnings
    )


def test_missing_expected_output_is_warning() -> None:
    dataset = make_dataset(
        entries=[
            DatasetEntry(
                id="entry-1",
                name="Open evaluation",
                input="Summarize this",
            )
        ]
    )

    result = validate_dataset(dataset)

    assert result.is_valid
    assert result.warnings[0].code == "missing_expected_output"
    assert result.warnings[0].entry_id == "entry-1"


def test_manifest_updated_at_cannot_precede_created_at() -> None:
    dataset = make_dataset()
    dataset.manifest.updated_at = (
        dataset.manifest.created_at - timedelta(seconds=1)
    )

    assert "manifest_timestamp_order" in issue_codes(dataset)


def test_version_cannot_predate_dataset() -> None:
    dataset = make_dataset()
    dataset.versions[0].created_at = (
        dataset.manifest.created_at - timedelta(seconds=1)
    )

    assert "version_predates_dataset" in issue_codes(dataset)
