from src.evaluation_run_provenance import EvaluationRunProvenance
from src.evaluation_run_provenance_fingerprint import (
    fingerprint_evaluation_run_provenance,
)


def make_provenance(**overrides):
    values = {
        "run_id": "run-123",
        "model": "llama3.1:latest",
        "evaluation_profile": "fast-ci",
        "dataset": "smoke-tests",
        "dataset_version": "1",
        "report_contract": "public-report-v1",
        "report_contract_fingerprint": "abc123",
    }
    values.update(overrides)

    return EvaluationRunProvenance(**values)


def test_fingerprint_is_sha256_hex_digest():
    fingerprint = fingerprint_evaluation_run_provenance(make_provenance())

    assert isinstance(fingerprint, str)
    assert len(fingerprint) == 64
    assert all(character in "0123456789abcdef" for character in fingerprint)


def test_equivalent_provenance_produces_same_fingerprint():
    first = make_provenance()
    second = make_provenance()

    assert fingerprint_evaluation_run_provenance(
        first
    ) == fingerprint_evaluation_run_provenance(second)


def test_model_change_produces_different_fingerprint():
    first = make_provenance(model="llama3.1:latest")
    second = make_provenance(model="different-model")

    assert fingerprint_evaluation_run_provenance(
        first
    ) != fingerprint_evaluation_run_provenance(second)


def test_evaluation_profile_change_produces_different_fingerprint():
    first = make_provenance(evaluation_profile="fast-ci")
    second = make_provenance(evaluation_profile="deep-quality")

    assert fingerprint_evaluation_run_provenance(
        first
    ) != fingerprint_evaluation_run_provenance(second)


def test_dataset_change_produces_different_fingerprint():
    first = make_provenance(dataset="smoke-tests")
    second = make_provenance(dataset="regression-tests")

    assert fingerprint_evaluation_run_provenance(
        first
    ) != fingerprint_evaluation_run_provenance(second)


def test_dataset_version_change_produces_different_fingerprint():
    first = make_provenance(dataset_version="1")
    second = make_provenance(dataset_version="2")

    assert fingerprint_evaluation_run_provenance(
        first
    ) != fingerprint_evaluation_run_provenance(second)


def test_report_contract_change_produces_different_fingerprint():
    first = make_provenance(report_contract="public-report-v1")
    second = make_provenance(report_contract="public-report-v2")

    assert fingerprint_evaluation_run_provenance(
        first
    ) != fingerprint_evaluation_run_provenance(second)


def test_report_contract_fingerprint_change_produces_different_fingerprint():
    first = make_provenance(report_contract_fingerprint="abc123")
    second = make_provenance(report_contract_fingerprint="def456")

    assert fingerprint_evaluation_run_provenance(
        first
    ) != fingerprint_evaluation_run_provenance(second)


def test_fingerprinting_does_not_modify_provenance():
    provenance = make_provenance()
    before = provenance.to_dict()

    fingerprint_evaluation_run_provenance(provenance)

    assert provenance.to_dict() == before

