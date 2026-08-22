from src.evaluation_run_provenance import EvaluationRunProvenance
from src.evaluation_run_provenance_fingerprint import (
    fingerprint_evaluation_run_provenance,
)
from src.evaluation_run_provenance_verification import (
    verify_evaluation_run_provenance_fingerprint,
)


def test_matching_provenance_fingerprint_verifies_successfully():
    provenance = EvaluationRunProvenance(
        run_id="run-001",
        model="llama3.1:latest",
        evaluation_profile="default",
        dataset="sample-dataset",
        dataset_version="v1",
        report_contract="public-report-v1",
        report_contract_fingerprint="contract-fingerprint-001",
    )

    fingerprint = fingerprint_evaluation_run_provenance(provenance)

    assert (
        verify_evaluation_run_provenance_fingerprint(
            provenance,
            fingerprint,
        )
        is True
    )


def test_modified_provenance_fingerprint_fails_verification():
    original = EvaluationRunProvenance(
        run_id="run-001",
        model="llama3.1:latest",
        evaluation_profile="default",
        dataset="sample-dataset",
        dataset_version="v1",
        report_contract="public-report-v1",
        report_contract_fingerprint="contract-fingerprint-001",
    )

    expected_fingerprint = fingerprint_evaluation_run_provenance(original)

    modified = EvaluationRunProvenance(
        run_id="run-001",
        model="llama3.1:latest",
        evaluation_profile="default",
        dataset="sample-dataset",
        dataset_version="v2",
        report_contract="public-report-v1",
        report_contract_fingerprint="contract-fingerprint-001",
    )

    assert (
        verify_evaluation_run_provenance_fingerprint(
            modified,
            expected_fingerprint,
        )
        is False
    )